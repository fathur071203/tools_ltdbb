import streamlit as st
import pandas as pd
from service.preprocess import set_page_visuals
from service.fds import load_models, read_excel, read_parquets, split_df, get_ml_model, \
    get_pjp_suspected_blacklisted_greylisted
from datetime import datetime
from service.database import connect_db, get_pjp_jkt, get_blacklisted_country, get_greylisted_country, get_sus_peoples, \
    upload_df, get_user_logs_data, get_country_participated
from collections import Counter
import json

# Initial Page Setup
set_page_visuals("fds")

db = connect_db()

list_pjp_dki = get_pjp_jkt(db)
list_blacklisted = get_blacklisted_country(db, True)
list_greylisted = get_greylisted_country(db, True)
list_sus_person = get_sus_peoples(db)

list_code_blacklisted = []
for country in list_blacklisted:
    list_code_blacklisted.append(country['code'])

list_code_greylisted = []
for country in list_greylisted:
    list_code_greylisted.append(country['code'])

list_name_sus_person = []
for person in list_sus_person:
    list_name_sus_person.append(person['name'])

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
        list_pjp_code_dki = []
        for pjp in list_pjp_dki:
            list_pjp_code_dki.append(pjp['code'])

        df = read_parquets(uploaded_files)

        df = df[df['SANDI_PELAPOR'].isin(list_pjp_code_dki)]
        df.index += 1

        # Determine the report type based on FORM_NO
        form_no = df['FORM_NO'].iloc[0]
        if form_no == "FORMG0001":
            df_blacklisted_filter = df[df['NEGARA_TUJUAN'].isin(list_code_blacklisted)]
            df_greylisted_filter = df[df['NEGARA_TUJUAN'].isin(list_code_greylisted)]
            df_suspected_person_filter = df[
                (df['NAMA_PENERIMA'].str.lower().isin([name.lower() for name in list_name_sus_person])) |
                (df['NAMA_PENGIRIM'].str.lower().isin([name.lower() for name in list_name_sus_person]))
                ]
            negara_text = "ke"
            tipe_laporan = "Outgoing"
            list_model_name = {1 : "isolation_forest_model_out_1.joblib", 2 : "isolation_forest_model_out_2.joblib",
                               3 : "isolation_forest_model_out_3.joblib"}
            predict_cols = ['FREKUENSI', 'NOMINAL_TRX', 'TUJUAN']
            selected_model = get_ml_model(tipe_laporan, models)  # dict {nama file : model}
            df_split = split_df(df, tipe_laporan)
        elif form_no == "FORMG0002":
            df_blacklisted_filter = df[df['NEGARA_ASAL'].isin(list_code_blacklisted)]
            df_greylisted_filter = df[df['NEGARA_ASAL'].isin(list_code_greylisted)]
            df_suspected_person_filter = df[
                (df['NAMA_PENERIMA'].str.lower().isin([name.lower() for name in list_name_sus_person])) |
                (df['NAMA_PENGIRIM'].str.lower().isin([name.lower() for name in list_name_sus_person]))
                ]
            negara_text = "dari"
            tipe_laporan = "Incoming"
            list_model_name = ["isolation_forest_model_inc.joblib"]
            predict_cols = ['FREKUENSI', 'NOMINAL_TRX']
            selected_model = get_ml_model(tipe_laporan, models)
            df_split = None
        else:
            df_blacklisted_filter = None
            df_greylisted_filter = None
            negara_text = None
            df_suspected_person_filter = df[
                (df['NAMA_PENERIMA'].str.lower().isin([name.lower() for name in list_name_sus_person])) |
                (df['NAMA_PENGIRIM'].str.lower().isin([name.lower() for name in list_name_sus_person]))
                ]
            tipe_laporan = "Domestik"
            list_model_name = { 1 : "isolation_forest_model_dom_1.joblib", 2 : "isolation_forest_model_dom_2.joblib",
                                3 : "isolation_forest_model_dom_3.joblib"}
            predict_cols = ['FREKUENSI_PENGIRIMAN', 'NOMINAL_TRX', 'TUJUAN_TRX']
            selected_model = get_ml_model(tipe_laporan, models)
            df_split = split_df(df, tipe_laporan)

        st.success("Data berhasil terbaca!")
        st.markdown(f"## Laporan Analisis Transaksi {tipe_laporan} ({st.session_state["selected_month"]}, "
                    f"{st.session_state["selected_year"]})")
        st.dataframe(df)
        st.divider()
        st.markdown(f"### Informasi Data Transaksi")

        # Filter df
        list_pjp = get_pjp_jkt(db)

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Jumlah Data Transaksi**: {len(df):,}")

        if df_split:
            for key in df_split.keys():
                selected_model_name = list_model_name.get(key)
                model_predict = selected_model.get(selected_model_name)
                selected_df_split = df_split[key][predict_cols].copy()
                original_index = df_split[key].index
                predictions = model_predict.predict(selected_df_split)
                negative_predictions_count = sum(pred == -1 for pred in predictions)
                df.loc[original_index, 'PREDICTED'] = predictions
        else:
            model_predict = selected_model.get(list_model_name[0])
            predictions = model_predict.predict(df[predict_cols])
            df['PREDICTED'] = predictions
        negative_predictions = df[df['PREDICTED'] == -1]
        negative_predictions['PREDICTED'] = negative_predictions['PREDICTED'].replace(-1, 'TKM')
        negative_predictions = negative_predictions.reset_index(drop=True)
        negative_predictions.index += 1
        formatted_number = f"{len(negative_predictions):,}".replace(',', '.')
        st.warning(f"Ditemukan {formatted_number} transaksi yang diduga mencurigakan.")
        st.dataframe(negative_predictions)
        st.divider()
        if not df_suspected_person_filter.empty:
            st.markdown(f"### Informasi Transaksi dengan Nama Pengirim atau Nama Penerima Tersangka")
            list_pjp_name = get_pjp_suspected_blacklisted_greylisted(df_suspected_person_filter, list_pjp_dki)
            pjp_counts = Counter(list_pjp_name)

            pjp_df = pd.DataFrame(pjp_counts.items(), columns=["PJP Name", "Count"])
            pjp_df = pjp_df.sort_values(by="Count", ascending=False).reset_index(drop=True)

            st.write(f"**Jumlah Data Transaksi**: {len(df_suspected_person_filter):,}")
            df_suspected_person_filter = df_suspected_person_filter.reset_index(drop=True)
            df_suspected_person_filter.index += 1
            df_sus_person = st.data_editor(
                df_suspected_person_filter,
                key="df_suspected_person"
            )
            st.write("**PJP Tersangka:**")
            st.data_editor(
                pjp_df,
                hide_index=True,
                column_config={
                    "PJP Name": "Nama Penyelenggara",
                    "Count": "Jumlah TKM"
                },
                use_container_width=False
            )
            st.divider()
        if not df_blacklisted_filter.empty:
            st.markdown(f"### Informasi Transaksi yang dilakukan {negara_text} Negara Blacklisted")
            list_pjp_name = get_pjp_suspected_blacklisted_greylisted(df_blacklisted_filter, list_pjp_dki)
            pjp_counts = Counter(list_pjp_name)

            if form_no == "FORMG0001":
                list_unique_participating_countries = sorted(list(set(df_blacklisted_filter['NEGARA_TUJUAN'])))
            else:
                list_unique_participating_countries = sorted(list(set(df_blacklisted_filter['NEGARA_ASAL'])))

            list_participating_country = get_country_participated(db, list_unique_participating_countries)
            pjp_df = pd.DataFrame(pjp_counts.items(), columns=["PJP Name", "Count"])
            pjp_df = pjp_df.sort_values(by="Count", ascending=False).reset_index(drop=True)
            st.write(f"**Jumlah Data Transaksi**: {len(df_blacklisted_filter):,}")
            df_blacklisted_filter = df_blacklisted_filter.reset_index(drop=True)
            df_blacklisted_filter.index += 1
            df_blacklisted = st.data_editor(
                df_blacklisted_filter,
                key="df_blacklisted"
            )
            col1, col2 = st.columns(2)
            with col1:
                st.write("**PJP Terlibat:**")
                st.data_editor(
                    pjp_df,
                    hide_index=True,
                    column_config={
                        "PJP Name": "Nama Penyelenggara",
                        "Count": "Jumlah TKM"
                    },
                    use_container_width=True
                )
            with col2:
                st.write("**Negara Terlibat:**")
                st.data_editor(
                    list_participating_country,
                    hide_index=True,
                    column_config={
                        "code": "Kode Negara",
                        "name": "Nama Negara"
                    },
                    use_container_width=True
                )
            st.divider()
        if not df_greylisted_filter.empty:
            st.markdown(f"### Informasi Transaksi yang dilakukan {negara_text} Negara Greylisted")
            list_pjp_name = get_pjp_suspected_blacklisted_greylisted(df_greylisted_filter, list_pjp_dki)
            pjp_counts = Counter(list_pjp_name)

            if form_no == "FORMG0001":
                list_unique_participating_countries = sorted(list(set(df_greylisted_filter['NEGARA_TUJUAN'])))
            else:
                list_unique_participating_countries = sorted(list(set(df_greylisted_filter['NEGARA_ASAL'])))

            list_participating_country = get_country_participated(db, list_unique_participating_countries)

            pjp_df = pd.DataFrame(pjp_counts.items(), columns=["PJP Name", "Count"])
            pjp_df = pjp_df.sort_values(by="Count", ascending=False).reset_index(drop=True)
            st.write(f"**Jumlah Data Transaksi**: {len(df_greylisted_filter):,}")
            df_greylisted_filter = df_greylisted_filter.reset_index(drop=True)
            df_greylisted_filter.index += 1
            df_greylisted = st.data_editor(
                df_greylisted_filter,
                key="df_greylisted"
            )
            col1, col2 = st.columns(2)
            with col1:
                st.write("**PJP Terlibat:**")
                st.data_editor(
                    pjp_df,
                    hide_index=True,
                    column_config={
                        "PJP Name": "Nama Penyelenggara",
                        "Count": "Jumlah TKM"
                    },
                    use_container_width=True
                )
            with col2:
                st.write("**Negara Terlibat:**")
                st.data_editor(
                    list_participating_country,
                    hide_index=True,
                    column_config={
                        "code": "Kode Negara",
                        "name": "Nama Negara"
                    },
                    use_container_width=True
                )
    except Exception as e:
        st.error(f"Error processing files: {e}")
