import pandas as pd
import streamlit as st
from datetime import date

from service.formatting import format_id_percent
import calendar

from service.preprocess import *
from service.visualize import *
from service.database import *


# Rules multilicense: aktif mulai tanggal efektif (inclusive)
_MULTILICENSE_RULES: list[dict] = [
    {"sandi": "777930115", "pjp": "Brankas Teknologi Indonesia", "effective": date(2024, 9, 20)},
    {"sandi": "777930112", "pjp": "Durian Pay Indonesia", "effective": date(2025, 6, 25)},
    {"sandi": "777962497", "pjp": "Ionpay Network", "effective": date(2021, 7, 1)},
    {"sandi": "777930038", "pjp": "Kharisma Catur Mandala", "effective": date(2021, 7, 1)},
    {"sandi": "777962104", "pjp": "MCP Indo Utama", "effective": date(2021, 7, 1)},
    {"sandi": "777930118", "pjp": "Smart Fintech For You", "effective": date(2024, 4, 24)},
]


def _norm_text(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def _month_to_int(value) -> int | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        m = int(value)
        return m if 1 <= m <= 12 else None

    s = str(value).strip().lower()
    if not s:
        return None
    if s.isdigit():
        m = int(s)
        return m if 1 <= m <= 12 else None

    month_en = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    month_id = {
        "januari": 1, "februari": 2, "maret": 3, "april": 4,
        "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
        "september": 9, "oktober": 10, "november": 11, "desember": 12,
    }
    return month_en.get(s) or month_id.get(s)


def _effective_period_date(df: pd.DataFrame) -> pd.Series:
    year = pd.to_numeric(df.get("Year"), errors="coerce")
    if "Month" in df.columns:
        month_series = df["Month"].map(_month_to_int)
    elif "Quarter" in df.columns:
        q = pd.to_numeric(df["Quarter"], errors="coerce")
        month_series = (q * 3).astype("Int64")
    else:
        month_series = pd.Series([12] * len(df), index=df.index)

    month_num = pd.to_numeric(month_series, errors="coerce")
    out = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    valid = year.notna() & month_num.notna()
    if valid.any():
        y = year[valid].astype(int)
        m = month_num[valid].astype(int)
        out.loc[valid] = pd.to_datetime({"year": y, "month": m, "day": 1}, errors="coerce") + pd.offsets.MonthEnd(0)
    return out


def _multilicense_mask(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty:
        return pd.Series([], dtype=bool)

    name_col = "Nama PJP" if "Nama PJP" in df.columns else ("PJP" if "PJP" in df.columns else None)
    code_candidates = ["Sandi PJP", "Sandi_PJP", "SandiPJP", "Kode PJP", "Kode_PJP", "Kode"]
    code_col = next((c for c in code_candidates if c in df.columns), None)

    if name_col is None and code_col is None:
        return pd.Series([False] * len(df), index=df.index)

    period_date = _effective_period_date(df)
    name_norm = df[name_col].astype(str).map(_norm_text) if name_col else pd.Series([""] * len(df), index=df.index)
    code_norm = (
        df[code_col].astype("string").str.replace(r"\D", "", regex=True).fillna("").astype(str)
        if code_col else pd.Series([""] * len(df), index=df.index)
    )

    mask = pd.Series([False] * len(df), index=df.index)
    for rule in _MULTILICENSE_RULES:
        r_name = _norm_text(rule.get("pjp"))
        r_code = str(rule.get("sandi", "")).strip()
        r_date = pd.Timestamp(rule.get("effective"))

        hit_name = (name_norm == r_name) if r_name else pd.Series([False] * len(df), index=df.index)
        hit_code = (code_norm == r_code) if r_code else pd.Series([False] * len(df), index=df.index)
        hit_entity = hit_name | hit_code
        hit_period = period_date.notna() & (period_date >= r_date)
        mask = mask | (hit_entity & hit_period)

    return mask


def _apply_multilicense_mode(df: pd.DataFrame, mode: str) -> tuple[pd.DataFrame, pd.Series]:
    if df is None or df.empty:
        return df, pd.Series([], dtype=bool)
    mask_ml = _multilicense_mask(df)
    if str(mode) == "exclude":
        return df.loc[~mask_ml].copy(), mask_ml
    return df.copy(), mask_ml

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
    else:
        st.info(
            "Referensi PJP dari database tidak tersedia saat ini; "
            "filter DKI tidak diterapkan (menggunakan data dari file)."
        )

        with st.sidebar:
            with st.expander("Filter Multilicense", True):
                ml_mode_ui = st.radio(
                    "Mode Perhitungan",
                    options=["Termasuk Multilicense", "Tanpa Multilicense"],
                    index=0,
                    key="summary_multilicense_mode",
                    help="Tanpa Multilicense = data multilicense aktif (sesuai tanggal efektif) dikeluarkan.",
                )
                ml_mode = "exclude" if ml_mode_ui == "Tanpa Multilicense" else "include"
                _df_before_ml = df
                df, _ml_mask = _apply_multilicense_mode(_df_before_ml, ml_mode)

                total_rows = int(len(_df_before_ml)) if _df_before_ml is not None else 0
                ml_rows = int(_ml_mask.sum()) if len(_ml_mask) else 0
                shown_rows = int(len(df)) if df is not None else 0
                st.caption(f"Baris data: total {total_rows:,} | multilicense aktif {ml_rows:,} | digunakan {shown_rows:,}")

    # Normalize time columns safely to avoid IntCastingNaNError
    time_cols = ['Year', 'Quarter', 'Month']
    for col in time_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').replace([float('inf'), float('-inf')], pd.NA)

    invalid_time_mask = (
        df['Year'].isna()
        | df['Quarter'].isna()
        | df['Month'].isna()
        | ~df['Quarter'].between(1, 4)
        | ~df['Month'].between(1, 12)
    )

    if invalid_time_mask.any():
        dropped_rows = int(invalid_time_mask.sum())
        st.warning(
            f"{dropped_rows} baris diabaikan karena nilai Year/Quarter/Month kosong atau tidak valid."
        )
        df = df.loc[~invalid_time_mask].copy()

    if df.empty:
        st.error("Tidak ada data valid setelah pembersihan kolom waktu (Year/Quarter/Month).")
        st.stop()

    df[time_cols] = df[time_cols].astype('int64')

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
