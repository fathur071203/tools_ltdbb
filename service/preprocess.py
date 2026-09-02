import pandas as pd
import streamlit as st
import calendar
import numpy as np
from io import BytesIO
from datetime import datetime

from service.units import pick_rupiah_unit, rupiah_unit_suffix
from service.formatting import (
    format_id_decimal,
    format_id_percent,
    parse_number,
    qround_float,
)


def _to_number(series: pd.Series) -> pd.Series:
    """Convert a messy numeric-like column to floats, deciding value by value.

    Excel exports mix genuine numbers with human-typed text (``'742.580.600'``,
    ``'248,294,749,080'``). Inferring the separator meaning from the column as a
    whole is unsafe: a handful of text cells would change how every real float in
    that column is read, either stripping its decimal point or turning it into
    NaN. ``parse_number`` applies the rules per value instead, and leaves values
    that are already numeric untouched.
    """
    if pd.api.types.is_numeric_dtype(series):
        return series

    return pd.to_numeric(series.map(lambda v: parse_number(v)), errors="coerce")


def _coerce_numeric_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = _to_number(df[col])
    return df


# Kolom nilai final (Fin ...) pada sheet Trx_PJPJKT, yaitu kolom M s.d. R.
# Kolom G s.d. L ("Jumlah Inc", "Nilai Inc", dst) adalah versi sebelum
# pembulatan/koreksi dan tidak dipakai di seluruh aplikasi.
PJP_VALUE_COLUMNS = [
    'Fin Jumlah Inc', 'Fin Nilai Inc',
    'Fin Jumlah Out', 'Fin Nilai Out',
    'Fin Jumlah Dom', 'Fin Nilai Dom',
]

NATIONAL_VALUE_COLUMNS = [
    'Nom Nasional Out', 'Nom Nasional Inc', 'Nom Nasional Dom', 'Nom Nasional Total',
    'Frek Nasional Out', 'Frek Nasional Inc', 'Frek Nasional Dom', 'Frek Nasional Total',
]


def round_half_up(value, decimals: int = 2):
    """Round a scalar half-up, returning NaN instead of None for missing input.

    numpy/pandas ``round`` breaks ties to even (2.675 -> 2.67), which does not
    match how these figures are reported. Every displayed number goes through
    this so the same input always yields the same output.
    """
    out = qround_float(value, decimals=decimals)
    return np.nan if out is None else out


def round_half_up_series(series: pd.Series, decimals: int = 2) -> pd.Series:
    """Vectorised counterpart of :func:`round_half_up` for a column."""
    numeric = pd.to_numeric(series, errors='coerce')
    return numeric.map(lambda v: round_half_up(v, decimals))


def _drop_non_data_rows(df: pd.DataFrame, key_cols: list[str]) -> pd.DataFrame:
    """Drop spreadsheet leftovers that sit below the real table.

    Both sheets carry trailing rows that are not observations: fully blank
    spacer rows, and scratch/footer rows (e.g. the 'Nom'/'Trx' notes under
    Raw_JKTNasional) that hold large stray values but no period. Keeping them
    would inflate national totals and create a bogus NaN-period group.
    """
    out = df.loc[:, ~df.columns.astype(str).str.startswith('Unnamed:')]
    out = out.dropna(how='all')

    present = [c for c in key_cols if c in out.columns]
    if present:
        keys = pd.DataFrame({c: pd.to_numeric(out[c], errors='coerce') for c in present})
        out = out[keys.notna().all(axis=1)]

    return out.reset_index(drop=True)


@st.cache_data
def load_data(uploaded_file, is_trx_nasional: bool = False):
    sheet_name = 'Trx_PJPJKT'
    if is_trx_nasional:
        sheet_name = 'Raw_JKTNasional'
    try:
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
    except ValueError as e:
        st.error(f"Sheet '{sheet_name}' not found in the uploaded file. Please upload the file according to the format.")
        return None
    except Exception as e:
        st.error(f"An error occurred while loading the data: {e}")
        return None

    # Buang baris sisa spreadsheet sebelum apa pun dijumlahkan.
    # Hanya 'Year' yang dipakai sebagai penanda baris data: 'Month' pada
    # sebagian file berisi nama bulan, bukan angka.
    df = _drop_non_data_rows(df, ['Year'])

    # Samakan pembacaan angka untuk data PJP (Fin) dan data Raw Nasional,
    # supaya keduanya melewati parser yang sama dan tidak ada selisih pembulatan
    # yang berasal dari perbedaan cara baca.
    df = _coerce_numeric_columns(df, PJP_VALUE_COLUMNS + NATIONAL_VALUE_COLUMNS)

    # Sheet nasional membaca Year/Month sebagai float karena baris sisa tadi;
    # setelah dibersihkan kembalikan ke integer agar cocok dengan sheet PJP
    # saat di-merge/di-group.
    for col in ('Year', 'Quarter', 'Month'):
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            as_num = pd.to_numeric(df[col], errors='coerce')
            if as_num.notna().all():
                df[col] = as_num.astype(int)

    return df


def format_to_rupiah(amount):
    return "Rp {:,}".format(amount)


def filter_data(df, selected_pjp=None, selected_year=None,
                selected_quarter=None, selected_month=None,
                group_by_pjp=False):
    if selected_year and selected_year != 'All':
        df = df[df['Year'] == selected_year]
    if selected_quarter and selected_quarter != 'All':
        df = df[df['Quarter'] == selected_quarter]
    if selected_month and selected_month != 'All' and 'Month' in df.columns:
        df = df[df['Month'] == selected_month]
    if selected_pjp and selected_pjp != 'All':
        df = df[df['Nama PJP'] == selected_pjp]

    if group_by_pjp:
        df = df.groupby('Nama PJP').agg({
            'Sum of Fin Nilai Out': 'sum',
            'Sum of Fin Nilai Inc': 'sum',
            'Sum of Fin Nilai Dom': 'sum',
            'Sum of Fin Jumlah Out': 'sum',
            'Sum of Fin Jumlah Inc': 'sum',
            'Sum of Fin Jumlah Dom': 'sum',
        }).reset_index()

        df['Sum of Total Nom'] = df[['Sum of Fin Nilai Inc', 'Sum of Fin Nilai Out', 'Sum of Fin Nilai Dom']].sum(
            axis=1)
        df['Sum of Total Jumlah'] = df[['Sum of Fin Jumlah Inc', 'Sum of Fin Jumlah Out', 'Sum of Fin Jumlah Dom']].sum(
            axis=1)
        df.insert(1, 'Sum of Total Nom', df.pop('Sum of Total Nom'))
        df.insert(1, 'Sum of Total Jumlah', df.pop('Sum of Total Jumlah'))

    return df


def filter_start_end_year(df, start_year, end_year, is_month: bool = False):
    if is_month:
        for col in df.columns:
            if 'Sum of Fin' in col:
                df = df[~((df[col] == 0) & (df['Year'] == df['Year'].max()))]
    df_filtered = df[(df['Year'] >= start_year) & (df['Year'] <= end_year)]
    return df_filtered


def compute_average_ticket_size(df_jkt: pd.DataFrame, df_national: pd.DataFrame) -> dict:
    """Compute average ticket size for DKI (JKT sheet) and outside DKI.

    Definitions:
    - avg_dki = total_nominal_dki / total_freq_dki
    - avg_outside = (total_nominal_national - total_nominal_dki) / (total_freq_national - total_freq_dki)

    The national sheet sometimes repeats the same national totals for every PJP row in a period.
    We try to detect that and aggregate per-period totals safely.
    """

    def _safe_sum(df: pd.DataFrame, cols: list[str]) -> float:
        present = [c for c in cols if c in df.columns]
        if not present:
            return 0.0
        return float(pd.to_numeric(df[present].sum(axis=1), errors="coerce").fillna(0).sum())

    def _get_jkt_totals(df: pd.DataFrame) -> tuple[float, float]:
        # Prefer raw columns from Trx_PJPJKT
        nom = _safe_sum(df, ["Fin Nilai Inc", "Fin Nilai Out", "Fin Nilai Dom"])
        frek = _safe_sum(df, ["Fin Jumlah Inc", "Fin Jumlah Out", "Fin Jumlah Dom"])

        # Fallback to aggregated columns if the page passes preprocessed data
        if nom == 0.0 and frek == 0.0:
            nom = _safe_sum(df, ["Sum of Fin Nilai Inc", "Sum of Fin Nilai Out", "Sum of Fin Nilai Dom"])
            frek = _safe_sum(df, ["Sum of Fin Jumlah Inc", "Sum of Fin Jumlah Out", "Sum of Fin Jumlah Dom"])

        return nom, frek

    def _get_national_totals(df: pd.DataFrame) -> tuple[float, float]:
        if "Nom Nasional Total" in df.columns and "Frek Nasional Total" in df.columns:
            group_cols: list[str] = []
            for col in ["Year", "Quarter", "Month"]:
                if col in df.columns and df[col].notna().any():
                    group_cols.append(col)

            if group_cols:
                tmp = df[group_cols + ["Nom Nasional Total", "Frek Nasional Total"]].copy()

                # Heuristic: if within-period values are mostly identical, treat as repeated totals.
                nunique_nom = tmp.groupby(group_cols, dropna=False)["Nom Nasional Total"].nunique()
                nunique_frek = tmp.groupby(group_cols, dropna=False)["Frek Nasional Total"].nunique()
                noisy_groups = ((nunique_nom > 1) | (nunique_frek > 1)).mean() if len(nunique_nom) else 0.0

                if noisy_groups <= 0.05:
                    # Repeated totals -> take max per period then sum periods
                    per_period = tmp.groupby(group_cols, dropna=False).agg(
                        {"Nom Nasional Total": "max", "Frek Nasional Total": "max"}
                    )
                    return float(per_period["Nom Nasional Total"].sum()), float(per_period["Frek Nasional Total"].sum())
                else:
                    # Values vary per row -> treat as per-row contributions
                    return float(tmp["Nom Nasional Total"].sum()), float(tmp["Frek Nasional Total"].sum())

            # No period columns -> safest is to de-duplicate identical pairs (avoid obvious overcount)
            dedup = df[["Nom Nasional Total", "Frek Nasional Total"]].drop_duplicates()
            return float(dedup["Nom Nasional Total"].sum()), float(dedup["Frek Nasional Total"].sum())

        # Fallback: if only transaction-like columns exist, approximate via sums
        nom = _safe_sum(df, ["Nom Nasional Inc", "Nom Nasional Out", "Nom Nasional Dom", "Nom Nasional Total"])
        frek = _safe_sum(df, ["Frek Nasional Inc", "Frek Nasional Out", "Frek Nasional Dom", "Frek Nasional Total"])
        if nom == 0.0 and frek == 0.0:
            nom = _safe_sum(df, ["Fin Nilai Inc", "Fin Nilai Out", "Fin Nilai Dom"])
            frek = _safe_sum(df, ["Fin Jumlah Inc", "Fin Jumlah Out", "Fin Jumlah Dom"])
        return nom, frek

    jkt_nom, jkt_frek = _get_jkt_totals(df_jkt)
    nat_nom, nat_frek = _get_national_totals(df_national)

    outside_nom = max(nat_nom - jkt_nom, 0.0)
    outside_frek = max(nat_frek - jkt_frek, 0.0)

    avg_dki = (jkt_nom / jkt_frek) if jkt_frek else 0.0
    avg_outside = (outside_nom / outside_frek) if outside_frek else 0.0

    return {
        "total_nominal_dki": jkt_nom,
        "total_freq_dki": jkt_frek,
        "total_nominal_national": nat_nom,
        "total_freq_national": nat_frek,
        "avg_ticket_dki": avg_dki,
        "avg_ticket_outside": avg_outside,
    }


def filter_by_quarter(df, start_year, start_quarter, end_year, end_quarter):
    """
    Filter data berdasarkan Year-Quarter range yang kontinyu
    Contoh: 2024-Q1 sampai 2025-Q3 akan include semua quarter dalam range itu
    """
    import calendar
    
    quarter_order = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
    start_q = quarter_order[start_quarter]
    end_q = quarter_order[end_quarter]
    
    df_copy = df.copy()
    
    # Hitung quarter dari month jika ada
    if 'Month' in df_copy.columns:
        # Convert Month ke month number dan pastikan integer
        df_copy['MonthNum'] = df_copy['Month'].apply(
            lambda m: list(calendar.month_name).index(str(m)) if str(m) in calendar.month_name else int(m)
        ).astype(int)
        df_copy['Quarter'] = ((df_copy['MonthNum'] - 1) // 3 + 1).astype(int)
    elif 'Quarter' not in df_copy.columns:
        # Jika tidak ada Quarter dan Month, return as-is
        return df
    
    # Filter: kombinasi Year dan Quarter dengan range kontinu
    # Start: Year == start_year dan Quarter >= start_q, atau Year > start_year
    # End: Year == end_year dan Quarter <= end_q, atau Year < end_year
    
    start_condition = (df_copy['Year'] > start_year) | ((df_copy['Year'] == start_year) & (df_copy['Quarter'] >= start_q))
    end_condition = (df_copy['Year'] < end_year) | ((df_copy['Year'] == end_year) & (df_copy['Quarter'] <= end_q))
    
    df_filtered = df_copy[start_condition & end_condition]
    
    # Hapus kolom helper
    if 'MonthNum' in df_filtered.columns:
        df_filtered = df_filtered.drop(['MonthNum'], axis=1, errors='ignore')
    if 'Quarter' in df_filtered.columns and 'Quarter' not in df.columns:
        df_filtered = df_filtered.drop(['Quarter'], axis=1, errors='ignore')
    
    return df_filtered


def set_data_settings():
    pd.set_option('display.float_format', '{:,.2f}'.format)
    return


def ensure_session_state_defaults() -> None:
    """Initialize keys used across pages to avoid KeyError on first load."""
    st.session_state.setdefault('df', None)
    st.session_state.setdefault('df_national', None)
    st.session_state.setdefault('file_name', None)


def set_page_settings():
    ensure_session_state_defaults()
    pages = [
        st.Page(page="views/summary.py", title="Summary", default=True),
        st.Page(page="views/growth.py", title="Growth"),
        st.Page(page="views/profile.py", title="Profile"),
        st.Page(page="views/market_share.py", title="Market Share"),
        st.Page(page="views/fraud.py", title="Analisis TKM"),
        st.Page(page="views/anomaly.py", title="Deteksi Anomali"),
        st.Page(page="views/manage_data.py", title="Kelola Data")
    ]
    pg = st.navigation(pages=pages)
    pg.run()


def inject_global_theme_css() -> None:
    """Tema global modern (biru-cyan) yang aman untuk semua halaman."""
    st.markdown(
        """
        <style>
            [data-testid="stAppViewContainer"] {
                background: linear-gradient(180deg, #f8fbff 0%, #f1f7ff 52%, #f3fcff 100%);
            }
            .block-container {
                /* Hindari tabrakan dengan App Toolbar/Header Streamlit */
                padding-top: 4.2rem;
                padding-bottom: 1.0rem;
            }
            [data-testid="stSidebarContent"] {
                /* Pastikan menu navigasi halaman tidak ketutup toolbar */
                padding-top: 3.4rem;
            }
            [data-testid="stSidebarNav"] {
                margin-top: 0.2rem;
            }
            .page-hero {
                background: linear-gradient(120deg, #1d4ed8 0%, #2563eb 45%, #06b6d4 100%);
                border-radius: 14px;
                padding: 0.9rem 1rem;
                margin-bottom: 0.8rem;
                color: #ffffff;
                box-shadow: 0 12px 24px rgba(37, 99, 235, 0.24);
                border: 1px solid rgba(255, 255, 255, 0.22);
            }
            .page-hero-title {
                margin: 0;
                font-size: 1.12rem;
                font-weight: 750;
                line-height: 1.2;
            }
            .page-hero-sub {
                margin-top: 0.2rem;
                font-size: 0.85rem;
                opacity: 0.95;
            }
            [data-testid="stSidebar"] > div:first-child {
                background: linear-gradient(180deg, #0b3f86 0%, #0f5db0 46%, #0b8bb0 100%);
            }
            /* Navigation tetap terang */
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
            [data-testid="stSidebar"] .stRadio label,
            [data-testid="stSidebar"] .stCheckbox label,
            [data-testid="stSidebar"] .stSelectbox label,
            [data-testid="stSidebar"] .stMultiSelect label {
                color: #f8fbff !important;
            }
            [data-testid="stSidebarNav"] a {
                color: #f8fbff !important;
                border-radius: 10px;
                margin: 2px 4px;
                padding: 6px 10px;
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
            }
            [data-testid="stSidebarNav"] a * {
                color: #f8fbff !important;
            }
            [data-testid="stSidebarNav"] a:hover {
                background: rgba(255, 255, 255, 0.16);
                border-color: rgba(255, 255, 255, 0.28);
            }
            [data-testid="stSidebarNav"] a[aria-current="page"] {
                color: #0b2f63 !important;
                background: linear-gradient(135deg, #e6f2ff 0%, #dff7ff 100%);
                border-color: rgba(255, 255, 255, 0.85);
                font-weight: 700;
            }
            [data-testid="stSidebarNav"] a[aria-current="page"] * {
                color: #0b2f63 !important;
            }

            /* Filter/input di sidebar pakai teks gelap agar tidak nyaru */
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
            [data-testid="stSidebar"] .stCaption,
            [data-testid="stSidebar"] .stRadio label p,
            [data-testid="stSidebar"] .stCheckbox label p,
            [data-testid="stSidebar"] .stSelectbox label p,
            [data-testid="stSidebar"] .stMultiSelect label p,
            [data-testid="stSidebar"] .stSlider label p {
                color: #0f172a !important;
                font-weight: 600;
            }
            [data-testid="stSidebar"] [data-baseweb="select"] *,
            [data-testid="stSidebar"] [data-baseweb="popover"] *,
            [data-testid="stSidebar"] [role="listbox"] *,
            [data-testid="stSidebar"] .stTextInput input,
            [data-testid="stSidebar"] .stNumberInput input {
                color: #0f172a !important;
            }

            /* Logo sidebar: paksa punya background putih agar tidak nyaru */
            [data-testid="stSidebar"] [data-testid="stImage"] {
                background: #ffffff;
                border-radius: 12px;
                border: 1px solid #dce8fb;
                box-shadow: 0 8px 16px rgba(2, 12, 34, 0.18);
                padding: 8px 8px 6px 8px;
                margin: 4px 2px 12px 2px;
            }
            [data-testid="stSidebar"] [data-testid="stImage"] img {
                border-radius: 8px;
            }

            [data-testid="stSidebar"] [data-baseweb="select"] > div,
            [data-testid="stSidebar"] [data-baseweb="input"] > div,
            [data-testid="stSidebar"] .stTextInput input,
            [data-testid="stSidebar"] .stNumberInput input {
                background: rgba(255, 255, 255, 0.98) !important;
                color: #0f172a !important;
                border-radius: 10px !important;
                border: 1px solid #d6e7ff !important;
            }
            .stButton > button[kind="primary"],
            .stButton > button[data-testid="stBaseButton-primary"] {
                background: linear-gradient(135deg, #2563eb 0%, #06b6d4 100%) !important;
                color: #ffffff !important;
                border: none !important;
                border-radius: 10px !important;
                box-shadow: 0 8px 18px rgba(37, 99, 235, 0.24) !important;
            }
            .stButton > button[kind="primary"]:hover,
            .stButton > button[data-testid="stBaseButton-primary"]:hover {
                filter: brightness(1.03);
                transform: translateY(-1px);
            }
            .stDownloadButton > button {
                background: linear-gradient(135deg, #10b981 0%, #22c55e 100%) !important;
                color: #ffffff !important;
                border: none !important;
                border-radius: 10px !important;
                box-shadow: 0 8px 18px rgba(16, 185, 129, 0.24) !important;
            }
            .kpi-card {
                background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
                border-radius: 14px;
                padding: 14px;
                border: 1px solid #dbeafe;
                box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .kpi-card:hover {
                transform: translateY(-3px);
                box-shadow: 0 14px 24px rgba(15, 23, 42, 0.12);
            }
            .kpi-title {
                font-size: 12px;
                color: #64748b;
                font-weight: 700;
                margin-bottom: 4px;
            }
            .kpi-value-main {
                font-size: 22px;
                font-weight: 800;
                margin-bottom: 0;
                line-height: 1.25;
            }
            .kpi-value-sub {
                font-size: 12px;
                color: #64748b;
                font-weight: 600;
            }
            [data-testid="stAlert"] {
                border-radius: 10px;
                border: 1px solid #dbeafe;
            }
            [data-testid="stExpander"] {
                border: 1px solid #dbeafe;
                border-radius: 10px;
                background: #ffffff;
            }
            [data-testid="stDataFrame"] {
                border: 1px solid #dbeafe;
                border-radius: 10px;
                box-shadow: 0 6px 14px rgba(15, 23, 42, 0.06);
                overflow: hidden;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def set_page_visuals(condition):
    _install_dataframe_download_patch()
    inject_global_theme_css()

    title_map = {
        "viz": "Data LTDBB PJP LR JKT Visualization",
        "fds": "Analisis Transaksi Keuangan Mencurigakan (TKM)",
        "dm": "Kelola Data Sistem",
        "anomali": "Deteksi Anomali & Early Warning Data LTDBB",
    }
    subtitle_map = {
        "viz": "Dashboard analitik transaksi dengan tampilan modern dan ringkas.",
        "fds": "Pemantauan pola transaksi mencurigakan secara lebih terstruktur.",
        "dm": "Pengelolaan data dan konfigurasi sistem dalam satu halaman.",
        "anomali": "Penyaringan dugaan kesalahan data dan peringatan dini lonjakan transaksi.",
    }

    page_title = title_map.get(condition, "Dashboard")
    page_subtitle = subtitle_map.get(condition, "")

    st.markdown(
        f"""
        <div class="page-hero">
            <div class="page-hero-title">{page_title}</div>
            <div class="page-hero-sub">{page_subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.image(".static/Logo.png", use_container_width=True)
        with st.expander("Pengaturan Tabel", False):
            st.slider(
                "Tinggi tabel",
                min_value=280,
                max_value=1200,
                value=int(st.session_state.get("global_table_height", 420)),
                step=20,
                key="global_table_height",
                help="Semua tabel dapat diperbesar/diperkecil tingginya.",
            )


def _extract_df_for_export(data) -> pd.DataFrame | None:
    try:
        if isinstance(data, pd.io.formats.style.Styler):
            return data.data.copy()
        if isinstance(data, pd.DataFrame):
            return data.copy()
        if isinstance(data, pd.Series):
            return data.to_frame()
        if data is None:
            return None
        return pd.DataFrame(data)
    except Exception:
        return None


def _df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="data")
    return buffer.getvalue()


def _install_dataframe_download_patch() -> None:
    """Tambahkan tombol download Excel di bawah setiap st.dataframe/st.table secara global."""
    if getattr(st, "_tools_ltdbb_df_patched", False):
        return

    original_dataframe = st.dataframe
    original_table = st.table

    def _dataframe_with_download(data=None, *args, **kwargs):
        height = st.session_state.get("global_table_height")
        if "height" not in kwargs and height is not None:
            kwargs["height"] = int(height)

        result = original_dataframe(data, *args, **kwargs)

        export_df = _extract_df_for_export(data)
        if export_df is not None and not export_df.empty:
            counter = int(st.session_state.get("_table_download_counter", 0)) + 1
            st.session_state["_table_download_counter"] = counter

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"table_{counter}_{ts}.xlsx"
            excel_bytes = _df_to_excel_bytes(export_df)

            c1, c2 = st.columns([1.2, 3.8])
            with c1:
                st.download_button(
                    label="⬇️ Download Excel",
                    data=excel_bytes,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"table_download_{counter}",
                    use_container_width=True,
                )
            with c2:
                st.caption(f"{len(export_df):,} baris × {len(export_df.columns):,} kolom")

        return result

    st.dataframe = _dataframe_with_download

    def _table_with_download(data=None, *args, **kwargs):
        result = original_table(data, *args, **kwargs)
        export_df = _extract_df_for_export(data)
        if export_df is not None and not export_df.empty:
            counter = int(st.session_state.get("_table_download_counter", 0)) + 1
            st.session_state["_table_download_counter"] = counter

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"table_{counter}_{ts}.xlsx"
            excel_bytes = _df_to_excel_bytes(export_df)

            c1, c2 = st.columns([1.2, 3.8])
            with c1:
                st.download_button(
                    label="⬇️ Download Excel",
                    data=excel_bytes,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"table_download_{counter}",
                    use_container_width=True,
                )
            with c2:
                st.caption(f"{len(export_df):,} baris × {len(export_df.columns):,} kolom")
        return result

    st.table = _table_with_download
    st._tools_ltdbb_df_patched = True

def aggregate_data(df, is_trx=False):
    # Ensure aggregation inputs are numeric; Excel uploads sometimes load as strings
    df = _coerce_numeric_columns(
        df,
        [
            'Fin Jumlah Inc', 'Fin Nilai Inc',
            'Fin Jumlah Out', 'Fin Nilai Out',
            'Fin Jumlah Dom', 'Fin Nilai Dom',
        ],
    )
    for col in ['Fin Jumlah Inc', 'Fin Nilai Inc', 'Fin Jumlah Out', 'Fin Nilai Out', 'Fin Jumlah Dom', 'Fin Nilai Dom']:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    if is_trx:
        group_cols = ['Nama PJP', 'Year', 'Quarter', 'Month']
    else:
        group_cols = ['Nama PJP', 'Year', 'Quarter']
    df = df.drop(columns=['Nama PJP Conv Final'], errors='ignore')
    df = df.groupby(group_cols).agg({'Fin Jumlah Inc': 'sum', 'Fin Nilai Inc': 'sum',
                                     'Fin Jumlah Out': 'sum', 'Fin Nilai Out': 'sum',
                                     'Fin Jumlah Dom': 'sum', 'Fin Nilai Dom': 'sum', })
    df = df.rename(columns=lambda x: 'Sum of ' + x)
    df = df.reset_index()

    df = _coerce_numeric_columns(
        df,
        ['Sum of Fin Nilai Inc', 'Sum of Fin Nilai Out', 'Sum of Fin Nilai Dom'],
    )
    df['Sum of Total Nom'] = (
        df['Sum of Fin Nilai Inc'].fillna(0)
        + df['Sum of Fin Nilai Out'].fillna(0)
        + df['Sum of Fin Nilai Dom'].fillna(0)
    )
    return df


def preprocess_data(df_non_agg, is_trx=False):
    if is_trx:
        df = aggregate_data(df_non_agg, is_trx=is_trx)
        # Month can be int (1-12) or already a month name
        if 'Month' in df.columns:
            month_num = pd.to_numeric(df['Month'], errors='coerce')
            if month_num.notna().any():
                df.loc[month_num.notna(), 'Month'] = month_num[month_num.notna()].astype(int).apply(
                    lambda x: calendar.month_name[x]
                )

        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        df['Month'] = pd.Categorical(df['Month'], categories=months, ordered=True)

        group_cols = ['Year', 'Quarter', 'Month']
    else:
        df = aggregate_data(df_non_agg)
        group_cols = ['Year', 'Quarter']

    total_sum_of_nom = df.groupby(group_cols, observed=False)['Sum of Total Nom'].transform('sum')

    df = calculate_market_share(df, total_sum_of_nom)

    return df


def preprocess_data_growth(df, is_month: bool):
    df['%YoY'] = pd.NA
    df['%QtQ'] = pd.NA
    df['%MtM'] = pd.NA

    first_year = df['Year'].min()
    df.loc[df['Year'] == first_year, ['%YoY', '%QtQ', '%MtM']] = pd.NA

    # TODO: Logic calculations for %YoY, %QtQ, and %MtM
    if is_month:
        df_jumlah_inc_month = df[['Year', 'Month', 'Sum of Fin Jumlah Inc', '%MtM']].copy()
        df_jumlah_inc_month = calculate_month_to_month(df_jumlah_inc_month, first_year, 'Jumlah', 'Inc')

        df_jumlah_out_month = df[['Year', 'Month', 'Sum of Fin Jumlah Out', '%MtM']].copy()
        df_jumlah_out_month = calculate_month_to_month(df_jumlah_out_month, first_year, 'Jumlah', 'Out')

        df_jumlah_dom_month = df[['Year', 'Month', 'Sum of Fin Jumlah Dom', '%MtM']].copy()
        df_jumlah_dom_month = calculate_month_to_month(df_jumlah_dom_month, first_year, 'Jumlah', 'Dom')

        df_nom_inc_month = df[['Year', 'Month', 'Sum of Fin Nilai Inc', '%MtM']].copy()
        df_nom_inc_month = calculate_month_to_month(df_nom_inc_month, first_year, 'Nilai', 'Inc')

        df_nom_out_month = df[['Year', 'Month', 'Sum of Fin Nilai Out', '%MtM']].copy()
        df_nom_out_month = calculate_month_to_month(df_nom_out_month, first_year, 'Nilai', 'Out')

        df_nom_dom_month = df[['Year', 'Month', 'Sum of Fin Nilai Dom', '%MtM']].copy()
        df_nom_dom_month = calculate_month_to_month(df_nom_dom_month, first_year, 'Nilai', 'Dom')

        return (df_jumlah_inc_month, df_jumlah_out_month, df_jumlah_dom_month,
                df_nom_inc_month, df_nom_out_month, df_nom_dom_month)
    else:
        df_jumlah_inc = df[['Year', 'Quarter', 'Sum of Fin Jumlah Inc', '%YoY', '%QtQ']].copy()
        df_jumlah_inc = calculate_growth(df_jumlah_inc, first_year, 'Jumlah', 'Inc')

        df_jumlah_out = df[['Year', 'Quarter', 'Sum of Fin Jumlah Out', '%YoY', '%QtQ']].copy()
        df_jumlah_out = calculate_growth(df_jumlah_out, first_year, 'Jumlah', 'Out')

        df_jumlah_dom = df[['Year', 'Quarter', 'Sum of Fin Jumlah Dom', '%YoY', '%QtQ']].copy()
        df_jumlah_dom = calculate_growth(df_jumlah_dom, first_year, 'Jumlah', 'Dom')

        df_nom_inc = df[['Year', 'Quarter', 'Sum of Fin Nilai Inc', '%YoY', '%QtQ']].copy()
        df_nom_inc = calculate_growth(df_nom_inc, first_year, 'Nilai', 'Inc')

        df_nom_out = df[['Year', 'Quarter', 'Sum of Fin Nilai Out', '%YoY', '%QtQ']].copy()
        df_nom_out = calculate_growth(df_nom_out, first_year, 'Nilai', 'Out')

        df_nom_dom = df[['Year', 'Quarter', 'Sum of Fin Nilai Dom', '%YoY', '%QtQ']].copy()
        df_nom_dom = calculate_growth(df_nom_dom, first_year, 'Nilai', 'Dom')

        return df_jumlah_inc, df_jumlah_out, df_jumlah_dom, df_nom_inc, df_nom_out, df_nom_dom


def preprocess_data_national(df: pd.DataFrame, is_year: bool = False, is_quarter: bool = False) -> pd.DataFrame:
    df_copy = df.copy()

    if 'Nom Nasional Total.1' in df_copy.columns:
        df_copy.drop('Nom Nasional Total.1', axis=1, inplace=True)

    national_cols = NATIONAL_VALUE_COLUMNS

    # Baca angka nasional dengan parser yang sama seperti data PJP, bukan
    # pd.to_numeric polos, supaya angka ber-format teks (mis. '1.234.567')
    # tidak diam-diam menjadi NaN dan hilang dari total.
    df_copy = _coerce_numeric_columns(df_copy, national_cols)
    df_copy = _drop_non_data_rows(df_copy, ['Year'])

    def _aggregate_group(g: pd.DataFrame) -> pd.Series:
        """Agregasi aman untuk data nasional yang kadang diulang per baris PJP.

        Jika dalam 1 periode nilainya identik (nunique<=1), ambil satu nilai (max).
        Jika bervariasi, jumlahkan (sum).
        """
        out = {}
        for col in national_cols:
            if col not in g.columns:
                continue
            s = pd.to_numeric(g[col], errors='coerce').dropna()
            if s.empty:
                out[col] = np.nan
            elif s.nunique(dropna=True) <= 1:
                out[col] = float(s.max())
            else:
                out[col] = float(s.sum())
        return pd.Series(out)

    if is_year:
        if is_quarter:
            grouped_df = (
                df_copy
                .groupby(['Year', 'Quarter'], dropna=False)
                .apply(_aggregate_group)
                .reset_index()
            )
        else:
            grouped_df = (
                df_copy
                .groupby('Year', dropna=False)
                .apply(_aggregate_group)
                .reset_index()
            )
    else:
        grouped_df = (
            df_copy
            .groupby(['Year', 'Month'], dropna=False)
            .apply(_aggregate_group)
            .reset_index()
        )

    return grouped_df

def process_combined_df(df_inc: pd.DataFrame, df_out: pd.DataFrame, df_dom: pd.DataFrame,
                        is_month: bool = False) -> pd.DataFrame:
    if is_month:
        group_cols = ['Year', 'Month']
    else:
        group_cols = ['Year', 'Quarter']
    df_total = pd.concat([df_inc, df_out, df_dom])

    df_total = df_total.groupby(group_cols, observed=False).sum().reset_index()

    trx_type = "Jumlah"

    for col in df_total.columns:
        if "Nilai" in col or "Nom" in col:
            trx_type = "Nilai"
            break

    df_total[f'Sum of Fin {trx_type} Total'] = df_total[f'Sum of Fin {trx_type} Inc'] + df_total[
        f'Sum of Fin {trx_type} Out'] + \
                                               df_total[f'Sum of Fin {trx_type} Dom']

    return df_total


def process_growth_combined(df_jumlah_total: pd.DataFrame, df_nom_total: pd.DataFrame, first_year: int,
                            is_month: bool = False) -> pd.DataFrame:
    if is_month:
        group_cols = ['Year', 'Month']
        drop_cols_jumlah = ['%MtM', 'Sum of Fin Jumlah Inc',
                            'Sum of Fin Jumlah Out', 'Sum of Fin Jumlah Dom']
        drop_cols_nom = ['%MtM', 'Sum of Fin Nilai Inc',
                         'Sum of Fin Nilai Out', 'Sum of Fin Nilai Dom']
    else:
        group_cols = ['Year', 'Quarter']
        drop_cols_jumlah = ['%YoY', '%QtQ', 'Sum of Fin Jumlah Inc',
                            'Sum of Fin Jumlah Out', 'Sum of Fin Jumlah Dom']
        drop_cols_nom = ['%YoY', '%QtQ', 'Sum of Fin Nilai Inc',
                         'Sum of Fin Nilai Out', 'Sum of Fin Nilai Dom']
    df_jumlah_total.drop(drop_cols_jumlah, axis=1, inplace=True)
    df_nom_total.drop(drop_cols_nom, axis=1, inplace=True)

    df_total = pd.merge(df_jumlah_total, df_nom_total, on=group_cols)

    if not is_month:
        df_total_jumlah = calculate_growth(df_total, first_year, "Jumlah", "Total")
        df_total_nilai = calculate_growth(df_total, first_year, "Nilai", "Total")
        df_total_combined = (
            pd.merge(df_total_jumlah, df_total_nilai, on=group_cols)
            .drop(['Sum of Fin Jumlah Total_y', 'Sum of Fin Nilai Total_y'], axis=1)
            .rename(columns={'Sum of Fin Jumlah Total_x': 'Sum of Fin Jumlah Total',
                             'Sum of Fin Nilai Total_x': 'Sum of Fin Nilai Total',
                             '%YoY_x': '%YoY Jumlah', '%YoY_y': '%YoY Nilai',
                             '%QtQ_x': '%QtQ Jumlah', '%QtQ_y': '%QtQ Nilai', })
        )
    else:
        df_total_jumlah = calculate_month_to_month(df_total, first_year, "Jumlah", "Total")
        df_total_nilai = calculate_month_to_month(df_total, first_year, "Nilai", "Total")
        df_total_combined = (
            pd.merge(df_total_jumlah, df_total_nilai, on=group_cols)
            .drop(['Sum of Fin Jumlah Total_y', 'Sum of Fin Nilai Total_y'], axis=1)
            .rename(columns={'Sum of Fin Jumlah Total_x': 'Sum of Fin Jumlah Total',
                             'Sum of Fin Nilai Total_x': 'Sum of Fin Nilai Total',
                             '%MtM_x': '%MtM Jumlah', '%MtM_y': '%MtM Nilai'})
        )
    return df_total_combined


def sum_data_time(df, is_month):
    if is_month:
        group_cols = ['Year', 'Month']
    else:
        group_cols = ['Year', 'Quarter']
    df_sum = df.groupby(group_cols, observed=False).agg({
        'Sum of Fin Jumlah Inc': 'sum',
        'Sum of Fin Nilai Inc': 'sum',
        'Sum of Fin Jumlah Out': 'sum',
        'Sum of Fin Nilai Out': 'sum',
        'Sum of Fin Jumlah Dom': 'sum',
        'Sum of Fin Nilai Dom': 'sum',
        'Sum of Total Nom': 'sum',
    }).reset_index()
    return df_sum


def calculate_market_share(df, total_sum_of_nom):
    # Bagi dulu pada presisi penuh, baru dibulatkan sekali di akhir.
    share = (pd.to_numeric(df['Sum of Total Nom'], errors='coerce')
             / pd.to_numeric(total_sum_of_nom, errors='coerce')) * 100
    df['Market Share (%)'] = round_half_up_series(share, 2)
    return df


def calculate_growth(df: pd.DataFrame, first_year: int, sum_trx_type: str, trx_type: str):
    df_copy = df.copy()
    df_copy = calculate_year_on_year(df_copy, first_year, sum_trx_type, trx_type)
    df_copy = calculate_quarter_to_quarter(df_copy, first_year, sum_trx_type, trx_type)
    return df_copy


def _pct_change(current, previous):
    """Percent change on full precision, rounded once, half-up.

    Returns NaN when the base is missing or zero so the cell shows blank rather
    than an infinite or misleading growth figure.
    """
    cur = parse_number(current)
    prev = parse_number(previous)
    if cur is None or not prev:
        return np.nan
    return round_half_up(((cur - prev) / prev) * 100, 2)


def calculate_year_on_year(df: pd.DataFrame, first_year: int, sum_trx_type: str, trx_type: str):
    for i in range(len(df)):
        if df.iloc[i]['Year'] > first_year:
            current_value = df.iloc[i][f'Sum of Fin {sum_trx_type} {trx_type}']
            previous_year_value = df[(df['Year'] == df.iloc[i]['Year'] - 1) &
                                     (df['Quarter'] == df.iloc[i]['Quarter'])][
                f'Sum of Fin {sum_trx_type} {trx_type}']

            if not previous_year_value.empty:
                previous_year_value = previous_year_value.values[0]
                df.at[i, '%YoY'] = _pct_change(current_value, previous_year_value)
    return df


def calculate_quarter_to_quarter(df: pd.DataFrame, first_year: int, sum_trx_type: str, trx_type: str):
    for i in range(len(df)):
        if df.iloc[i]['Year'] > first_year:
            current_value = df.iloc[i][f'Sum of Fin {sum_trx_type} {trx_type}']
            previous_year_value = df.iloc[i - 1][f'Sum of Fin {sum_trx_type} {trx_type}']
            df.at[i, '%QtQ'] = _pct_change(current_value, previous_year_value)
    return df


def calculate_month_to_month(df_original: pd.DataFrame, first_year: int, sum_trx_type: str, trx_type: str):
    df = df_original.copy()
    df['Month'] = df['Month'].apply(lambda x: list(calendar.month_name).index(x))

    for i in range(len(df)):
        if df.iloc[i]['Year'] > first_year or (df.iloc[i]['Year'] == first_year and df.iloc[i]['Month'] > 1):
            current_value = df.iloc[i][f'Sum of Fin {sum_trx_type} {trx_type}']
            previous_month_value = df[(df['Year'] == df.iloc[i]['Year']) & (df['Month'] == df.iloc[i]['Month'] - 1)]

            if previous_month_value.empty:
                previous_month_value = df[(df['Year'] == df.iloc[i]['Year'] - 1) & (df['Month'] == 12)]

            if not previous_month_value.empty:
                previous_month_value = previous_month_value[f'Sum of Fin {sum_trx_type} {trx_type}'].values[0]

                df.at[i, '%MtM'] = _pct_change(current_value, previous_month_value)

    df['Month'] = df['Month'].apply(lambda x: calendar.month_name[x])
    return df


def merge_df_growth(left_df, right_df, is_month: bool = False):
    if not is_month:
        df_combined = pd.merge(left_df, right_df, "inner", on=['Year', 'Quarter'])
        df_combined.rename(columns={"%YoY_x": "%YoY Jumlah", "%QtQ_x": "%QtQ Jumlah",
                                    "%YoY_y": "%YoY Nom", "%QtQ_y": "%QtQ Nom"}, inplace=True)
    else:
        df_combined = pd.merge(left_df, right_df, "inner", on=['Year', 'Month'])
        df_combined.rename(columns={"%MtM_x": "%MtM Jumlah", "%MtM_y": "%MtM Nom"}, inplace=True)
    return df_combined

def compile_data_profile(df: pd.DataFrame, df_national: pd.DataFrame, sum_trx_type: str, trx_type: str) -> pd.DataFrame:
    if len(df_national) <= 0:
        return pd.DataFrame()
    data_pjp = parse_number(df[f'Sum of Fin {sum_trx_type} {trx_type}'].values[0])
    if sum_trx_type == "Jumlah":
        sum_trx_word = "Frekuensi"
        national_word = "Frek"
        scale = 1.0
    else:
        # Data PJP sumber dalam Rupiah -> konversi ke miliar dulu.
        # Data nasional pada file sumber sudah dalam miliar.
        sum_trx_word = "Nominal Rp Miliar"
        national_word = "Nom"
        scale = 1_000_000_000.0

    if trx_type == "Inc":
        trx_word = "Incoming"
    elif trx_type == "Out":
        trx_word = "Outgoing"
    else:
        trx_word = "Domestik"

    data_national = parse_number(df_national[f'{national_word} Nasional {trx_type}'].values[0])

    # Semua hitungan memakai presisi penuh; pembulatan hanya sekali, saat nilai
    # siap ditampilkan. Sebelumnya persentase dihitung dari angka yang sudah
    # dibulatkan (miliar 2 desimal, lalu dibagi 1.000 dan dibulatkan lagi),
    # sehingga market share bisa meleset dari hasil bagi yang sebenarnya.
    value_pjp = None if data_pjp is None else data_pjp / scale
    value_national = data_national

    if sum_trx_type != "Jumlah" and value_pjp is not None and value_national is not None:
        # Samakan skala nominal antara Trx Perusahaan dan Trx Nasional.
        # Jika nilainya besar, tampilkan keduanya dalam triliun.
        if max(abs(value_pjp), abs(value_national)) >= 1_000:
            value_pjp /= 1_000
            value_national /= 1_000
            sum_trx_word = "Nominal Rp Triliun"

    if not value_national or value_pjp is None:
        data_percentage = None
    else:
        data_percentage = round_half_up((value_pjp / value_national) * 100, 2)

    data_pjp = round_half_up(value_pjp, 2)
    data_national = round_half_up(value_national, 2)

    data = {
        "Transaction Type": ["Trx Perusahaan", "Trx Nasional", "Persentase (%)"],
        f"{trx_word} ({sum_trx_word})": [data_pjp, data_national, data_percentage],
    }

    return pd.DataFrame(data)

def compile_data_market_share(df: pd.DataFrame, df_national: pd.DataFrame, trx_type: str, df_inc: pd.DataFrame = None,
                              df_out: pd.DataFrame = None, df_dom: pd.DataFrame = None) -> pd.DataFrame:
    if trx_type == "Inc":
        trx_word = "Incoming"
    elif trx_type == "Out":
        trx_word = "Outgoing"
    elif trx_type == "Dom":
        trx_word = "Domestik"
    else:
        trx_word = "Total"

    def _total(frame: pd.DataFrame, column: str, divisor: float) -> float:
        if frame is None or column not in frame.columns:
            return 0.0
        return float(pd.to_numeric(frame[column], errors='coerce').fillna(0).sum()) / divisor

    # "Total" dijumlahkan dari data sumber, bukan dari tabel Inc/Out/Dom yang
    # sudah dibulatkan, supaya total tidak menyerap tiga kali error pembulatan.
    parts = ["Inc", "Out", "Dom"] if trx_type == "Total" else [trx_type]

    nominal_jkt = sum(_total(df, f'Sum of Fin Nilai {t}', 1_000_000_000_000) for t in parts)
    frek_jkt = sum(_total(df, f'Sum of Fin Jumlah {t}', 1_000_000) for t in parts)
    # Kolom nasional sudah dalam miliar -> /1.000 untuk jadi triliun.
    nominal_nasional = sum(_total(df_national, f'Nom Nasional {t}', 1_000) for t in parts)
    frek_nasional = sum(_total(df_national, f'Frek Nasional {t}', 1_000_000) for t in parts)

    def _share(jkt: float, nasional: float):
        # Rasio dihitung pada presisi penuh, lalu dibulatkan satu kali.
        if not nasional:
            return None
        return round_half_up((jkt / nasional) * 100, 2)

    data = {
        f"Transaksi {trx_word}": ['Jakarta', 'Nasional', 'Market Share (%)'],
        "Nominal (dalam triliun)": [
            round_half_up(nominal_jkt, 2),
            round_half_up(nominal_nasional, 2),
            _share(nominal_jkt, nominal_nasional),
        ],
        "Frekuensi (dalam jutaan)": [
            round_half_up(frek_jkt, 2),
            round_half_up(frek_nasional, 2),
            _share(frek_jkt, frek_nasional),
        ],
    }
    return pd.DataFrame(data)

def process_data_profile_month(df_month: pd.DataFrame, trx_type: str) -> pd.DataFrame:
    df_domestic_month = df_month[['Year', 'Month', f'Sum of Fin Jumlah {trx_type}', f'Sum of Fin Nilai {trx_type}']].copy()
    return df_domestic_month

def process_grand_total_profile(df: pd.DataFrame, trx_type: str) -> pd.DataFrame:
    grand_total_jumlah_month = df[f'Sum of Fin Jumlah {trx_type}'].sum()
    grand_total_nilai_month = df[f'Sum of Fin Nilai {trx_type}'].sum()
    df_grand_total_month = pd.DataFrame({
        f'Grand Total Jumlah {trx_type}': [grand_total_jumlah_month],
        f'Grand Total Nilai {trx_type}': [grand_total_nilai_month]
    })
    return df_grand_total_month

def add_quarter_column(df: pd.DataFrame) -> pd.DataFrame:
    df['Quarter'] = (df['Month'] - 1) // 3 + 1
    return df

def rename_format_growth_df(df: pd.DataFrame, trx_type: str):
    """
    Rename kolom dan kembalikan DataFrame dengan nilai numerik untuk sorting yang benar.
    Formatting akan dilakukan di growth.py menggunakan column_config.
    """
    if trx_type == "Inc":
        trx_var = "Incoming"
    elif trx_type == "Out":
        trx_var = "Outgoing"
    elif trx_type == "Dom":
        trx_var = "Domestik"
    else:
        trx_var = "Total"

    df = df.copy()
    df.rename(columns={
        f"Sum of Fin Jumlah {trx_type}": f"Total Frekuensi {trx_var}",
        f"Sum of Fin Nilai {trx_type}": f"Total Nominal {trx_var}",
        "%YoY Jumlah": "Year-on-Year Frekuensi",
        "%QtQ Jumlah": "Quarter-to-Quarter Frekuensi",
        "%YoY Nom": "Year-on-Year Nominal",
        "%QtQ Nom": "Quarter-to-Quarter Nominal",
        "%YoY Nilai": "Year-on-Year Nominal",
        "%QtQ Nilai": "Quarter-to-Quarter Nominal",
    }, inplace=True)

    # Ensure all columns are numeric types for proper sorting
    growth_cols = ["Year-on-Year Frekuensi", "Quarter-to-Quarter Frekuensi", 
                   "Year-on-Year Nominal", "Quarter-to-Quarter Nominal"]
    for col in growth_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Keep Year as int
    if 'Year' in df.columns:
        df['Year'] = df['Year'].astype(int)
    
    # Keep frekuensi and nominal as numeric
    if f"Total Frekuensi {trx_var}" in df.columns:
        df[f"Total Frekuensi {trx_var}"] = pd.to_numeric(df[f"Total Frekuensi {trx_var}"], errors='coerce')
    if f"Total Nominal {trx_var}" in df.columns:
        df[f"Total Nominal {trx_var}"] = pd.to_numeric(df[f"Total Nominal {trx_var}"], errors='coerce')
    
    return df

def rename_format_growth_monthly_df(df: pd.DataFrame, trx_type: str):
    """
    Rename kolom dan kembalikan DataFrame dengan nilai numerik untuk sorting yang benar.
    Formatting akan dilakukan di growth.py menggunakan column_config.
    """
    if trx_type == "Inc":
        trx_var = "Incoming"
    elif trx_type == "Out":
        trx_var = "Outgoing"
    elif trx_type == "Dom":
        trx_var = "Domestik"
    else:
        trx_var = "Total"

    df = df.copy()
    df.rename(columns={
        f"Sum of Fin Jumlah {trx_type}": f"Total Frekuensi {trx_var}",
        f"Sum of Fin Nilai {trx_type}": f"Total Nominal {trx_var}",
        "%MtM Jumlah": "Month-to-Month Frekuensi",
        "%MtM Nom": "Month-to-Month Nominal",
        "%MtM Nilai": "Month-to-Month Nominal",
    }, inplace=True)

    # Ensure all columns are numeric types for proper sorting
    growth_cols = ["Month-to-Month Frekuensi", "Month-to-Month Nominal"]
    for col in growth_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Keep Year as int
    if 'Year' in df.columns:
        df['Year'] = df['Year'].astype(int)
    
    # Keep frekuensi and nominal as numeric
    if f"Total Frekuensi {trx_var}" in df.columns:
        df[f"Total Frekuensi {trx_var}"] = pd.to_numeric(df[f"Total Frekuensi {trx_var}"], errors='coerce')
    if f"Total Nominal {trx_var}" in df.columns:
        df[f"Total Nominal {trx_var}"] = pd.to_numeric(df[f"Total Nominal {trx_var}"], errors='coerce')
    
    return df

def format_profile_df(df: pd.DataFrame, is_market_share: bool = False):
    # Pembulatan tampilan memakai HALF_UP yang sama dengan perhitungannya,
    # bukan format '%.2f' bawaan Python yang membulatkan ke genap terdekat.
    def _fmt_id_number(v):
        if v is None or (isinstance(v, (int, float, np.number)) and pd.isna(v)):
            return "-"
        if not isinstance(v, (int, float, np.number)):
            return v
        return format_id_decimal(v, decimals=2, none="-")

    def _fmt_id_percent(v):
        if v is None or (isinstance(v, (int, float, np.number)) and pd.isna(v)):
            return "-"
        if not isinstance(v, (int, float, np.number)):
            return v
        return format_id_percent(v, decimals=2, show_sign=False, none="-", space_before_percent=True)

    out = df.copy()
    if out.empty:
        return out

    # Kolom label baris berbeda antar tabel: "Transaction Type" atau "Transaksi ...".
    label_col = None
    if "Transaction Type" in out.columns:
        label_col = "Transaction Type"
    else:
        trans_cols = [c for c in out.columns if str(c).startswith("Transaksi ")]
        if trans_cols:
            label_col = trans_cols[0]
        elif len(out.columns) > 0:
            # Fallback aman: biasanya kolom pertama adalah label kategori.
            label_col = out.columns[0]

    value_cols = [c for c in out.columns if c != label_col]
    # Kolom diubah ke object dulu: isinya akan menjadi teks terformat, dan
    # menulis teks ke kolom float sudah deprecated di pandas.
    for col in value_cols:
        out[col] = out[col].astype(object)

    for col in value_cols:
        if col not in out.columns:
            continue

        # Baris persentase: format persen. Baris lain: format angka biasa.
        if label_col is not None:
            is_pct_row = out[label_col].astype(str).isin(["Persentase (%)", "Market Share (%)"])
        else:
            is_pct_row = pd.Series(False, index=out.index)

        if bool(is_pct_row.any()):
            out.loc[~is_pct_row, col] = out.loc[~is_pct_row, col].map(_fmt_id_number)
            out.loc[is_pct_row, col] = out.loc[is_pct_row, col].map(_fmt_id_percent)
        else:
            # fallback untuk tabel market share (baris terakhir juga persentase)
            out.loc[out.index[:-1], col] = out.loc[out.index[:-1], col].map(_fmt_id_number)
            out.loc[out.index[-1:], col] = out.loc[out.index[-1:], col].map(_fmt_id_percent)

    return out


def rename_format_profile_df(df: pd.DataFrame, trx_type: str):
    if trx_type == "Inc":
        trx_var = "Incoming"
    elif trx_type == "Out":
        trx_var = "Outgoing"
    else:
        trx_var = "Domestik"

    df = df.copy()

    nominal_src_col = f"Sum of Fin Nilai {trx_type}"
    unit = pick_rupiah_unit(df[nominal_src_col].max() if nominal_src_col in df.columns else None)
    decimals = 2 if unit.label in {"Miliar", "Triliun"} else 0

    if nominal_src_col in df.columns:
        df[nominal_src_col] = df[nominal_src_col] / unit.divisor

    nominal_label_col = f"Total Nominal {trx_var} {rupiah_unit_suffix(unit)}"

    df.rename(columns={
        f"Sum of Fin Jumlah {trx_type}": f"Total Frekuensi {trx_var}",
        nominal_src_col: nominal_label_col,
    }, inplace=True)

    df = df.style.format(
        {
            "Year": "{:.0f}",
            f"Total Frekuensi {trx_var}": "{:,.0f}",
            nominal_label_col: f"{{:,.{decimals}f}}",
        },
        thousands=".",
        decimal=",",
    )
    return df

def format_profile_df_grand_total(df: pd.DataFrame, trx_type: str):
    if trx_type == "Inc":
        trx_var = "Incoming"
    elif trx_type == "Out":
        trx_var = "Outgoing"
    else:
        trx_var = "Domestik"

    df = df.copy()

    nominal_src_col = f"Grand Total Nilai {trx_type}"
    unit = pick_rupiah_unit(df[nominal_src_col].max() if nominal_src_col in df.columns else None)
    decimals = 2 if unit.label in {"Miliar", "Triliun"} else 0

    if nominal_src_col in df.columns:
        df[nominal_src_col] = df[nominal_src_col] / unit.divisor

    nominal_label_col = f"Grand Total Nominal {trx_var} {rupiah_unit_suffix(unit)}"

    df.rename(columns={
        f"Grand Total Jumlah {trx_type}": f"Grand Total Frekuensi {trx_var}",
        nominal_src_col: nominal_label_col,
    }, inplace=True)

    df = df.style.format(
        {
            f"Grand Total Frekuensi {trx_var}": "{:,.0f}",
            nominal_label_col: f"{{:,.{decimals}f}}",
        },
        thousands=".",
        decimal=",",
    )
    return df


def get_pjp_growth_data(df: pd.DataFrame, pjp_name: str, is_month: bool = False) -> dict:
    """
    Generate growth data untuk satu PJP dengan breakdown per Incoming/Outgoing/Domestik
    """
    # Filter data untuk PJP tertentu
    df_pjp = df[df['Nama PJP'] == pjp_name].copy()
    
    if df_pjp.empty:
        return {}
    
    first_year = df_pjp['Year'].min()
    
    if is_month:
        group_cols = ['Year', 'Month']
    else:
        group_cols = ['Year', 'Quarter']
    
    # Aggregate per Year/Quarter
    df_agg = df_pjp.groupby(group_cols, observed=False).agg({
        'Sum of Fin Jumlah Inc': 'sum',
        'Sum of Fin Jumlah Out': 'sum',
        'Sum of Fin Jumlah Dom': 'sum',
        'Sum of Fin Nilai Inc': 'sum',
        'Sum of Fin Nilai Out': 'sum',
        'Sum of Fin Nilai Dom': 'sum',
    }).reset_index()
    
    # Buat combined total
    df_agg['Sum of Fin Jumlah Total'] = (
        df_agg['Sum of Fin Jumlah Inc'] + 
        df_agg['Sum of Fin Jumlah Out'] + 
        df_agg['Sum of Fin Jumlah Dom']
    )
    df_agg['Sum of Fin Nilai Total'] = (
        df_agg['Sum of Fin Nilai Inc'] + 
        df_agg['Sum of Fin Nilai Out'] + 
        df_agg['Sum of Fin Nilai Dom']
    )
    
    # Ensure numeric types
    numeric_cols = [col for col in df_agg.columns if 'Sum of Fin' in col]
    for col in numeric_cols:
        df_agg[col] = pd.to_numeric(df_agg[col], errors='coerce')
    
    # Calculate growth rates untuk Total
    if not is_month:
        # YoY & QtQ untuk quarterly
        df_agg['%YoY'] = np.nan
        df_agg['%QtQ'] = np.nan
        
        # YoY calculation untuk total
        for i in range(len(df_agg)):
            if df_agg.iloc[i]['Year'] > first_year:
                current_val = df_agg.iloc[i]['Sum of Fin Nilai Total']
                prev_year_data = df_agg[
                    (df_agg['Year'] == df_agg.iloc[i]['Year'] - 1) & 
                    (df_agg['Quarter'] == df_agg.iloc[i]['Quarter'])
                ]
                if not prev_year_data.empty:
                    prev_val = prev_year_data.iloc[0]['Sum of Fin Nilai Total']
                    if prev_val != 0:
                        df_agg.at[i, '%YoY'] = round(((current_val - prev_val) / prev_val) * 100, 2)
        
        # QtQ calculation untuk total
        for i in range(len(df_agg)):
            if i > 0:
                current_val = df_agg.iloc[i]['Sum of Fin Nilai Total']
                prev_val = df_agg.iloc[i - 1]['Sum of Fin Nilai Total']
                if prev_val != 0:
                    df_agg.at[i, '%QtQ'] = round(((current_val - prev_val) / prev_val) * 100, 2)
    
    # Prepare breakdown untuk setiap tipe transaksi dengan growth
    def add_growth_to_breakdown(df_breakdown, col_base, group_cols, first_year):
        """Helper function untuk tambah YoY & QtQ ke breakdown"""
        df_breakdown['%YoY'] = np.nan
        df_breakdown['%QtQ'] = np.nan
        
        # YoY calculation
        for i in range(len(df_breakdown)):
            if df_breakdown.iloc[i]['Year'] > first_year:
                current_val = df_breakdown.iloc[i][col_base]
                prev_year_data = df_breakdown[
                    (df_breakdown['Year'] == df_breakdown.iloc[i]['Year'] - 1) & 
                    (df_breakdown['Quarter'] == df_breakdown.iloc[i]['Quarter'])
                ]
                if not prev_year_data.empty:
                    prev_val = prev_year_data.iloc[0][col_base]
                    if pd.notna(prev_val) and prev_val != 0:
                        df_breakdown.at[i, '%YoY'] = round(((current_val - prev_val) / prev_val) * 100, 2)
        
        # QtQ calculation
        for i in range(len(df_breakdown)):
            if i > 0:
                current_val = df_breakdown.iloc[i][col_base]
                prev_val = df_breakdown.iloc[i - 1][col_base]
                if pd.notna(prev_val) and prev_val != 0:
                    df_breakdown.at[i, '%QtQ'] = round(((current_val - prev_val) / prev_val) * 100, 2)
        
        return df_breakdown
    
    # Incoming breakdown dengan growth
    df_inc = df_agg[group_cols + ['Sum of Fin Jumlah Inc', 'Sum of Fin Nilai Inc']].copy()
    df_inc = df_inc.rename(columns={
        'Sum of Fin Jumlah Inc': 'Frekuensi',
        'Sum of Fin Nilai Inc': 'Nominal',
    })
    # Ensure numeric
    df_inc['Frekuensi'] = pd.to_numeric(df_inc['Frekuensi'], errors='coerce')
    df_inc['Nominal'] = pd.to_numeric(df_inc['Nominal'], errors='coerce')
    df_inc = add_growth_to_breakdown(df_inc, 'Nominal', group_cols, first_year)
    
    # Outgoing breakdown dengan growth
    df_out = df_agg[group_cols + ['Sum of Fin Jumlah Out', 'Sum of Fin Nilai Out']].copy()
    df_out = df_out.rename(columns={
        'Sum of Fin Jumlah Out': 'Frekuensi',
        'Sum of Fin Nilai Out': 'Nominal',
    })
    # Ensure numeric
    df_out['Frekuensi'] = pd.to_numeric(df_out['Frekuensi'], errors='coerce')
    df_out['Nominal'] = pd.to_numeric(df_out['Nominal'], errors='coerce')
    df_out = add_growth_to_breakdown(df_out, 'Nominal', group_cols, first_year)
    
    # Domestik breakdown dengan growth
    df_dom = df_agg[group_cols + ['Sum of Fin Jumlah Dom', 'Sum of Fin Nilai Dom']].copy()
    df_dom = df_dom.rename(columns={
        'Sum of Fin Jumlah Dom': 'Frekuensi',
        'Sum of Fin Nilai Dom': 'Nominal',
    })
    # Ensure numeric
    df_dom['Frekuensi'] = pd.to_numeric(df_dom['Frekuensi'], errors='coerce')
    df_dom['Nominal'] = pd.to_numeric(df_dom['Nominal'], errors='coerce')
    df_dom = add_growth_to_breakdown(df_dom, 'Nominal', group_cols, first_year)
    
    # Prepare result dictionary dengan breakdown per tipe
    result = {
        'total': df_agg,
        'incoming': df_inc,
        'outgoing': df_out,
        'domestik': df_dom,
    }
    
    return result


def format_pjp_growth_table(df: pd.DataFrame, is_total: bool = True):
    """
    Format tabel growth data untuk PJP dengan tipe data numerik yang tepat
    """
    df_copy = df.copy()

    from service.formatting import format_id_int_thousands, format_id_percent
    
    # Format function untuk percent
    def format_percent(x):
        if pd.isna(x):
            return 'None'
        return format_id_percent(x, decimals=2, show_sign=False, none='None', space_before_percent=True)
    
    # Format function untuk ribuan (dengan titik sebagai thousand separator, tanpa desimal)
    def format_thousands(x):
        if pd.isna(x):
            return ''
        return format_id_int_thousands(x, none='')
    
    # Format setiap kolom langsung di DataFrame
    for col in df_copy.columns:
        if col in ['Year', 'Quarter', 'Month']:
            # Year, Quarter, Month as strings
            df_copy[col] = df_copy[col].astype(str)
        elif any(pct in col for pct in ['%', 'Year-on-Year', 'Quarter-to-Quarter']):
            # Percentage columns - format langsung sebagai string
            df_copy[col] = df_copy[col].apply(format_percent).astype(str)
        elif any(num in col for num in ['Frekuensi', 'Nominal', 'Total']):
            # Numeric columns - format langsung sebagai string
            df_copy[col] = df_copy[col].apply(format_thousands).astype(str)
    
    return df_copy