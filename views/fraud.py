import streamlit as st
from service.preprocess import set_page_visuals
from service.fds import load_models, read_excel, read_parquets, split_df, get_ml_model
from datetime import datetime
from service.database import connect_db, get_pjp_jkt

# Initial Page Setup
set_page_visuals("fds")

db = connect_db()

if "date_submitted" not in st.session_state:
    st.session_state["date_submitted"] = False
if "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = None
if "models" not in st.session_state:
    try:
        st.session_state["models"] = load_models()
    except Exception as e:
        st.error(f"Error loading models: {e}")
        st.session_state["models"] = None

models = st.session_state.get("models", None)

current_year = datetime.now().year
current_month = datetime.now().month - 1

placeholder = st.empty()

with placeholder.form(key="date_form"):
    year = st.number_input(
        "Enter a year:",
        min_value=0,
        max_value=9999,
        value=current_year,
        step=1
    )

    month = st.selectbox(
        "Enter a month:",
        options=['January', 'February', 'March', 'April', 'May', 'June', 'July',
                 'August', 'September', 'October', 'November', 'December'],
        index=current_month
    )

    submitted = st.form_submit_button("Submit")
    if submitted:
        st.session_state["date_submitted"] = True
        st.session_state["selected_year"] = year
        st.session_state["selected_month"] = month
        placeholder.empty()

success_placeholder = st.empty()

if st.session_state["date_submitted"] and not st.session_state["uploaded_files"]:
    success_placeholder.success("Tahun dan Bulan berhasil dipilih.")

if st.session_state["date_submitted"]:
    st.session_state["uploaded_files"] = st.file_uploader(
        "Upload Transaction Data",
        accept_multiple_files=True,
        type=["parquet", "xlsx", "xls"]
    )
    placeholder.empty()

if st.session_state["uploaded_files"]:
    success_placeholder.empty()
    uploaded_files = st.session_state["uploaded_files"]
    try:
        df = read_parquets(uploaded_files)

        df.reset_index(inplace=True)

        # Determine the report type based on FORM_NO
        form_no = df['FORM_NO'].iloc[0]
        if form_no == "FORMG0001":
            tipe_laporan = "Outgoing"
            predict_cols = ['FREKUENSI', 'NOMINAL_TRX', 'TUJUAN']
            selected_model = get_ml_model(tipe_laporan, models)
            df_split = split_df(df, tipe_laporan)
        elif form_no == "FORMG0002":
            tipe_laporan = "Incoming"
            predict_cols = ['FREKUENSI', 'NOMINAL_TRX']
            selected_model = get_ml_model(tipe_laporan, models)
            df_split = None
        else:
            tipe_laporan = "Domestik"
            predict_cols = ['FREKUENSI_PENGIRIMAN', 'NOMINAL_TRX', 'TUJUAN_TRX']
            selected_model = get_ml_model(tipe_laporan, models)
            df_split = split_df(df, tipe_laporan)

        st.success("Data berhasil terbaca!")
        st.markdown(f"## Laporan Analisis Transaksi {tipe_laporan} ({st.session_state["selected_month"]}, "
                    f"{st.session_state["selected_year"]})")
        st.dataframe(df)
        st.markdown(f"### Informasi Data Transaksi")

        num_of_rows = len(df)

        # Filter df
        list_pjp = get_pjp_jkt(db)

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Jumlah Data Transaksi**: {num_of_rows:,}")

        if df_split:
            for key in df_split.keys():
                indx = int(key) - 1
                selected_df_split = df_split[key][predict_cols].copy()
                original_index = df_split[key].index
                predictions = selected_model[indx].predict(selected_df_split)
                negative_predictions_count = sum(pred == -1 for pred in predictions)
                print(f"Number of negative predictions (-1): {negative_predictions_count}")
                df.loc[original_index, 'PREDICTED'] = predictions
        else:
            predictions = selected_model[0].predict(df[predict_cols])
            df['PREDICTED'] = predictions
        negative_predictions = df[df['PREDICTED'] == -1]
        st.warning(f"Found {len(negative_predictions)} transactions with negative predictions (-1).")
        st.dataframe(negative_predictions)
    except Exception as e:
        st.error(f"Error processing files: {e}")