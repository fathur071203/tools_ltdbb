import pandas as pd
import streamlit as st

from service.preprocess import *
from service.visualize import *


def _get_growth_column_config(trx_var: str):
    """
    Mengembalikan column_config untuk st.dataframe agar format tampil dengan benar
    sambil tetap mempertahankan sorting numerik yang benar.
    """
    return {
        "Year": st.column_config.NumberColumn(
            "Year",
            format="%d"
        ),
        "Quarter": st.column_config.NumberColumn(
            "Quarter", 
            format="%d"
        ) if "Quarter" in ["Quarter"] else None,
        f"Total Frekuensi {trx_var}": st.column_config.NumberColumn(
            f"Total Frekuensi {trx_var}",
            format="%.0f"
        ),
        f"Total Nominal {trx_var}": st.column_config.NumberColumn(
            f"Total Nominal {trx_var}",
            format="%.0f"
        ),
        "Year-on-Year Frekuensi": st.column_config.NumberColumn(
            "Year-on-Year Frekuensi",
            format="%+.2f%%"
        ),
        "Quarter-to-Quarter Frekuensi": st.column_config.NumberColumn(
            "Quarter-to-Quarter Frekuensi",
            format="%+.2f%%"
        ),
        "Year-on-Year Nominal": st.column_config.NumberColumn(
            "Year-on-Year Nominal",
            format="%+.2f%%"
        ),
        "Quarter-to-Quarter Nominal": st.column_config.NumberColumn(
            "Quarter-to-Quarter Nominal",
            format="%+.2f%%"
        ),
        "Month-to-Month Frekuensi": st.column_config.NumberColumn(
            "Month-to-Month Frekuensi",
            format="%+.2f%%"
        ),
        "Month-to-Month Nominal": st.column_config.NumberColumn(
            "Month-to-Month Nominal",
            format="%+.2f%%"
        ),
    }


def _render_pjp_detail(df_base: pd.DataFrame, year: int, quarter: int, trx_type: str):
    """Tampilkan detail growth per PJP untuk periode (year, quarter) dan tipe transaksi."""
    col_map_jumlah = {
        "Incoming": "Sum of Fin Jumlah Inc",
        "Outgoing": "Sum of Fin Jumlah Out",
        "Domestik": "Sum of Fin Jumlah Dom",
    }
    col_map_nilai = {
        "Incoming": "Sum of Fin Nilai Inc",
        "Outgoing": "Sum of Fin Nilai Out",
        "Domestik": "Sum of Fin Nilai Dom",
    }

    # Filter current period
    current = df_base[(df_base["Year"] == year) & (df_base["Quarter"] == quarter)].copy()
    if current.empty:
        st.warning("Data tidak ditemukan untuk periode tersebut")
        return

    if trx_type == "Total":
        current["Jumlah"] = (
            current["Sum of Fin Jumlah Inc"]
            + current["Sum of Fin Jumlah Out"]
            + current["Sum of Fin Jumlah Dom"]
        )
        current["Nilai"] = (
            current["Sum of Fin Nilai Inc"]
            + current["Sum of Fin Nilai Out"]
            + current["Sum of Fin Nilai Dom"]
        )
    else:
        current["Jumlah"] = current[col_map_jumlah[trx_type]]
        current["Nilai"] = current[col_map_nilai[trx_type]]

    # Grup per PJP
    cur_group = current.groupby("Nama PJP", observed=False)[["Jumlah", "Nilai"]].sum().reset_index()

    # Prev quarter
    prev_q = quarter - 1 if quarter > 1 else 4
    prev_y = year if quarter > 1 else year - 1
    prev_q_df = df_base[(df_base["Year"] == prev_y) & (df_base["Quarter"] == prev_q)].copy()
    if not prev_q_df.empty:
        if trx_type == "Total":
            prev_q_df["Jumlah"] = (
                prev_q_df["Sum of Fin Jumlah Inc"]
                + prev_q_df["Sum of Fin Jumlah Out"]
                + prev_q_df["Sum of Fin Jumlah Dom"]
            )
            prev_q_df["Nilai"] = (
                prev_q_df["Sum of Fin Nilai Inc"]
                + prev_q_df["Sum of Fin Nilai Out"]
                + prev_q_df["Sum of Fin Nilai Dom"]
            )
        else:
            prev_q_df["Jumlah"] = prev_q_df[col_map_jumlah[trx_type]]
            prev_q_df["Nilai"] = prev_q_df[col_map_nilai[trx_type]]
        prev_q_group = prev_q_df.groupby("Nama PJP", observed=False)[["Jumlah", "Nilai"]].sum().reset_index()
    else:
        prev_q_group = pd.DataFrame(columns=["Nama PJP", "Jumlah", "Nilai"])

    # Prev year same quarter
    prev_y_df = df_base[(df_base["Year"] == year - 1) & (df_base["Quarter"] == quarter)].copy()
    if not prev_y_df.empty:
        if trx_type == "Total":
            prev_y_df["Jumlah"] = (
                prev_y_df["Sum of Fin Jumlah Inc"]
                + prev_y_df["Sum of Fin Jumlah Out"]
                + prev_y_df["Sum of Fin Jumlah Dom"]
            )
            prev_y_df["Nilai"] = (
                prev_y_df["Sum of Fin Nilai Inc"]
                + prev_y_df["Sum of Fin Nilai Out"]
                + prev_y_df["Sum of Fin Nilai Dom"]
            )
        else:
            prev_y_df["Jumlah"] = prev_y_df[col_map_jumlah[trx_type]]
            prev_y_df["Nilai"] = prev_y_df[col_map_nilai[trx_type]]
        prev_y_group = prev_y_df.groupby("Nama PJP", observed=False)[["Jumlah", "Nilai"]].sum().reset_index()
    else:
        prev_y_group = pd.DataFrame(columns=["Nama PJP", "Jumlah", "Nilai"])

    # Merge for growth
    detail = cur_group.merge(prev_q_group, on="Nama PJP", how="left", suffixes=("", "_PrevQ"))
    detail = detail.merge(prev_y_group, on="Nama PJP", how="left", suffixes=("", "_PrevY"))

    def pct_growth(cur, prev):
        if pd.isna(prev) or prev == 0:
            return 0.0
        return (cur - prev) / prev * 100

    detail["Growth QtQ (%)"] = detail.apply(lambda r: pct_growth(r["Nilai"], r.get("Nilai_PrevQ", 0)), axis=1)
    detail["Growth YoY (%)"] = detail.apply(lambda r: pct_growth(r["Nilai"], r.get("Nilai_PrevY", 0)), axis=1)

    # Format display
    disp = detail.copy()
    for col in ["Jumlah", "Nilai", "Jumlah_PrevQ", "Nilai_PrevQ", "Jumlah_PrevY", "Nilai_PrevY"]:
        if col in disp.columns:
            disp[col] = disp[col].fillna(0).astype(int).apply(lambda x: f"{x:,}".replace(',', '.'))
    for col in ["Growth QtQ (%)", "Growth YoY (%)"]:
        disp[col] = disp[col].apply(lambda x: f"{x:+.2f}%".replace('.', ',').replace(',00%', '%'))

    st.dataframe(disp[[c for c in disp.columns if not c.endswith("_PrevQ") and not c.endswith("_PrevY")]], use_container_width=True, hide_index=True)


def _render_pjp_detail_month(df_base: pd.DataFrame, year: int, month: str, trx_type: str):
    """Tampilkan detail growth per PJP untuk periode (year, month) dengan MtM & YoY pada level bulan."""
    import calendar

    col_map_jumlah = {
        "Incoming": "Sum of Fin Jumlah Inc",
        "Outgoing": "Sum of Fin Jumlah Out",
        "Domestik": "Sum of Fin Jumlah Dom",
    }
    col_map_nilai = {
        "Incoming": "Sum of Fin Nilai Inc",
        "Outgoing": "Sum of Fin Nilai Out",
        "Domestik": "Sum of Fin Nilai Dom",
    }

    month_num = list(calendar.month_name).index(str(month)) if str(month) in calendar.month_name else int(month)

    current = df_base[(df_base["Year"] == year) & (df_base["Month"].astype(str) == str(month))].copy()
    if current.empty:
        st.warning("Data tidak ditemukan untuk periode tersebut")
        return

    if trx_type == "Total":
        current["Jumlah"] = (
            current["Sum of Fin Jumlah Inc"]
            + current["Sum of Fin Jumlah Out"]
            + current["Sum of Fin Jumlah Dom"]
        )
        current["Nilai"] = (
            current["Sum of Fin Nilai Inc"]
            + current["Sum of Fin Nilai Out"]
            + current["Sum of Fin Nilai Dom"]
        )
    else:
        current["Jumlah"] = current[col_map_jumlah[trx_type]]
        current["Nilai"] = current[col_map_nilai[trx_type]]

    cur_group = current.groupby("Nama PJP", observed=False)[["Jumlah", "Nilai"]].sum().reset_index()

    # Prev month
    prev_m = 12 if month_num == 1 else month_num - 1
    prev_y = year if month_num > 1 else year - 1
    prev_m_name = calendar.month_name[prev_m]
    prev_m_df = df_base[(df_base["Year"] == prev_y) & (df_base["Month"].astype(str) == str(prev_m_name))].copy()
    if prev_m_df.empty:
        prev_m_df = df_base[(df_base["Year"] == prev_y) & (df_base["Month"].astype(str) == str(prev_m))].copy()
    if not prev_m_df.empty:
        if trx_type == "Total":
            prev_m_df["Jumlah"] = prev_m_df["Sum of Fin Jumlah Inc"] + prev_m_df["Sum of Fin Jumlah Out"] + prev_m_df["Sum of Fin Jumlah Dom"]
            prev_m_df["Nilai"] = prev_m_df["Sum of Fin Nilai Inc"] + prev_m_df["Sum of Fin Nilai Out"] + prev_m_df["Sum of Fin Nilai Dom"]
        else:
            prev_m_df["Jumlah"] = prev_m_df[col_map_jumlah[trx_type]]
            prev_m_df["Nilai"] = prev_m_df[col_map_nilai[trx_type]]
        prev_m_group = prev_m_df.groupby("Nama PJP", observed=False)[["Jumlah", "Nilai"]].sum().reset_index()
    else:
        prev_m_group = pd.DataFrame(columns=["Nama PJP", "Jumlah", "Nilai"])

    # Prev year same month
    prev_y_df = df_base[(df_base["Year"] == year - 1) & (df_base["Month"].astype(str) == str(month))].copy()
    if prev_y_df.empty:
        prev_y_df = df_base[(df_base["Year"] == year - 1) & (df_base["Month"].astype(str) == str(month_num))].copy()
    if not prev_y_df.empty:
        if trx_type == "Total":
            prev_y_df["Jumlah"] = prev_y_df["Sum of Fin Jumlah Inc"] + prev_y_df["Sum of Fin Jumlah Out"] + prev_y_df["Sum of Fin Jumlah Dom"]
            prev_y_df["Nilai"] = prev_y_df["Sum of Fin Nilai Inc"] + prev_y_df["Sum of Fin Nilai Out"] + prev_y_df["Sum of Fin Nilai Dom"]
        else:
            prev_y_df["Jumlah"] = prev_y_df[col_map_jumlah[trx_type]]
            prev_y_df["Nilai"] = prev_y_df[col_map_nilai[trx_type]]
        prev_y_group = prev_y_df.groupby("Nama PJP", observed=False)[["Jumlah", "Nilai"]].sum().reset_index()
    else:
        prev_y_group = pd.DataFrame(columns=["Nama PJP", "Jumlah", "Nilai"])

    detail = cur_group.merge(prev_m_group, on="Nama PJP", how="left", suffixes=("", "_PrevM"))
    detail = detail.merge(prev_y_group, on="Nama PJP", how="left", suffixes=("", "_PrevY"))

    def pct_growth(cur, prev):
        if pd.isna(prev) or prev == 0:
            return 0.0
        return (cur - prev) / prev * 100

    detail["Growth MtM (%)"] = detail.apply(lambda r: pct_growth(r["Nilai"], r.get("Nilai_PrevM", 0)), axis=1)
    detail["Growth YoY (%)"] = detail.apply(lambda r: pct_growth(r["Nilai"], r.get("Nilai_PrevY", 0)), axis=1)

    disp = detail.copy()
    for col in ["Jumlah", "Nilai", "Jumlah_PrevM", "Nilai_PrevM", "Jumlah_PrevY", "Nilai_PrevY"]:
        if col in disp.columns:
            disp[col] = disp[col].fillna(0).astype(int).apply(lambda x: f"{x:,}".replace(',', '.'))
    for col in ["Growth MtM (%)", "Growth YoY (%)"]:
        disp[col] = disp[col].apply(lambda x: f"{x:+.2f}%".replace('.', ',').replace(',00%', '%'))

    st.dataframe(disp[[c for c in disp.columns if not c.endswith("_PrevM") and not c.endswith("_PrevY")]], use_container_width=True, hide_index=True)


def _render_overall_growth_detail_table_quarterly(
    *,
    df_total_combined: pd.DataFrame,
    df_inc: pd.DataFrame,
    df_out: pd.DataFrame,
    df_dom: pd.DataFrame,
    sum_trx_type: str,
    visible_periods: list[str] | None,
    ordered_periods: list[str],
):
    """Tabel detail YoY/QtQ untuk semua periode yang sedang ditampilkan (visual-only)."""

    if sum_trx_type not in ("Jumlah", "Nilai"):
        return

    if df_total_combined is None or df_total_combined.empty:
        return

    # Tentukan periode yang benar-benar ditampilkan (urut sesuai pilihan)
    visible_set = set(visible_periods or [])
    shown_periods = [p for p in ordered_periods if p in visible_set] if visible_set else list(ordered_periods)
    if not shown_periods:
        st.info("Tidak ada periode yang dipilih untuk tabel detail.")
        return

    # Parse "YYYY Qn" menjadi list (Year, Quarter) berurutan
    parsed = []
    for p in shown_periods:
        try:
            parts = str(p).split()
            if len(parts) >= 2 and parts[1].upper().startswith("Q"):
                y = int(parts[0])
                q = int(parts[1].upper().replace("Q", ""))
                if 1 <= q <= 4:
                    parsed.append((y, q))
        except Exception:
            continue

    if not parsed:
        return

    if sum_trx_type == "Jumlah":
        value_unit = "Volume (Jutaan)"
        scale = 1e6
    else:
        value_unit = "Nilai (Rp Triliun)"
        scale = 1e12

    periods_df = pd.DataFrame(parsed, columns=["Year", "Quarter"]).drop_duplicates()

    total_val_col = f"Sum of Fin {sum_trx_type} Total"
    total_yoy_col = f"%YoY {sum_trx_type}"
    total_qoq_col = f"%QtQ {sum_trx_type}"

    inc_val_col = f"Sum of Fin {sum_trx_type} Inc"
    out_val_col = f"Sum of Fin {sum_trx_type} Out"
    dom_val_col = f"Sum of Fin {sum_trx_type} Dom"

    def _num(v):
        return pd.to_numeric(v, errors="coerce")

    def _build_block(
        df_src: pd.DataFrame,
        *,
        jenis: str,
        value_col: str,
        yoy_col: str,
        qoq_col: str,
    ) -> pd.DataFrame:
        if df_src is None or df_src.empty:
            return pd.DataFrame()
        if not {"Year", "Quarter"}.issubset(set(df_src.columns)):
            return pd.DataFrame()
        needed = {value_col, yoy_col, qoq_col}
        if not needed.issubset(set(df_src.columns)):
            return pd.DataFrame()

        dfc = df_src[["Year", "Quarter", value_col, yoy_col, qoq_col]].copy()
        dfc["Year"] = dfc["Year"].astype(int)
        dfc["Quarter"] = dfc["Quarter"].astype(int)

        # Join ke daftar periode yg sedang ditampilkan agar urut & hanya yg dipilih
        dfc = periods_df.merge(dfc, on=["Year", "Quarter"], how="left")
        dfc["Periode"] = "Q" + dfc["Quarter"].astype(int).astype(str) + " " + dfc["Year"].astype(int).astype(str)
        dfc["Jenis"] = jenis
        dfc[value_unit] = _num(dfc[value_col]) / scale
        dfc["YoY (%)"] = _num(dfc[yoy_col])
        dfc["QtQ (%)"] = _num(dfc[qoq_col])
        return dfc[["Periode", "Jenis", value_unit, "YoY (%)", "QtQ (%)"]]

    df_total_block = _build_block(
        df_total_combined,
        jenis="Total",
        value_col=total_val_col,
        yoy_col=total_yoy_col,
        qoq_col=total_qoq_col,
    )
    df_inc_block = _build_block(
        df_inc,
        jenis="Incoming",
        value_col=inc_val_col,
        yoy_col="%YoY",
        qoq_col="%QtQ",
    )
    df_out_block = _build_block(
        df_out,
        jenis="Outgoing",
        value_col=out_val_col,
        yoy_col="%YoY",
        qoq_col="%QtQ",
    )
    df_dom_block = _build_block(
        df_dom,
        jenis="Domestik",
        value_col=dom_val_col,
        yoy_col="%YoY",
        qoq_col="%QtQ",
    )

    df_detail = pd.concat([df_total_block, df_inc_block, df_out_block, df_dom_block], ignore_index=True)
    if df_detail.empty:
        return

    st.caption("Detail perbandingan untuk semua periode yang sedang ditampilkan pada chart (sesuai filter 'Tampilkan Kuartal').")
    st.dataframe(
        df_detail,
        use_container_width=True,
        hide_index=True,
        column_config={
            value_unit: st.column_config.NumberColumn(value_unit, format="%.2f"),
            "YoY (%)": st.column_config.NumberColumn("YoY (%)", format="%+.2f%%"),
            "QtQ (%)": st.column_config.NumberColumn("QtQ (%)", format="%+.2f%%"),
        },
    )

# Initial Page Setup
set_page_visuals("viz")

if st.session_state['df'] is not None:
    df = st.session_state['df']
    with st.sidebar:
        with st.expander("Filter Growth", True):
            unique_years = sorted(df['Year'].unique().tolist())
            quarters = ['Q1', 'Q2', 'Q3', 'Q4']
            
            # Start Year & Quarter
            col_y1, col_q1 = st.columns(2)
            with col_y1:
                selected_start_year = st.selectbox('Start Year:', unique_years)
            with col_q1:
                selected_start_quarter = st.selectbox('Start Quarter:', quarters)
            
            # End Year & Quarter
            col_y2, col_q2 = st.columns(2)
            with col_y2:
                selected_end_year = st.selectbox('End Year:', unique_years, index=len(unique_years) - 1)
            with col_q2:
                selected_end_quarter = st.selectbox('End Quarter:', quarters, index=3)

            jenis_transaksi = ['All', 'Incoming', 'Outgoing', 'Domestik']
            selected_jenis_transaksi = st.selectbox('Select Jenis Transaksi:', jenis_transaksi)

        with st.expander("Pengaturan Tampilan Grafik (Growth)", True):
            st.slider(
                "Ukuran Font (Global)",
                min_value=9,
                max_value=22,
                value=int(st.session_state.get("growth_font_size", 12)),
                step=1,
                key="growth_font_size",
                help="Mengatur ukuran seluruh tulisan di grafik (judul, axis, legend, hoverlabel).",
            )
            st.slider(
                "Ukuran Angka Sumbu X",
                min_value=8,
                max_value=24,
                value=int(st.session_state.get("growth_axis_x_tick_font_size", max(int(st.session_state.get("growth_font_size", 12)) - 1, 9))),
                step=1,
                key="growth_axis_x_tick_font_size",
                help="Mengatur ukuran angka pada sumbu X (horizontal/periode).",
            )
            st.slider(
                "Ukuran Angka Sumbu Y",
                min_value=8,
                max_value=24,
                value=int(st.session_state.get("growth_axis_y_tick_font_size", max(int(st.session_state.get("growth_font_size", 12)) - 1, 9))),
                step=1,
                key="growth_axis_y_tick_font_size",
                help="Mengatur ukuran angka pada sumbu Y (kiri & kanan/nilai & growth).",
            )
            st.slider(
                "Ukuran Legend (Legenda Grafik)",
                min_value=9,
                max_value=24,
                value=int(st.session_state.get("growth_legend_font_size", st.session_state.get("growth_font_size", 12))),
                step=1,
                key="growth_legend_font_size",
                help="Mengatur ukuran tulisan pada legend/legenda grafik.",
            )
            st.slider(
                "Ukuran Font Label (%)",
                min_value=9,
                max_value=26,
                value=int(st.session_state.get("growth_label_font_size", 12)),
                step=1,
                key="growth_label_font_size",
                help="Mengatur ukuran tulisan label persentase (YoY/QtQ) di titik terakhir.",
            )
            st.slider(
                "Tinggi Grafik (px)",
                min_value=380,
                max_value=980,
                value=int(st.session_state.get("growth_chart_height", 560)),
                step=20,
                key="growth_chart_height",
                help="Atur tinggi grafik supaya tidak gepeng / terlalu tinggi.",
            )
            st.slider(
                "Lebar Grafik (px)",
                min_value=0,
                max_value=2200,
                value=int(st.session_state.get("growth_chart_width", 0)),
                step=50,
                key="growth_chart_width",
                help="Atur lebar grafik. 0 = mengikuti lebar container (auto).",
            )
        st.info("Use the filters to adjust the year-quarter range and transaction type.")

        _growth_font_size = int(st.session_state.get("growth_font_size", 12))
        _growth_axis_x_tick_font_size = int(st.session_state.get("growth_axis_x_tick_font_size", max(_growth_font_size - 1, 9)))
        _growth_axis_y_tick_font_size = int(st.session_state.get("growth_axis_y_tick_font_size", max(_growth_font_size - 1, 9)))
        _growth_legend_font_size = int(st.session_state.get("growth_legend_font_size", _growth_font_size))
        _growth_label_font_size = int(st.session_state.get("growth_label_font_size", 12))
        _growth_chart_height = int(st.session_state.get("growth_chart_height", 560))
        _growth_chart_width = int(st.session_state.get("growth_chart_width", 0))

    with (st.spinner('Loading and filtering data...')):
        df_preprocessed_time = preprocess_data(df, True)

        df_sum_time = sum_data_time(df_preprocessed_time, False)
        df_sum_time_month = sum_data_time(df_preprocessed_time, True)

        df_tuple = preprocess_data_growth(df_sum_time, False)
        df_tuple_month = preprocess_data_growth(df_sum_time_month, True)

        df_jumlah_inc, df_jumlah_out, df_jumlah_dom, df_nom_inc, df_nom_out, df_nom_dom = df_tuple

        (df_jumlah_inc_month, df_jumlah_out_month, df_jumlah_dom_month,
         df_nom_inc_month, df_nom_out_month, df_nom_dom_month) = df_tuple_month

        df_jumlah_total = process_combined_df(df_jumlah_inc, df_jumlah_out,
                                              df_jumlah_dom, False)
        df_nom_total = process_combined_df(df_nom_inc, df_nom_out,
                                           df_nom_dom, False)

        df_jumlah_total_month = process_combined_df(df_jumlah_inc_month, df_jumlah_out_month,
                                                    df_jumlah_dom_month, True)
        df_nom_total_month = process_combined_df(df_nom_inc_month, df_nom_out_month,
                                                 df_nom_dom_month, True)

        df_total_combined = process_growth_combined(df_jumlah_total, df_nom_total, df_preprocessed_time['Year'].min(),
                                                    False)
        df_total_month_combined = process_growth_combined(df_jumlah_total_month, df_nom_total_month,
                                                          df_preprocessed_time['Year'].min(), True)

        # Filter by year and quarter range (continuous)
        df_total_combined = filter_start_end_year(df_total_combined, selected_start_year, selected_end_year)
        df_total_combined = filter_by_quarter(df_total_combined, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_total_month_combined = filter_start_end_year(df_total_month_combined, selected_start_year, selected_end_year, True)
        df_total_month_combined = filter_by_quarter(df_total_month_combined, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)

        df_jumlah_inc_filtered = filter_start_end_year(df_jumlah_inc, selected_start_year, selected_end_year)
        df_jumlah_inc_filtered = filter_by_quarter(df_jumlah_inc_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_jumlah_out_filtered = filter_start_end_year(df_jumlah_out, selected_start_year, selected_end_year)
        df_jumlah_out_filtered = filter_by_quarter(df_jumlah_out_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_jumlah_dom_filtered = filter_start_end_year(df_jumlah_dom, selected_start_year, selected_end_year)
        df_jumlah_dom_filtered = filter_by_quarter(df_jumlah_dom_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)

        df_nom_inc_filtered = filter_start_end_year(df_nom_inc, selected_start_year, selected_end_year)
        df_nom_inc_filtered = filter_by_quarter(df_nom_inc_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_nom_out_filtered = filter_start_end_year(df_nom_out, selected_start_year, selected_end_year)
        df_nom_out_filtered = filter_by_quarter(df_nom_out_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_nom_dom_filtered = filter_start_end_year(df_nom_dom, selected_start_year, selected_end_year)
        df_nom_dom_filtered = filter_by_quarter(df_nom_dom_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)

        df_jumlah_inc_month_filtered = filter_start_end_year(df_jumlah_inc_month, selected_start_year, selected_end_year, True)
        df_jumlah_inc_month_filtered = filter_by_quarter(df_jumlah_inc_month_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_jumlah_out_month_filtered = filter_start_end_year(df_jumlah_out_month, selected_start_year, selected_end_year, True)
        df_jumlah_out_month_filtered = filter_by_quarter(df_jumlah_out_month_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_jumlah_dom_month_filtered = filter_start_end_year(df_jumlah_dom_month, selected_start_year, selected_end_year, True)
        df_jumlah_dom_month_filtered = filter_by_quarter(df_jumlah_dom_month_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)

        df_nom_inc_month_filtered = filter_start_end_year(df_nom_inc_month, selected_start_year, selected_end_year, True)
        df_nom_inc_month_filtered = filter_by_quarter(df_nom_inc_month_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_nom_out_month_filtered = filter_start_end_year(df_nom_out_month, selected_start_year, selected_end_year, True)
        df_nom_out_month_filtered = filter_by_quarter(df_nom_out_month_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_nom_dom_month_filtered = filter_start_end_year(df_nom_dom_month, selected_start_year, selected_end_year, True)
        df_nom_dom_month_filtered = filter_by_quarter(df_nom_dom_month_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)

        df_inc_combined = merge_df_growth(df_jumlah_inc_filtered, df_nom_inc_filtered)
        df_out_combined = merge_df_growth(df_jumlah_out_filtered, df_nom_out_filtered)
        df_dom_combined = merge_df_growth(df_jumlah_dom_filtered, df_nom_dom_filtered)

        df_inc_combined_month = merge_df_growth(df_jumlah_inc_month_filtered, df_nom_inc_month_filtered, True)
        df_out_combined_month = merge_df_growth(df_jumlah_out_month_filtered, df_nom_out_month_filtered, True)
        df_dom_combined_month = merge_df_growth(df_jumlah_dom_month_filtered, df_nom_dom_month_filtered, True)

        st.header("Growth in Transactions")
        
        # Initialize default view mode
        if 'view_mode' not in st.session_state:
            st.session_state['view_mode'] = 'quarterly'
        
        # Toggle buttons dengan styling modern
        col_space1, col_toggle1, col_toggle2, col_space2 = st.columns([2, 1.5, 1.5, 2])
        
        # CSS styling untuk toggle buttons
        toggle_css = """
        <style>
            .toggle-container {
                display: flex;
                gap: 10px;
                justify-content: center;
                margin-bottom: 20px;
            }
            
            .toggle-btn {
                padding: 10px 20px;
                border-radius: 8px;
                border: 2px solid #e0e0e0;
                background-color: #f8f9fa;
                color: #333;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 15px;
                min-width: 140px;
            }
            
            .toggle-btn:hover {
                border-color: #3b82f6;
                background-color: #eff6ff;
                color: #1e40af;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(59, 130, 246, 0.15);
            }
            
            .toggle-btn.active {
                background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
                color: white;
                border-color: #1e40af;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            }
            
            .toggle-btn.active:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
            }
        </style>
        """
        st.markdown(toggle_css, unsafe_allow_html=True)
        
        # Render modern toggle slider
        col_space1, col_toggle, col_space2 = st.columns([1.5, 3, 1.5])
        
        with col_toggle:
            # Custom CSS untuk segmented control
            segmented_css = """
            <style>
                .segmented-control {
                    display: flex;
                    background: linear-gradient(to bottom, #f5f5f5, #efefef);
                    border-radius: 50px;
                    padding: 3px;
                    width: fit-content;
                    margin: 20px auto;
                    box-shadow: 
                        inset 0 2px 4px rgba(255,255,255,0.5),
                        inset 0 -2px 4px rgba(0,0,0,0.05),
                        0 4px 12px rgba(0,0,0,0.08);
                    gap: 4px;
                }
                
                .segmented-control button {
                    flex: 1;
                    padding: 12px 24px;
                    border: none;
                    background: transparent;
                    color: #666;
                    font-weight: 500;
                    font-size: 15px;
                    cursor: pointer;
                    border-radius: 48px;
                    transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
                    min-width: 130px;
                    white-space: nowrap;
                }
                
                .segmented-control button:hover {
                    background: rgba(59, 130, 246, 0.08);
                    color: #3b82f6;
                }
                
                .segmented-control button.active {
                    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                    color: white;
                    font-weight: 600;
                    box-shadow: 
                        0 4px 12px rgba(59, 130, 246, 0.35),
                        inset 0 1px 2px rgba(255,255,255,0.2);
                }
            </style>
            """
            st.markdown(segmented_css, unsafe_allow_html=True)
        
        # Create button group
        col_q, col_m = st.columns([1, 1], gap="small")
        
        with col_q:
            is_quarterly = st.session_state['view_mode'] == 'quarterly'
            btn_style = "primary" if is_quarterly else "secondary"
            if st.button("📊 Quarterly", key="toggle_quarterly", use_container_width=True, 
                        type=btn_style):
                st.session_state['view_mode'] = 'quarterly'
                st.rerun()
        
        with col_m:
            is_monthly = st.session_state['view_mode'] == 'monthly'
            btn_style = "primary" if is_monthly else "secondary"
            if st.button("📅 Monthly", key="toggle_monthly", use_container_width=True,
                        type=btn_style):
                st.session_state['view_mode'] = 'monthly'
                st.rerun()
        
        st.divider()
        
        # QUARTERLY SECTION
        if st.session_state['view_mode'] == 'quarterly':
            st.subheader("📊 Data Transaksi Kuartalan")
            
            # KPI Cards - Tampilkan total dari semua data
            st.markdown("<h3 style='margin-top: 20px; margin-bottom: 15px;'>📈 Ringkasan Transaksi</h3>", unsafe_allow_html=True)
            
            # Calculate totals
            total_inc_freq = df_inc_combined['Sum of Fin Jumlah Inc'].sum()
            total_inc_value = df_inc_combined['Sum of Fin Nilai Inc'].sum()
            total_out_freq = df_out_combined['Sum of Fin Jumlah Out'].sum()
            total_out_value = df_out_combined['Sum of Fin Nilai Out'].sum()
            total_dom_freq = df_dom_combined['Sum of Fin Jumlah Dom'].sum()
            total_dom_value = df_dom_combined['Sum of Fin Nilai Dom'].sum()
            total_all_freq = total_inc_freq + total_out_freq + total_dom_freq
            total_all_value = total_inc_value + total_out_value + total_dom_value
            
            # KPI Cards CSS
            kpi_css = """
            <style>
                .kpi-card {
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                    border-left: 5px solid;
                    transition: transform 0.2s ease, box-shadow 0.2s ease;
                }
                .kpi-card:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
                }
                .kpi-title {
                    font-size: 14px;
                    color: #6b7280;
                    font-weight: 600;
                    margin-bottom: 8px;
                }
                .kpi-value-main {
                    font-size: 28px;
                    font-weight: 700;
                    margin-bottom: 4px;
                }
                .kpi-value-sub {
                    font-size: 16px;
                    color: #6b7280;
                    font-weight: 500;
                }
            </style>
            """
            st.markdown(kpi_css, unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #F5B0CB;">
                    <div class="kpi-title">📥 INCOMING</div>
                    <div class="kpi-value-main" style="color: #F5B0CB;">{total_inc_freq:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #F5B0CB; margin-top: 12px;">Rp {total_inc_value/1e12:,.2f} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #F5CBA7;">
                    <div class="kpi-title">📤 OUTGOING</div>
                    <div class="kpi-value-main" style="color: #F5CBA7;">{total_out_freq:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #F5CBA7; margin-top: 12px;">Rp {total_out_value/1e12:,.2f} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #5DADE2;">
                    <div class="kpi-title">🏠 DOMESTIK</div>
                    <div class="kpi-value-main" style="color: #5DADE2;">{total_dom_freq:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #5DADE2; margin-top: 12px;">Rp {total_dom_value/1e12:,.2f} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #6366f1;">
                    <div class="kpi-title">💰 TOTAL</div>
                    <div class="kpi-value-main" style="color: #6366f1;">{total_all_freq:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #6366f1; margin-top: 12px;">Rp {total_all_value/1e12:,.2f} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
            
            # Grafik Gabungan (Stacked Bar + Line)
            st.markdown("<h3 style='margin-bottom: 15px;'>📊 Grafik Gabungan - Nilai Transaksi</h3>", unsafe_allow_html=True)
            make_stacked_bar_line_chart_combined(
                df_inc_combined,
                df_out_combined,
                df_dom_combined,
                is_month=False,
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )

            # Perbandingan Periode (Quarter) - VS
            st.markdown("<h3 style='margin-top: 25px; margin-bottom: 10px;'>🆚 Perbandingan Periode (Kuartal)</h3>", unsafe_allow_html=True)
            st.markdown(
                "<p style='color:#6b7280; margin-top:-6px; margin-bottom:12px;'>Pilih 2 periode (tahun & kuartal) untuk dibandingkan. Grafik hanya menampilkan 2 batang yang relevan.</p>",
                unsafe_allow_html=True,
            )

            # Sinkronkan default Periode A/B dengan filter sidebar (Start/End)
            _start_q_int = int(str(selected_start_quarter).replace("Q", ""))
            _end_q_int = int(str(selected_end_quarter).replace("Q", ""))
            _vs_filter_sig = (int(selected_start_year), _start_q_int, int(selected_end_year), _end_q_int)
            if st.session_state.get("_vs_filter_sig") != _vs_filter_sig:
                st.session_state["_vs_filter_sig"] = _vs_filter_sig
                st.session_state["vs_year_a"] = int(selected_start_year)
                st.session_state["vs_q_a"] = int(_start_q_int)
                st.session_state["vs_year_b"] = int(selected_end_year)
                st.session_state["vs_q_b"] = int(_end_q_int)

            cmp_years = sorted(df_total_combined['Year'].unique().tolist()) if not df_total_combined.empty else sorted(df_preprocessed_time['Year'].unique().tolist())
            cmp_quarters = [1, 2, 3, 4]

            c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 1.2])
            with c1:
                vs_year_a = st.selectbox("Tahun A", cmp_years, key="vs_year_a")
            with c2:
                vs_q_a = st.selectbox("Kuartal A", cmp_quarters, format_func=lambda q: f"Q{q}", key="vs_q_a")
            with c3:
                vs_year_b = st.selectbox("Tahun B", cmp_years, key="vs_year_b")
            with c4:
                vs_q_b = st.selectbox("Kuartal B", cmp_quarters, format_func=lambda q: f"Q{q}", key="vs_q_b")

            c5, c6 = st.columns([1.2, 1.6])
            with c5:
                vs_metric = st.selectbox("Metrik", ["Nominal", "Frekuensi"], key="vs_metric")
            with c6:
                vs_trx = st.selectbox("Jenis Transaksi", ["Incoming", "Outgoing", "Domestik", "Total"], key="vs_trx")

            sum_trx_type = "Nilai" if vs_metric == "Nominal" else "Jumlah"

            if vs_trx == "Incoming":
                df_vs_src = df_nom_inc_filtered if sum_trx_type == "Nilai" else df_jumlah_inc_filtered
                trx_code = "Inc"
                is_combined = False
            elif vs_trx == "Outgoing":
                df_vs_src = df_nom_out_filtered if sum_trx_type == "Nilai" else df_jumlah_out_filtered
                trx_code = "Out"
                is_combined = False
            elif vs_trx == "Domestik":
                df_vs_src = df_nom_dom_filtered if sum_trx_type == "Nilai" else df_jumlah_dom_filtered
                trx_code = "Dom"
                is_combined = False
            else:
                df_vs_src = df_total_combined
                trx_code = "Total"
                is_combined = True

            if trx_code == "Total":
                df_vs_inc = df_nom_inc_filtered if sum_trx_type == "Nilai" else df_jumlah_inc_filtered
                df_vs_out = df_nom_out_filtered if sum_trx_type == "Nilai" else df_jumlah_out_filtered
                df_vs_dom = df_nom_dom_filtered if sum_trx_type == "Nilai" else df_jumlah_dom_filtered

                make_quarter_vs_quarter_chart_total_breakdown(
                    df_inc=df_vs_inc,
                    df_out=df_vs_out,
                    df_dom=df_vs_dom,
                    year_a=int(vs_year_a),
                    quarter_a=int(vs_q_a),
                    year_b=int(vs_year_b),
                    quarter_b=int(vs_q_b),
                    sum_trx_type=sum_trx_type,
                    font_size=_growth_font_size,
                    label_font_size=_growth_label_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
            else:
                make_quarter_vs_quarter_chart(
                    df=df_vs_src,
                    year_a=int(vs_year_a),
                    quarter_a=int(vs_q_a),
                    year_b=int(vs_year_b),
                    quarter_b=int(vs_q_b),
                    sum_trx_type=sum_trx_type,
                    trx_type=trx_code,
                    is_combined=is_combined,
                    font_size=_growth_font_size,
                    label_font_size=_growth_label_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )

            # Tabel VS Market Share (Jakarta vs Nasional)
            df_national_raw = st.session_state.get('df_national')
            if df_national_raw is None:
                st.info("Upload data nasional (Raw_JKTNasional) di Summary dulu untuk menampilkan tabel market share vs nasional.")
            else:
                try:
                    df_national_q = add_quarter_column(df_national_raw.copy())
                    df_national_grouped = preprocess_data_national(df_national_q, True, True)

                    jkt_a = df_sum_time[(df_sum_time['Year'] == int(vs_year_a)) & (df_sum_time['Quarter'] == int(vs_q_a))].copy()
                    nat_a = df_national_grouped[(df_national_grouped['Year'] == int(vs_year_a)) & (df_national_grouped['Quarter'] == int(vs_q_a))].copy()

                    jkt_b = df_sum_time[(df_sum_time['Year'] == int(vs_year_b)) & (df_sum_time['Quarter'] == int(vs_q_b))].copy()
                    nat_b = df_national_grouped[(df_national_grouped['Year'] == int(vs_year_b)) & (df_national_grouped['Quarter'] == int(vs_q_b))].copy()

                    if jkt_a.empty or nat_a.empty or jkt_b.empty or nat_b.empty:
                        st.warning("Data market share tidak lengkap untuk salah satu periode (A/B).")
                    else:
                        def _build_ms_row(df_ms: pd.DataFrame, label: str) -> dict:
                            # df_ms: output compile_data_market_share
                            return {
                                "Periode": label,
                                "Jakarta Nom (T)": df_ms["Nominal (dalam triliun)"].iloc[0],
                                "Nasional Nom (T)": df_ms["Nominal (dalam triliun)"].iloc[1],
                                "Market Share Nom (%)": df_ms["Nominal (dalam triliun)"].iloc[2],
                                "Jakarta Frek (Juta)": df_ms["Frekuensi (dalam jutaan)"].iloc[0],
                                "Nasional Frek (Juta)": df_ms["Frekuensi (dalam jutaan)"].iloc[1],
                                "Market Share Frek (%)": df_ms["Frekuensi (dalam jutaan)"].iloc[2],
                            }

                        if trx_code == "Total":
                            ms_a_inc = compile_data_market_share(jkt_a, nat_a, "Inc")
                            ms_a_out = compile_data_market_share(jkt_a, nat_a, "Out")
                            ms_a_dom = compile_data_market_share(jkt_a, nat_a, "Dom")
                            ms_a = compile_data_market_share(jkt_a, nat_a, "Total", ms_a_inc, ms_a_out, ms_a_dom)

                            ms_b_inc = compile_data_market_share(jkt_b, nat_b, "Inc")
                            ms_b_out = compile_data_market_share(jkt_b, nat_b, "Out")
                            ms_b_dom = compile_data_market_share(jkt_b, nat_b, "Dom")
                            ms_b = compile_data_market_share(jkt_b, nat_b, "Total", ms_b_inc, ms_b_out, ms_b_dom)
                        else:
                            ms_a = compile_data_market_share(jkt_a, nat_a, trx_code)
                            ms_b = compile_data_market_share(jkt_b, nat_b, trx_code)

                        st.markdown("<h4 style='margin-top: 10px; margin-bottom: 10px;'>📋 Tabel VS - Market Share Jakarta vs Nasional</h4>", unsafe_allow_html=True)
                        df_ms_vs = pd.DataFrame([
                            _build_ms_row(ms_a, f"Q{int(vs_q_a)} {int(vs_year_a)}"),
                            _build_ms_row(ms_b, f"Q{int(vs_q_b)} {int(vs_year_b)}"),
                        ])
                        st.dataframe(df_ms_vs, use_container_width=True, hide_index=True)
                        st.caption("Market Share = (Jakarta / Nasional) × 100. Nominal dalam triliun, Frekuensi dalam jutaan.")
                except Exception as e:
                    st.warning(f"Gagal memproses market share vs nasional: {e}")
            
            st.divider()
            
            if selected_jenis_transaksi == 'Incoming' or selected_jenis_transaksi == 'All':
                st.markdown("<h3 style='background-color: #f0f7ff; border-left: 5px solid #3b82f6; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px;'>📥 INCOMING - Data Transaksi</h3>", unsafe_allow_html=True)
                
                # Display table with proper numeric sorting
                df_inc_combined_display = rename_format_growth_df(df_inc_combined.copy(), "Inc")
                st.dataframe(
                    df_inc_combined_display, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config=_get_growth_column_config("Incoming")
                )
                
                # Detail selection with dropdown
                col_detail, col_empty = st.columns([3, 5])
                with col_detail:
                    period_options = [f"Q{int(row['Quarter'])} {int(row['Year'])}" for _, row in df_inc_combined.iterrows()]
                    selected_period = st.selectbox("Pilih periode untuk detail", period_options, key="sel_inc_period", label_visibility="collapsed")
                    if selected_period:
                        for idx, row in df_inc_combined.iterrows():
                            if f"Q{int(row['Quarter'])} {int(row['Year'])}" == selected_period:
                                year_val = int(row['Year'])
                                quarter_val = int(row['Quarter'])
                                
                                with st.container(border=True):
                                    st.markdown(f"**📊 Detail per PJP - {selected_period} (Incoming)**")
                                    _render_pjp_detail(df_preprocessed_time, year_val, quarter_val, "Incoming")
                                break
                
                make_combined_bar_line_chart(
                    df_jumlah_inc_filtered,
                    "Jumlah",
                    "Inc",
                    font_size=_growth_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
                make_combined_bar_line_chart(
                    df_nom_inc_filtered,
                    "Nilai",
                    "Inc",
                    font_size=_growth_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
                st.divider()

            if selected_jenis_transaksi == 'Outgoing' or selected_jenis_transaksi == 'All':
                st.markdown("<h3 style='background-color: #fef2f2; border-left: 5px solid #ef4444; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px;'>📤 OUTGOING - Data Transaksi</h3>", unsafe_allow_html=True)
                
                # Display table with proper numeric sorting
                df_out_combined_display = rename_format_growth_df(df_out_combined.copy(), "Out")
                st.dataframe(
                    df_out_combined_display, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config=_get_growth_column_config("Outgoing")
                )
                
                # Detail selection with dropdown
                col_detail, col_empty = st.columns([3, 5])
                with col_detail:
                    period_options = [f"Q{int(row['Quarter'])} {int(row['Year'])}" for _, row in df_out_combined.iterrows()]
                    selected_period = st.selectbox("Pilih periode untuk detail", period_options, key="sel_out_period", label_visibility="collapsed")
                    if selected_period:
                        for idx, row in df_out_combined.iterrows():
                            if f"Q{int(row['Quarter'])} {int(row['Year'])}" == selected_period:
                                year_val = int(row['Year'])
                                quarter_val = int(row['Quarter'])
                                
                                with st.container(border=True):
                                    st.markdown(f"**📊 Detail per PJP - {selected_period} (Outgoing)**")
                                    _render_pjp_detail(df_preprocessed_time, year_val, quarter_val, "Outgoing")
                                break
                
                make_combined_bar_line_chart(
                    df_jumlah_out_filtered,
                    "Jumlah",
                    "Out",
                    font_size=_growth_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
                make_combined_bar_line_chart(
                    df_nom_out_filtered,
                    "Nilai",
                    "Out",
                    font_size=_growth_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
                st.divider()
                
            if selected_jenis_transaksi == 'Domestik' or selected_jenis_transaksi == 'All':
                st.markdown("<h3 style='background-color: #f0fdf4; border-left: 5px solid #16a34a; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px;'>🏠 DOMESTIK - Data Transaksi</h3>", unsafe_allow_html=True)
                
                # Display table with proper numeric sorting
                df_dom_combined_display = rename_format_growth_df(df_dom_combined.copy(), "Dom")
                st.dataframe(
                    df_dom_combined_display, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config=_get_growth_column_config("Domestik")
                )
                
                # Detail selection with dropdown
                col_detail, col_empty = st.columns([3, 5])
                with col_detail:
                    period_options = [f"Q{int(row['Quarter'])} {int(row['Year'])}" for _, row in df_dom_combined.iterrows()]
                    selected_period = st.selectbox("Pilih periode untuk detail", period_options, key="sel_dom_period", label_visibility="collapsed")
                    if selected_period:
                        for idx, row in df_dom_combined.iterrows():
                            if f"Q{int(row['Quarter'])} {int(row['Year'])}" == selected_period:
                                year_val = int(row['Year'])
                                quarter_val = int(row['Quarter'])
                                
                                with st.container(border=True):
                                    st.markdown(f"**📊 Detail per PJP - {selected_period} (Domestik)**")
                                    _render_pjp_detail(df_preprocessed_time, year_val, quarter_val, "Domestik")
                                break
                
                make_combined_bar_line_chart(
                    df_jumlah_dom_filtered,
                    "Jumlah",
                    "Dom",
                    font_size=_growth_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
                make_combined_bar_line_chart(
                    df_nom_dom_filtered,
                    "Nilai",
                    "Dom",
                    font_size=_growth_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
                st.divider()

            st.markdown("<h3 style='background-color: #fef3c7; border-left: 5px solid #f59e0b; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px; margin-top: 30px;'>💰 TOTAL KESELURUHAN - Data Transaksi (Kuartalan)</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color: #92400e; font-weight: 500; margin-bottom: 15px;'>Gabungan Data Transaksi Incoming + Outgoing + Domestik (Frekuensi & Nominal)</p>", unsafe_allow_html=True)
            
            df_total_combined_display = df_total_combined.copy()
            df_total_combined_display = rename_format_growth_df(df_total_combined_display, "Total")
            st.dataframe(
                df_total_combined_display, 
                use_container_width=True, 
                hide_index=True,
                column_config=_get_growth_column_config("Total")
            )
            
            # Detail selection with dropdown
            col_detail, col_empty = st.columns([3, 5])
            with col_detail:
                period_options = [f"Q{int(row['Quarter'])} {int(row['Year'])}" for _, row in df_total_combined.iterrows()]
                selected_period = st.selectbox("Pilih periode untuk detail", period_options, key="sel_total_period", label_visibility="collapsed")
                if selected_period:
                    for idx, row in df_total_combined.iterrows():
                        if f"Q{int(row['Quarter'])} {int(row['Year'])}" == selected_period:
                            year_val = int(row['Year'])
                            quarter_val = int(row['Quarter'])
                            
                            with st.container(border=True):
                                st.markdown(f"**📊 Detail per PJP - {selected_period} (Total)**")
                                _render_pjp_detail(df_preprocessed_time, year_val, quarter_val, "Total")
                            break

            st.markdown("<hr style='border-top: 2px dashed #f59e0b; margin: 20px 0;'>", unsafe_allow_html=True)
            st.markdown("### 📊 Visualisasi Keseluruhan Data Transaksi (Frekuensi & Nominal Tergabung)")

            st.caption(
                "Grafik berikut menampilkan stacked bar (Incoming/Outgoing/Domestik) pada sumbu kiri dan garis Growth (YoY & QtQ) pada sumbu kanan. "
                "Gunakan legend untuk menyembunyikan/menampilkan garis tertentu; label % akan ikut hilang saat garis di-hide."
            )

            # Visual-only filter: tampilkan/sematikan kuartal tertentu (growth tidak dihitung ulang)
            overall_period_options = (
                df_total_combined.assign(
                    _period=lambda d: d["Year"].astype(int).astype(str) + " Q" + d["Quarter"].astype(int).astype(str)
                )
                .sort_values(["Year", "Quarter"])
                ["_period"]
                .dropna()
                .astype(str)
                .tolist()
            )
            overall_period_sig = "|".join(overall_period_options)
            if st.session_state.get("overall_visible_period_sig") != overall_period_sig:
                st.session_state["overall_visible_period_sig"] = overall_period_sig
                st.session_state["overall_visible_periods"] = overall_period_options

            st.multiselect(
                "Tampilkan Kuartal",
                options=overall_period_options,
                key="overall_visible_periods",
                help="Hanya menyaring tampilan chart. Nilai YoY/QtQ tetap nilai asli dari perhitungan data.",
            )

            st.markdown("#### 📦 Volume / Frekuensi")
            st.caption("Sumbu kiri: Volume (Jutaan). Sumbu kanan: Growth YoY & QtQ (%).")

            make_overall_total_stacked_growth_chart(
                df_total=df_total_combined,
                df_inc=df_jumlah_inc_filtered,
                df_out=df_jumlah_out_filtered,
                df_dom=df_jumlah_dom_filtered,
                sum_trx_type="Jumlah",
                is_month=False,
                show_breakdown_growth=True,
                visible_periods=st.session_state.get("overall_visible_periods"),
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )
            _render_overall_growth_detail_table_quarterly(
                df_total_combined=df_total_combined,
                df_inc=df_jumlah_inc_filtered,
                df_out=df_jumlah_out_filtered,
                df_dom=df_jumlah_dom_filtered,
                sum_trx_type="Jumlah",
                visible_periods=st.session_state.get("overall_visible_periods"),
                ordered_periods=overall_period_options,
            )

            st.markdown("#### 💰 Nominal")
            st.caption("Sumbu kiri: Nilai (Rp Triliun). Sumbu kanan: Growth YoY & QtQ (%).")
            make_overall_total_stacked_growth_chart(
                df_total=df_total_combined,
                df_inc=df_nom_inc_filtered,
                df_out=df_nom_out_filtered,
                df_dom=df_nom_dom_filtered,
                sum_trx_type="Nilai",
                is_month=False,
                show_breakdown_growth=True,
                visible_periods=st.session_state.get("overall_visible_periods"),
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )
            _render_overall_growth_detail_table_quarterly(
                df_total_combined=df_total_combined,
                df_inc=df_nom_inc_filtered,
                df_out=df_nom_out_filtered,
                df_dom=df_nom_dom_filtered,
                sum_trx_type="Nilai",
                visible_periods=st.session_state.get("overall_visible_periods"),
                ordered_periods=overall_period_options,
            )

        # MONTHLY SECTION
        if st.session_state['view_mode'] == 'monthly':
            st.subheader("📅 Data Transaksi Bulanan")
            
            # KPI Cards - Monthly
            st.markdown("<h3 style='margin-top: 20px; margin-bottom: 15px;'>📈 Ringkasan Transaksi</h3>", unsafe_allow_html=True)
            
            # Calculate totals
            total_inc_freq_m = df_inc_combined_month['Sum of Fin Jumlah Inc'].sum()
            total_inc_value_m = df_inc_combined_month['Sum of Fin Nilai Inc'].sum()
            total_out_freq_m = df_out_combined_month['Sum of Fin Jumlah Out'].sum()
            total_out_value_m = df_out_combined_month['Sum of Fin Nilai Out'].sum()
            total_dom_freq_m = df_dom_combined_month['Sum of Fin Jumlah Dom'].sum()
            total_dom_value_m = df_dom_combined_month['Sum of Fin Nilai Dom'].sum()
            total_all_freq_m = total_inc_freq_m + total_out_freq_m + total_dom_freq_m
            total_all_value_m = total_inc_value_m + total_out_value_m + total_dom_value_m
            
            col1_kpi, col2_kpi, col3_kpi, col4_kpi = st.columns(4)
            
            with col1_kpi:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #F5B0CB;">
                    <div class="kpi-title">📥 INCOMING</div>
                    <div class="kpi-value-main" style="color: #F5B0CB;">{total_inc_freq_m:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #F5B0CB; margin-top: 12px;">Rp {total_inc_value_m/1e12:,.2f} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2_kpi:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #F5CBA7;">
                    <div class="kpi-title">📤 OUTGOING</div>
                    <div class="kpi-value-main" style="color: #F5CBA7;">{total_out_freq_m:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #F5CBA7; margin-top: 12px;">Rp {total_out_value_m/1e12:,.2f} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3_kpi:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #5DADE2;">
                    <div class="kpi-title">🏠 DOMESTIK</div>
                    <div class="kpi-value-main" style="color: #5DADE2;">{total_dom_freq_m:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #5DADE2; margin-top: 12px;">Rp {total_dom_value_m/1e12:,.2f} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4_kpi:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #6366f1;">
                    <div class="kpi-title">💰 TOTAL</div>
                    <div class="kpi-value-main" style="color: #6366f1;">{total_all_freq_m:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #6366f1; margin-top: 12px;">Rp {total_all_value_m/1e12:,.2f} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
            
            # Grafik Gabungan (Stacked Bar + Line) - Monthly
            st.markdown("<h3 style='margin-bottom: 15px;'>📊 Grafik Gabungan - Nilai Transaksi</h3>", unsafe_allow_html=True)
            make_stacked_bar_line_chart_combined(
                df_inc_combined_month,
                df_out_combined_month,
                df_dom_combined_month,
                is_month=True,
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )
            
            st.divider()
            
            col1, col2, col3 = st.columns(3)
            
            if selected_jenis_transaksi == 'Incoming' or selected_jenis_transaksi == 'All':
                with col1:
                    st.markdown("<h4 style='background-color: #f0f7ff; border-left: 5px solid #3b82f6; padding: 10px 12px; border-radius: 5px; margin-bottom: 15px;'>📥 INCOMING (Bulanan)</h4>", unsafe_allow_html=True)
                    
                    df_inc_combined_month_display = rename_format_growth_monthly_df(df_inc_combined_month.copy(), "Inc")
                    st.dataframe(
                        df_inc_combined_month_display, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config=_get_growth_column_config("Incoming")
                    )
                    
                    # Detail selection with dropdown
                    period_options_m = [f"{row['Month']} {int(row['Year'])}" for _, row in df_inc_combined_month.iterrows()]
                    selected_period_m = st.selectbox("Detail:", period_options_m, key="sel_inc_m_period", label_visibility="collapsed")
                    if selected_period_m:
                        for idx, row in df_inc_combined_month.iterrows():
                            if f"{row['Month']} {int(row['Year'])}" == selected_period_m:
                                year_val = int(row['Year'])
                                month_val = row['Month']
                                
                                with st.container(border=True):
                                    st.markdown(f"**📊 Detail per PJP - {selected_period_m} (Incoming)**")
                                    _render_pjp_detail_month(df_preprocessed_time, year_val, str(month_val), "Incoming")
                                break
            
            if selected_jenis_transaksi == 'Outgoing' or selected_jenis_transaksi == 'All':
                with col2:
                    st.markdown("<h4 style='background-color: #fef2f2; border-left: 5px solid #ef4444; padding: 10px 12px; border-radius: 5px; margin-bottom: 15px;'>📤 OUTGOING (Bulanan)</h4>", unsafe_allow_html=True)
                    
                    df_out_combined_month_display = rename_format_growth_monthly_df(df_out_combined_month.copy(), "Out")
                    st.dataframe(
                        df_out_combined_month_display, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config=_get_growth_column_config("Outgoing")
                    )
                    
                    # Detail selection with dropdown
                    period_options_m = [f"{row['Month']} {int(row['Year'])}" for _, row in df_out_combined_month.iterrows()]
                    selected_period_m = st.selectbox("Detail:", period_options_m, key="sel_out_m_period", label_visibility="collapsed")
                    if selected_period_m:
                        for idx, row in df_out_combined_month.iterrows():
                            if f"{row['Month']} {int(row['Year'])}" == selected_period_m:
                                year_val = int(row['Year'])
                                month_val = row['Month']
                                
                                with st.container(border=True):
                                    st.markdown(f"**📊 Detail per PJP - {selected_period_m} (Outgoing)**")
                                    _render_pjp_detail_month(df_preprocessed_time, year_val, str(month_val), "Outgoing")
                                break
            
            if selected_jenis_transaksi == 'Domestik' or selected_jenis_transaksi == 'All':
                with col3:
                    st.markdown("<h4 style='background-color: #f0fdf4; border-left: 5px solid #16a34a; padding: 10px 12px; border-radius: 5px; margin-bottom: 15px;'>🏠 DOMESTIK (Bulanan)</h4>", unsafe_allow_html=True)
                    
                    df_dom_combined_month_display = rename_format_growth_monthly_df(df_dom_combined_month.copy(), "Dom")
                    st.dataframe(
                        df_dom_combined_month_display, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config=_get_growth_column_config("Domestik")
                    )
                    
                    # Detail selection with dropdown
                    period_options_m = [f"{row['Month']} {int(row['Year'])}" for _, row in df_dom_combined_month.iterrows()]
                    selected_period_m = st.selectbox("Detail:", period_options_m, key="sel_dom_m_period", label_visibility="collapsed")
                    if selected_period_m:
                        for idx, row in df_dom_combined_month.iterrows():
                            if f"{row['Month']} {int(row['Year'])}" == selected_period_m:
                                year_val = int(row['Year'])
                                month_val = row['Month']
                                
                                with st.container(border=True):
                                    st.markdown(f"**📊 Detail per PJP - {selected_period_m} (Domestik)**")
                                    _render_pjp_detail_month(df_preprocessed_time, year_val, str(month_val), "Domestik")
                                break
            
            st.divider()
            
            make_combined_bar_line_chart(
                df_jumlah_inc_month_filtered,
                "Jumlah",
                "Inc",
                True,
                font_size=_growth_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )
            make_combined_bar_line_chart(
                df_nom_inc_month_filtered,
                "Nilai",
                "Inc",
                True,
                font_size=_growth_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )

            make_combined_bar_line_chart(
                df_jumlah_out_month_filtered,
                "Jumlah",
                "Out",
                True,
                font_size=_growth_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )
            make_combined_bar_line_chart(
                df_nom_out_month_filtered,
                "Nilai",
                "Out",
                True,
                font_size=_growth_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )

            make_combined_bar_line_chart(
                df_jumlah_dom_month_filtered,
                "Jumlah",
                "Dom",
                True,
                font_size=_growth_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )
            make_combined_bar_line_chart(
                df_nom_dom_month_filtered,
                "Nilai",
                "Dom",
                True,
                font_size=_growth_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )

            st.markdown("<h3 style='background-color: #fef3c7; border-left: 5px solid #f59e0b; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px; margin-top: 30px;'>💰 TOTAL KESELURUHAN - Data Transaksi (Bulanan)</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color: #92400e; font-weight: 500; margin-bottom: 15px;'>Gabungan Data Transaksi Incoming + Outgoing + Domestik per Bulan (Frekuensi & Nominal)</p>", unsafe_allow_html=True)
            df_total_month_combined_display = df_total_month_combined.copy()
            df_total_month_combined_display = rename_format_growth_monthly_df(df_total_month_combined_display, "Total")
            st.dataframe(
                df_total_month_combined_display, 
                use_container_width=True, 
                hide_index=True,
                column_config=_get_growth_column_config("Total")
            )
            
            # Detail selection with dropdown for monthly
            col_detail_m, col_empty_m = st.columns([3, 5])
            with col_detail_m:
                period_options_m = [f"{row['Month']} {int(row['Year'])}" for _, row in df_total_month_combined.iterrows()]
                selected_period_m = st.selectbox("Detail:", period_options_m, key="sel_total_m_period", label_visibility="collapsed")
                if selected_period_m:
                    for idx, row in df_total_month_combined.iterrows():
                        if f"{row['Month']} {int(row['Year'])}" == selected_period_m:
                            year_val = int(row['Year'])
                            month_val = row['Month']
                            
                            with st.container(border=True):
                                st.markdown(f"**📊 Detail per PJP - {selected_period_m} (Total)**")
                                _render_pjp_detail_month(df_preprocessed_time, year_val, str(month_val), "Total")
                            break

            st.markdown("<hr style='border-top: 2px dashed #f59e0b; margin: 20px 0;'>", unsafe_allow_html=True)
            st.markdown("### 📅 Visualisasi Keseluruhan Data Transaksi (Frekuensi & Nominal Tergabung)")
            make_overall_total_stacked_growth_chart(
                df_total=df_total_month_combined,
                df_inc=df_jumlah_inc_month_filtered,
                df_out=df_jumlah_out_month_filtered,
                df_dom=df_jumlah_dom_month_filtered,
                sum_trx_type="Jumlah",
                is_month=True,
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
            )
            make_overall_total_stacked_growth_chart(
                df_total=df_total_month_combined,
                df_inc=df_nom_inc_month_filtered,
                df_out=df_nom_out_month_filtered,
                df_dom=df_nom_dom_month_filtered,
                sum_trx_type="Nilai",
                is_month=True,
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
            )

else:
    st.warning("Please Upload the Main Excel File first in the Summary Section.")

