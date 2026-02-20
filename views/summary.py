import pandas as pd
import streamlit as st

from service.formatting import format_id_percent
import calendar

from service.preprocess import *
from service.visualize import *
from service.database import *

# Initial Page Setup
set_page_visuals("viz")

# DB reference data is optional; fetch it only when needed.
if "_pjp_reference_cache" not in st.session_state:
    st.session_state["_pjp_reference_cache"] = None

if 'df' not in st.session_state:
    st.session_state['df'] = None
if 'df_national' not in st.session_state:
    st.session_state['df_national'] = None
if 'file_name' not in st.session_state:
    st.session_state['file_name'] = None

uploaded_file = st.file_uploader("Choose an Excel file",
                                 type=["xlsx", "xls"],
                                 help="Pastikan upload file Excel Data LTDBB PJP LR JKT yang memiliki dua worksheet, yaitu: 'Trx_PJPJKT' dan 'Raw_JKTNasional'.")

if uploaded_file is not None:
    file_name = uploaded_file.name

    if file_name != st.session_state['file_name']:
        st.session_state['file_name'] = file_name
        df = load_data(uploaded_file, False)
        df_national = load_data(uploaded_file, True)
        st.session_state['df'] = df
        st.session_state['df_national'] = df_national
    else:
        df = st.session_state['df']
        df_national = st.session_state['df_national']
else:
    df = st.session_state['df']
    df_national = st.session_state['df_national']

if df is not None and df_national is not None:
    # Optional DB-based filter for DKI PJP reference
    if st.session_state.get("_pjp_reference_cache") is None:
        db = connect_db_safe()
        if db is not None:
            try:
                st.session_state["_pjp_reference_cache"] = get_pjp_jkt(db)
            except Exception:
                st.session_state["_pjp_reference_cache"] = []
        else:
            st.session_state["_pjp_reference_cache"] = []

    list_pjp_dki = st.session_state.get("_pjp_reference_cache") or []

    with st.sidebar:
        if st.button("Retry koneksi DB", use_container_width=True, type="secondary"):
            st.session_state["_pjp_reference_cache"] = None
            st.session_state.pop("_tools_ltdbb_db_last_error", None)
            st.rerun()

    show_db_error_banner(clear=False)

    if list_pjp_dki:
        list_pjp_code_dki = []
        for pjp in list_pjp_dki:
            try:
                list_pjp_code_dki.append(int(pjp['code']))
            except Exception:
                continue

        if list_pjp_code_dki:
            df = df[df['Kode'].isin(list_pjp_code_dki)]
            st.session_state['df'] = df
    else:
        st.info(
            "Referensi PJP dari database tidak tersedia saat ini; "
            "filter DKI tidak diterapkan (menggunakan data dari file)."
        )

    if not df['Year'].dtype == 'int64':
        df['Year'] = df['Year'].astype('int64')
    if not df['Quarter'].dtype == 'int64':
        df['Quarter'] = df['Quarter'].astype('int64')
    if not df['Month'].dtype == 'int64':
        df['Month'] = df['Month'].astype('int64')

    pjp_list = ['All'] + df['Nama PJP'].unique().tolist()
    years = ['All'] + list(df['Year'].unique())
    quarters = ['All'] + list(df['Quarter'].unique())
    months = ['All'] + [calendar.month_name[m] for m in df['Month'].unique()]

    with st.sidebar:
        with st.expander("Filter Market Share", True):
            selected_pjp = st.selectbox('Select PJP:', pjp_list)
            selected_year_pjp = st.selectbox('Select Year:', years, key="key_year_pjp")
            selected_quarter_pjp = st.selectbox('Select Quarter:', quarters, key="key_quarter_pjp")
        with st.expander("Filter Transactions", True):
            time_option = st.selectbox("Choose Time Period:", ("Month", "Quarter"))
            selected_year = st.selectbox('Select Year:', years, key="key_year_trx")

            if time_option == 'Month':
                selected_month = st.selectbox('Select Month:', months, key="key_month_trx")
            else:
                selected_quarter = st.selectbox('Select Quarter:', quarters, key="key_quarter_trx")

    df_preprocessed = preprocess_data(df)
    df_preprocessed_time = preprocess_data(df, is_trx=True)

    filtered_df = filter_data(df=df_preprocessed,
                              selected_pjp=selected_pjp,
                              selected_quarter=selected_quarter_pjp,
                              selected_year=selected_year_pjp,
                              group_by_pjp=True)

    if time_option == "Month":
        filtered_df_time = filter_data(df=df_preprocessed_time,
                                       selected_year=selected_year,
                                       selected_month=selected_month)
        is_month = True
    else:
        filtered_df_time = filter_data(df=df_preprocessed_time,
                                       selected_year=selected_year,
                                       selected_quarter=selected_quarter)
        is_month = False

    df_sum_time = sum_data_time(filtered_df_time, is_month)

    total_sum_of_nom = filtered_df['Sum of Total Nom'].sum()
    df_with_market_share = calculate_market_share(filtered_df, total_sum_of_nom)

    df_sum_time = df_sum_time[(df_sum_time['Sum of Fin Jumlah Inc'] != 0) & (df_sum_time['Sum of Fin Nilai Inc'] != 0) &
                              (df_sum_time['Sum of Fin Jumlah Out'] != 0) & (df_sum_time['Sum of Fin Nilai Out'] != 0) &
                              (df_sum_time['Sum of Fin Jumlah Dom'] != 0) & (df_sum_time['Sum of Fin Nilai Dom'] != 0)]

    grand_total_inc_nominal = int(df_sum_time['Sum of Fin Nilai Inc'].sum())
    grand_total_inc_jumlah = int(df_sum_time['Sum of Fin Jumlah Inc'].sum())
    grand_total_out_nominal = int(df_sum_time['Sum of Fin Nilai Out'].sum())
    grand_total_out_jumlah = int(df_sum_time['Sum of Fin Jumlah Out'].sum())
    grand_total_dom_nominal = int(df_sum_time['Sum of Fin Nilai Dom'].sum())
    grand_total_dom_jumlah = int(df_sum_time['Sum of Fin Jumlah Dom'].sum())

    grand_total_nominal = int(df_sum_time['Sum of Total Nom'].sum())
    grand_total_frequency = int(df_sum_time['Sum of Fin Jumlah Inc'].sum() +
                                df_sum_time['Sum of Fin Jumlah Out'].sum() +
                                df_sum_time['Sum of Fin Jumlah Dom'].sum())

    col1 = st.columns(1)
    with col1[0]:
        top_n = 5
        make_pie_chart_summary(df_with_market_share, top_n)

    df_with_market_share.index = df_with_market_share.index + 1

    df_with_market_share.rename(columns={
        "Sum of Total Jumlah": "Total Frekuensi Seluruh Transaksi",
        "Sum of Total Nom": "Total Nominal Seluruh Transaksi",
        "Sum of Fin Nilai Out": "Total Nominal Outgoing",
        "Sum of Fin Nilai Inc": "Total Nominal Incoming",
        "Sum of Fin Nilai Dom": "Total Nominal Domestik",
        "Sum of Fin Jumlah Out": "Total Frekuensi Outgoing",
        "Sum of Fin Jumlah Inc": "Total Frekuensi Incoming",
        "Sum of Fin Jumlah Dom": "Total Frekuensi Domestik",
        "Market Share (%)": "Market Share (%)"
    }, inplace=True)

    df_with_market_share = df_with_market_share.style.format(
        {
            "Total Frekuensi Seluruh Transaksi": lambda x: '{:,.0f}'.format(x),
            "Total Nominal Seluruh Transaksi": lambda x: '{:,.0f}'.format(x),
            "Total Nominal Outgoing": lambda x: '{:,.0f}'.format(x),
            "Total Nominal Incoming": lambda x: '{:,.0f}'.format(x),
            "Total Nominal Domestik": lambda x: '{:,.0f}'.format(x),
            "Total Frekuensi Outgoing": lambda x: '{:,.0f}'.format(x),
            "Total Frekuensi Incoming": lambda x: '{:,.0f}'.format(x),
            "Total Frekuensi Domestik": lambda x: '{:,.0f}'.format(x),
            "Market Share (%)": lambda x: format_id_percent(x, decimals=2, show_sign=False, none='-', space_before_percent=True),
        },
        thousands=".",
        decimal=",",
    )

    st.dataframe(df_with_market_share, use_container_width=True)
    col2, col3 = st.columns(2)
    with col2:
        make_grouped_bar_chart(df_sum_time, "Jumlah", is_month)
    with col3:
        make_grouped_bar_chart(df_sum_time, "Nilai", is_month)

    df_sum_time.rename(columns={
        "Sum of Total Nom": "Total Nominal Seluruh Transaksi",
        "Sum of Fin Nilai Out": "Total Nominal Outgoing",
        "Sum of Fin Nilai Inc": "Total Nominal Incoming",
        "Sum of Fin Nilai Dom": "Total Nominal Domestik",
        "Sum of Fin Jumlah Out": "Total Frekuensi Outgoing",
        "Sum of Fin Jumlah Inc": "Total Frekuensi Incoming",
        "Sum of Fin Jumlah Dom": "Total Frekuensi Domestik",
    }, inplace=True)

    df_sum_time = df_sum_time.style.format(
        {
            "Year": lambda x: "{:.0f}".format(x),
            "Total Nominal Seluruh Transaksi": lambda x: '{:,.0f}'.format(x),
            "Total Nominal Outgoing": lambda x: '{:,.0f}'.format(x),
            "Total Nominal Incoming": lambda x: '{:,.0f}'.format(x),
            "Total Nominal Domestik": lambda x: '{:,.0f}'.format(x),
            "Total Frekuensi Outgoing": lambda x: '{:,.0f}'.format(x),
            "Total Frekuensi Incoming": lambda x: '{:,.0f}'.format(x),
            "Total Frekuensi Domestik": lambda x: '{:,.0f}'.format(x),
        },
        thousands=".",
        decimal=",",
    )

    st.dataframe(df_sum_time, use_container_width=True, hide_index=True)

    df_grand_totals = pd.DataFrame({
        'Category': ['Incoming', 'Outgoing', 'Domestic', 'All'],
        'Grand Total Jumlah': [grand_total_inc_jumlah, grand_total_out_jumlah, grand_total_dom_jumlah,
                               grand_total_frequency],
        'Grand Total Nominal': [grand_total_inc_nominal, grand_total_out_nominal, grand_total_dom_nominal,
                                grand_total_nominal]
    })
    df_grand_totals = df_grand_totals.style.format(
        {
            "Grand Total Jumlah": lambda x: '{:,.0f}'.format(x),
            "Grand Total Nominal": lambda x: '{:,.0f}'.format(x)
        },
        thousands=".",
        decimal=",",
    )
    st.dataframe(df_grand_totals, use_container_width=True, hide_index=True)
else:
    st.warning("You Must Upload an Excel File.")
