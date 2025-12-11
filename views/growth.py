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
        st.info("Use the filters to adjust the year-quarter range and transaction type.")

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
        
        # Toggle buttons dengan styling yang lebih menarik
        col_space1, col_toggle1, col_toggle2, col_space2 = st.columns([2, 1.5, 1.5, 2])
        
        with col_toggle1:
            is_quarterly = st.session_state['view_mode'] == 'quarterly'
            if st.button("📊 Quarterly", key="toggle_quarterly", use_container_width=True):
                st.session_state['view_mode'] = 'quarterly'
                st.rerun()
        
        with col_toggle2:
            is_monthly = st.session_state['view_mode'] == 'monthly'
            if st.button("📅 Monthly", key="toggle_monthly", use_container_width=True):
                st.session_state['view_mode'] = 'monthly'
                st.rerun()
        
        st.divider()
        
        # QUARTERLY SECTION
        if st.session_state['view_mode'] == 'quarterly':
            st.subheader("📊 Data Transaksi Kuartalan")
            
            if selected_jenis_transaksi == 'Incoming' or selected_jenis_transaksi == 'All':
                st.markdown("<h3 style='background-color: #f0f7ff; border-left: 5px solid #3b82f6; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px;'>📥 Data Transaksi Incoming</h3>", unsafe_allow_html=True)
                
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
                
                make_combined_bar_line_chart(df_jumlah_inc_filtered, "Jumlah", "Inc")
                make_combined_bar_line_chart(df_nom_inc_filtered, "Nilai", "Inc")
                st.divider()

            if selected_jenis_transaksi == 'Outgoing' or selected_jenis_transaksi == 'All':
                st.markdown("<h3 style='background-color: #fef2f2; border-left: 5px solid #ef4444; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px;'>📤 Data Transaksi Outgoing</h3>", unsafe_allow_html=True)
                
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
                
                make_combined_bar_line_chart(df_jumlah_out_filtered, "Jumlah", "Out")
                make_combined_bar_line_chart(df_nom_out_filtered, "Nilai", "Out")
                st.divider()
                
            if selected_jenis_transaksi == 'Domestik' or selected_jenis_transaksi == 'All':
                st.markdown("<h3 style='background-color: #f0fdf4; border-left: 5px solid #16a34a; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px;'>🏠 Data Transaksi Domestik</h3>", unsafe_allow_html=True)
                
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
                
                make_combined_bar_line_chart(df_jumlah_dom_filtered, "Jumlah", "Dom")
                make_combined_bar_line_chart(df_nom_dom_filtered, "Nilai", "Dom")
                st.divider()

            st.markdown("<div style='background-color: #fef3c7; border: 2px solid #f59e0b; padding: 20px; border-radius: 8px; margin: 30px 0;'>", unsafe_allow_html=True)
            st.markdown("<h3 style='margin-top: 0;'>⭐ Summary Keseluruhan Data Transaksi (Kuartalan)</h3>", unsafe_allow_html=True)
            st.markdown("Gabungan Data Transaksi **Incoming, Outgoing, dan Domestik** (Frekuensi & Nominal).")
            st.markdown("</div>", unsafe_allow_html=True)
            
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
            make_combined_bar_line_chart(df_total_combined, "Jumlah", "Total", False, True)
            make_combined_bar_line_chart(df_total_combined, "Nilai", "Total", False, True)

        # MONTHLY SECTION
        if st.session_state['view_mode'] == 'monthly':
            st.subheader("📅 Data Transaksi Bulanan")
            
            col1, col2, col3 = st.columns(3)
            
            if selected_jenis_transaksi == 'Incoming' or selected_jenis_transaksi == 'All':
                with col1:
                    st.markdown("<h4 style='background-color: #f0f7ff; border-left: 5px solid #3b82f6; padding: 10px 12px; border-radius: 5px; margin-bottom: 15px;'>📥 Data Transaksi Incoming (Bulanan)</h4>", unsafe_allow_html=True)
                    
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
                    st.markdown("<h4 style='background-color: #fef2f2; border-left: 5px solid #ef4444; padding: 10px 12px; border-radius: 5px; margin-bottom: 15px;'>📤 Data Transaksi Outgoing (Bulanan)</h4>", unsafe_allow_html=True)
                    
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
                    st.markdown("<h4 style='background-color: #f0fdf4; border-left: 5px solid #16a34a; padding: 10px 12px; border-radius: 5px; margin-bottom: 15px;'>🏠 Data Transaksi Domestik (Bulanan)</h4>", unsafe_allow_html=True)
                    
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
            
            make_combined_bar_line_chart(df_jumlah_inc_month_filtered, "Jumlah", "Inc", True)
            make_combined_bar_line_chart(df_nom_inc_month_filtered, "Nilai", "Inc", True)

            make_combined_bar_line_chart(df_jumlah_out_month_filtered, "Jumlah", "Out", True)
            make_combined_bar_line_chart(df_nom_out_month_filtered, "Nilai", "Out", True)

            make_combined_bar_line_chart(df_jumlah_dom_month_filtered, "Jumlah", "Dom", True)
            make_combined_bar_line_chart(df_nom_dom_month_filtered, "Nilai", "Dom", True)

            st.markdown("<div style='background-color: #fef3c7; border: 2px solid #f59e0b; padding: 20px; border-radius: 8px; margin: 30px 0;'>", unsafe_allow_html=True)
            st.markdown("<h3 style='margin-top: 0;'>⭐ Summary Keseluruhan Data Transaksi (Bulanan)</h3>", unsafe_allow_html=True)
            st.markdown("Gabungan Data Transaksi **Incoming, Outgoing, dan Domestik** per Bulan (Frekuensi & Nominal).")
            st.markdown("</div>", unsafe_allow_html=True)
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
            make_combined_bar_line_chart(df_total_month_combined, "Jumlah", "Total", True, True)
            make_combined_bar_line_chart(df_total_month_combined, "Nilai", "Total", True, True)

else:
    st.warning("Please Upload the Main Excel File first in the Summary Section.")