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


# PJP dengan izin dicabut (dikeluarkan dari perhitungan pada mode "Tanpa Dicabut").
# Tidak memakai tanggal efektif: seluruh periode dikeluarkan saat mode exclude.
_REVOKED_RULES: list[dict] = [
    {"sandi": "777930075", "pjp": "KSP Indosurya Cipta", "note": "Dicabut"},
    {"sandi": "777958129", "pjp": "PT Aryadana", "note": "Dicabut"},
    {"sandi": "777930081", "pjp": "PT Asia Fintek Teknologi", "note": "Dicabut"},
    {"sandi": "777958117", "pjp": "PT Dhasatra Moneytransfer", "note": "Dicabut"},
    {"sandi": "777930064", "pjp": "PT Dompet Harapan Bangsa", "note": "Dicabut"},
    {"sandi": "777930100", "pjp": "PT Giat Bangun Indonesia", "note": "Dicabut"},
    {"sandi": "777958116", "pjp": "PT Indomarco Prismatama", "note": "Dicabut"},
    {"sandi": "777930045", "pjp": "PT Media Indonusa", "note": "Dicabut"},
    {"sandi": "777930028", "pjp": "PT Nusa Ekspresstama Remmitance", "note": "Dicabut"},
    {"sandi": "777958113", "pjp": "PT Tiki Jalur Nugraha Ekakurir", "note": "Dicabut"},
    {"sandi": "777111113", "pjp": "PT Tranglo Indonesia", "note": "Dicabut atas Permintaan sendiri"},
]


def _norm_text(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def _effective_period_date(df: pd.DataFrame) -> pd.Series:
    year = pd.to_numeric(df.get("Year"), errors="coerce")
    if "Month" in df.columns:
        month_series = df["Month"].map(month_to_number)
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


def _revoked_mask(df: pd.DataFrame) -> pd.Series:
    """Tandai baris PJP yang izinnya dicabut (match by sandi/nama, tanpa tanggal)."""
    if df is None or df.empty:
        return pd.Series([], dtype=bool)

    name_col = "Nama PJP" if "Nama PJP" in df.columns else ("PJP" if "PJP" in df.columns else None)
    code_candidates = ["Sandi PJP", "Sandi_PJP", "SandiPJP", "Kode PJP", "Kode_PJP", "Kode"]
    code_col = next((c for c in code_candidates if c in df.columns), None)

    if name_col is None and code_col is None:
        return pd.Series([False] * len(df), index=df.index)

    if name_col is not None:
        name_norm = df[name_col].astype(str).map(_norm_text)
    else:
        name_norm = pd.Series([""] * len(df), index=df.index)

    if code_col is not None:
        code_norm = (
            df[code_col]
            .astype("string")
            .str.replace(r"\D", "", regex=True)
            .fillna("")
            .astype(str)
        )
    else:
        code_norm = pd.Series([""] * len(df), index=df.index)

    mask = pd.Series([False] * len(df), index=df.index)
    for rule in _REVOKED_RULES:
        r_name = _norm_text(rule.get("pjp"))
        r_code = str(rule.get("sandi", "")).strip()

        hit_name = (name_norm == r_name) if r_name else pd.Series([False] * len(df), index=df.index)
        hit_code = (code_norm == r_code) if r_code else pd.Series([False] * len(df), index=df.index)
        mask = mask | (hit_name | hit_code)

    return mask


def _apply_revoked_mode(df: pd.DataFrame, mode: str) -> tuple[pd.DataFrame, pd.Series]:
    if df is None or df.empty:
        return df, pd.Series([], dtype=bool)
    mask_rv = _revoked_mask(df)
    if str(mode) == "exclude":
        return df.loc[~mask_rv].copy(), mask_rv
    return df.copy(), mask_rv


def _year_index(years: list[int], value, fallback: int) -> int:
    """Posisi tahun pada daftar selectbox, jatuh ke fallback bila tidak ada."""
    try:
        return years.index(int(value))
    except (TypeError, ValueError):
        return fallback


def _range_defaults(df: pd.DataFrame, mode: str, years: list[int]):
    """Default rentang filter = seluruh periode yang tersedia pada data."""
    bounds = period_bounds(df, mode)
    if bounds:
        return bounds
    if mode == "year":
        return (years[0], None), (years[-1], None)
    return (years[0], 1), (years[-1], 12 if mode == "month" else 4)


# Nama kolom tampilan disamakan dengan tabel Market Share di atasnya, supaya
# istilah yang dibaca pengguna konsisten di seluruh halaman.
_BUNDLING_RENAME = {
    "Sum of Total Jumlah": "Total Frekuensi Seluruh Transaksi",
    "Sum of Total Nom": "Total Nominal Seluruh Transaksi",
    "Sum of Fin Jumlah Inc": "Total Frekuensi Incoming",
    "Sum of Fin Jumlah Out": "Total Frekuensi Outgoing",
    "Sum of Fin Jumlah Dom": "Total Frekuensi Domestik",
    "Sum of Fin Nilai Inc": "Total Nominal Incoming",
    "Sum of Fin Nilai Out": "Total Nominal Outgoing",
    "Sum of Fin Nilai Dom": "Total Nominal Domestik",
    "Kode": "Sandi PJP",
}

_BUNDLING_TEXT_COLUMNS = ("Bundling", "Sandi PJP", "Nama PJP")


def _bundling_table_format(df: pd.DataFrame) -> dict:
    """Formatter kolom tabel bundling: persen gaya ID, sisanya ribuan bulat."""

    def _count(x):
        return '{:,.0f}'.format(x)

    def _percent(x):
        return format_id_percent(x, decimals=2, show_sign=False,
                                 none='-', space_before_percent=True)

    return {
        col: (_percent if col.endswith("(%)") else _count)
        for col in df.columns
        if col not in _BUNDLING_TEXT_COLUMNS
    }


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

            with st.expander("Filter PJP Dicabut", True):
                rv_mode_ui = st.radio(
                    "Mode Perhitungan",
                    options=["Termasuk PJP Dicabut", "Tanpa PJP Dicabut"],
                    index=0,
                    key="summary_revoked_mode",
                    help="Tanpa PJP Dicabut = data PJP yang izinnya dicabut dikeluarkan dari seluruh periode.",
                )
                rv_mode = "exclude" if rv_mode_ui == "Tanpa PJP Dicabut" else "include"
                _df_before_rv = df
                df, _rv_mask = _apply_revoked_mode(_df_before_rv, rv_mode)

                base_rows = int(len(_df_before_rv)) if _df_before_rv is not None else 0
                rv_rows = int(_rv_mask.sum()) if len(_rv_mask) else 0
                shown_rows = int(len(df)) if df is not None else 0
                st.caption(f"Baris data: total {base_rows:,} | PJP dicabut {rv_rows:,} | digunakan {shown_rows:,}")

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
    unique_years = sorted(int(y) for y in df['Year'].unique())
    month_names = [calendar.month_name[m] for m in range(1, 13)]
    quarter_labels = [f"Q{q}" for q in range(1, 5)]

    with st.sidebar:
        with st.expander("Filter Market Share", True):
            selected_pjp = st.selectbox('Select PJP:', pjp_list)

            ms_start, ms_end = _range_defaults(df, 'quarter', unique_years)

            col_ms_y1, col_ms_q1 = st.columns(2)
            with col_ms_y1:
                ms_start_year = st.selectbox(
                    'Start Year:', unique_years,
                    index=_year_index(unique_years, ms_start[0], 0),
                    key="ms_start_year",
                )
            with col_ms_q1:
                ms_start_quarter = st.selectbox(
                    'Start Quarter:', quarter_labels,
                    index=int(ms_start[1]) - 1,
                    key="ms_start_quarter",
                )

            col_ms_y2, col_ms_q2 = st.columns(2)
            with col_ms_y2:
                ms_end_year = st.selectbox(
                    'End Year:', unique_years,
                    index=_year_index(unique_years, ms_end[0], len(unique_years) - 1),
                    key="ms_end_year",
                )
            with col_ms_q2:
                ms_end_quarter = st.selectbox(
                    'End Quarter:', quarter_labels,
                    index=int(ms_end[1]) - 1,
                    key="ms_end_quarter",
                )

            ms_start_q = quarter_labels.index(ms_start_quarter) + 1
            ms_end_q = quarter_labels.index(ms_end_quarter) + 1
            ms_lo, ms_hi = (ms_start_year, ms_start_q), (ms_end_year, ms_end_q)
            if period_to_ordinal('quarter', *ms_lo) > period_to_ordinal('quarter', *ms_hi):
                ms_lo, ms_hi = ms_hi, ms_lo
                st.warning("Kuartal awal lebih akhir dari kuartal akhir; rentang dibalik otomatis.")

            st.caption(
                "Rentang: "
                f"{format_period_label('quarter', *ms_lo)} s.d. "
                f"{format_period_label('quarter', *ms_hi)}"
            )

        with st.expander("Filter Transactions", True):
            time_option = st.selectbox("Choose Time Period:", ("Month", "Quarter", "Year"))
            period_mode = normalize_period_mode(time_option)
            is_month = period_mode == "month"

            trx_start, trx_end = _range_defaults(df, period_mode, unique_years)

            if period_mode == "year":
                trx_start_period = trx_end_period = None
                col_trx_y1, col_trx_y2 = st.columns(2)
                with col_trx_y1:
                    trx_start_year = st.selectbox(
                        'Start Year:', unique_years,
                        index=_year_index(unique_years, trx_start[0], 0),
                        key="trx_start_year_year",
                    )
                with col_trx_y2:
                    trx_end_year = st.selectbox(
                        'End Year:', unique_years,
                        index=_year_index(unique_years, trx_end[0], len(unique_years) - 1),
                        key="trx_end_year_year",
                    )
            else:
                period_options = month_names if is_month else quarter_labels
                period_word = "Month" if is_month else "Quarter"

                col_trx_y1, col_trx_p1 = st.columns(2)
                with col_trx_y1:
                    trx_start_year = st.selectbox(
                        'Start Year:', unique_years,
                        index=_year_index(unique_years, trx_start[0], 0),
                        key=f"trx_start_year_{period_mode}",
                    )
                with col_trx_p1:
                    trx_start_label = st.selectbox(
                        f'Start {period_word}:', period_options,
                        index=int(trx_start[1]) - 1,
                        key=f"trx_start_period_{period_mode}",
                    )

                col_trx_y2, col_trx_p2 = st.columns(2)
                with col_trx_y2:
                    trx_end_year = st.selectbox(
                        'End Year:', unique_years,
                        index=_year_index(unique_years, trx_end[0], len(unique_years) - 1),
                        key=f"trx_end_year_{period_mode}",
                    )
                with col_trx_p2:
                    trx_end_label = st.selectbox(
                        f'End {period_word}:', period_options,
                        index=int(trx_end[1]) - 1,
                        key=f"trx_end_period_{period_mode}",
                    )

                trx_start_period = period_options.index(trx_start_label) + 1
                trx_end_period = period_options.index(trx_end_label) + 1

            trx_lo = (trx_start_year, trx_start_period)
            trx_hi = (trx_end_year, trx_end_period)
            if period_to_ordinal(period_mode, *trx_lo) > period_to_ordinal(period_mode, *trx_hi):
                trx_lo, trx_hi = trx_hi, trx_lo
                st.warning("Periode awal lebih akhir dari periode akhir; rentang dibalik otomatis.")

            st.caption(
                "Rentang: "
                f"{format_period_label(period_mode, *trx_lo)} s.d. "
                f"{format_period_label(period_mode, *trx_hi)}"
            )

    df_preprocessed = preprocess_data(df)
    df_preprocessed_time = preprocess_data(df, is_trx=True)

    df_market_share_range = filter_period_range(df_preprocessed, 'quarter',
                                                ms_start_year, ms_end_year,
                                                ms_start_q, ms_end_q)
    filtered_df = filter_data(df=df_market_share_range,
                              selected_pjp=selected_pjp,
                              group_by_pjp=True)

    filtered_df_time = filter_period_range(df_preprocessed_time, period_mode,
                                           trx_start_year, trx_end_year,
                                           trx_start_period, trx_end_period)

    if filtered_df.empty:
        st.warning("Tidak ada data Market Share pada rentang periode yang dipilih. Perlebar rentangnya.")
        st.stop()

    if filtered_df_time.empty:
        st.warning("Tidak ada data transaksi pada rentang periode yang dipilih. Perlebar rentangnya.")
        st.stop()

    df_sum_time = sum_data_time(filtered_df_time, is_month, mode=period_mode)

    total_sum_of_nom = filtered_df['Sum of Total Nom'].sum()
    df_with_market_share = calculate_market_share(filtered_df, total_sum_of_nom)

    df_sum_time = df_sum_time[(df_sum_time['Sum of Fin Jumlah Inc'] != 0) & (df_sum_time['Sum of Fin Nilai Inc'] != 0) &
                              (df_sum_time['Sum of Fin Jumlah Out'] != 0) & (df_sum_time['Sum of Fin Nilai Out'] != 0) &
                              (df_sum_time['Sum of Fin Jumlah Dom'] != 0) & (df_sum_time['Sum of Fin Nilai Dom'] != 0)]

    if df_sum_time.empty:
        st.warning("Tidak ada periode dengan transaksi lengkap pada rentang yang dipilih. Perlebar rentangnya.")
        st.stop()

    df_sum_time['Periode'] = build_period_label(df_sum_time, period_mode)

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
        make_grouped_bar_chart(df_sum_time, "Jumlah", is_month,
                               time_label='Periode', title_label=time_option)
    with col3:
        make_grouped_bar_chart(df_sum_time, "Nilai", is_month,
                               time_label='Periode', title_label=time_option)

    df_sum_time = df_sum_time.drop(columns=['Periode'])

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

    st.divider()
    st.subheader("Transaksi per Bundling")

    if not has_bundling(df):
        st.info(
            "Kolom 'Bundling' tidak ada atau kosong pada sheet 'Trx_PJPJKT'. "
            "Unggah file yang sudah memuat kolom Bundling untuk melihat ringkasan ini."
        )
    else:
        st.caption(
            "Mengikuti rentang Filter Transactions: "
            f"{format_period_label(period_mode, *trx_lo)} s.d. "
            f"{format_period_label(period_mode, *trx_hi)}"
        )

        bundling_metric = st.radio(
            "Ukuran yang ditampilkan:",
            ("Nominal", "Frekuensi"),
            horizontal=True,
            key="bundling_metric",
        )
        is_nominal_bundling = bundling_metric == "Nominal"
        bundling_value_col = 'Sum of Total Nom' if is_nominal_bundling else 'Sum of Total Jumlah'

        # Dihitung ulang dari baris mentah: kolom Bundling ikut terbuang saat data
        # diagregasi per PJP untuk bagian atas halaman.
        df_bundling_rows = filter_period_range(df, period_mode,
                                               trx_start_year, trx_end_year,
                                               trx_start_period, trx_end_period)
        df_bundling_total = aggregate_by_bundling(df_bundling_rows)

        if df_bundling_total.empty:
            st.warning("Tidak ada data bundling pada rentang periode yang dipilih.")
        else:
            df_bundling_period = aggregate_by_bundling(df_bundling_rows, period_mode=period_mode)
            df_bundling_period['Periode'] = build_period_label(df_bundling_period, period_mode)

            col_b1, col_b2 = st.columns([2, 3])
            with col_b1:
                make_bundling_share_chart(df_bundling_total, bundling_value_col,
                                          bundling_metric, key="bundling_share")
            with col_b2:
                make_bundling_trend_chart(df_bundling_period, bundling_value_col, 'Periode',
                                          bundling_metric, is_nominal_bundling,
                                          key="bundling_trend")

            df_bundling_summary = add_share_column(df_bundling_total, 'Sum of Total Nom',
                                                   'Share Nominal (%)')
            df_bundling_summary = add_share_column(df_bundling_summary, 'Sum of Total Jumlah',
                                                   'Share Frekuensi (%)')
            df_bundling_summary['Rata-rata Nominal per Transaksi'] = (
                df_bundling_summary['Sum of Total Nom']
                / df_bundling_summary['Sum of Total Jumlah'].replace(0, pd.NA)
            )
            df_bundling_summary = (
                df_bundling_summary
                .sort_values('Sum of Total Nom', ascending=False, ignore_index=True)
                .rename(columns=_BUNDLING_RENAME)
            )
            df_bundling_summary = df_bundling_summary[[
                "Bundling", "Jumlah PJP",
                "Total Frekuensi Seluruh Transaksi", "Total Nominal Seluruh Transaksi",
                "Share Frekuensi (%)", "Share Nominal (%)", "Rata-rata Nominal per Transaksi",
                "Total Frekuensi Incoming", "Total Frekuensi Outgoing", "Total Frekuensi Domestik",
                "Total Nominal Incoming", "Total Nominal Outgoing", "Total Nominal Domestik",
            ]]

            st.dataframe(
                df_bundling_summary.style.format(
                    _bundling_table_format(df_bundling_summary),
                    thousands=".",
                    decimal=",",
                ),
                use_container_width=True,
                hide_index=True,
            )

            with st.expander("Detail PJP per Bundling", False):
                df_bundling_pjp = aggregate_by_bundling(df_bundling_rows, by_pjp=True)

                # Porsi dalam bundling dihitung sebelum penyaringan, supaya angkanya
                # tetap relatif terhadap bundling penuh dan bukan terhadap yang tampil.
                group_total = df_bundling_pjp.groupby("Bundling")['Sum of Total Nom'].transform('sum')
                df_bundling_pjp['Share dalam Bundling (%)'] = round_half_up_series(
                    df_bundling_pjp['Sum of Total Nom'] / group_total.replace(0, pd.NA) * 100, 2
                )
                df_bundling_pjp = add_share_column(df_bundling_pjp, 'Sum of Total Nom',
                                                   'Share Keseluruhan (%)')

                bundling_options = ["Semua"] + sort_bundling_labels(df_bundling_pjp["Bundling"])
                selected_bundling = st.selectbox("Pilih Bundling:", bundling_options,
                                                 key="bundling_detail_pick")
                if selected_bundling != "Semua":
                    df_bundling_pjp = df_bundling_pjp[df_bundling_pjp["Bundling"] == selected_bundling]

                df_bundling_pjp = (
                    df_bundling_pjp
                    .sort_values('Sum of Total Nom', ascending=False, ignore_index=True)
                    .rename(columns=_BUNDLING_RENAME)
                )
                detail_cols = ["Bundling"]
                if "Sandi PJP" in df_bundling_pjp.columns:
                    # Sandi sebagai teks: angkanya identitas, bukan nilai yang dijumlahkan.
                    df_bundling_pjp["Sandi PJP"] = df_bundling_pjp["Sandi PJP"].astype("string")
                    detail_cols.append("Sandi PJP")
                detail_cols += [
                    "Nama PJP",
                    "Total Frekuensi Seluruh Transaksi", "Total Nominal Seluruh Transaksi",
                    "Share dalam Bundling (%)", "Share Keseluruhan (%)",
                    "Total Nominal Incoming", "Total Nominal Outgoing", "Total Nominal Domestik",
                ]
                df_bundling_pjp = df_bundling_pjp[detail_cols]

                st.caption(f"{len(df_bundling_pjp)} PJP ditampilkan.")
                st.dataframe(
                    df_bundling_pjp.style.format(
                        _bundling_table_format(df_bundling_pjp),
                        thousands=".",
                        decimal=",",
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
else:
    st.warning("You Must Upload an Excel File.")
