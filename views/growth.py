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
        if selected_jenis_transaksi == 'Incoming' or selected_jenis_transaksi == 'All':
            st.markdown("### Transaksi Incoming")
            
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
            st.markdown("### Transaksi Outgoing")
            
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
            st.markdown("### Transaksi Domestik")
            
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

        st.subheader("Data Transaksi Bulanan")
        col1, col2, col3 = st.columns(3)
        if selected_jenis_transaksi == 'Incoming' or selected_jenis_transaksi == 'All':
            with col1:
                st.markdown("### Incoming (Bulanan)")
                
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
                st.markdown("### Outgoing (Bulanan)")
                
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
                st.markdown("### Domestik (Bulanan)")
                
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

        make_combined_bar_line_chart(df_jumlah_inc_month_filtered, "Jumlah", "Inc", True)
        make_combined_bar_line_chart(df_nom_inc_month_filtered, "Nilai", "Inc", True)

        make_combined_bar_line_chart(df_jumlah_out_month_filtered, "Jumlah", "Out", True)
        make_combined_bar_line_chart(df_nom_out_month_filtered, "Nilai", "Out", True)

        make_combined_bar_line_chart(df_jumlah_dom_month_filtered, "Jumlah", "Dom", True)
        make_combined_bar_line_chart(df_nom_dom_month_filtered, "Nilai", "Dom", True)

        st.subheader("Summary Keseluruhan Data Transaksi")
        st.write("Gabungan Data Transaksi Incoming, Outgoing, dan Domestik.")
        
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

        st.markdown("### Visualisasi Keseluruhan Data Transaksi")
        make_combined_bar_line_chart(df_total_combined, "Jumlah", "Total", False, True)
        make_combined_bar_line_chart(df_total_combined, "Nilai", "Total", False, True)

        st.subheader("Summary Keseluruhan Data Transaksi (Bulanan)")
        st.write("Gabungan Data Transaksi Incoming, Outgoing, dan Domestik per Bulan.")
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

        st.markdown("### Visualisasi Keseluruhan Data Transaksi (Bulanan)")
        make_combined_bar_line_chart(df_total_month_combined, "Jumlah", "Total", True, True)
        make_combined_bar_line_chart(df_total_month_combined, "Nilai", "Total", True, True)

        # Detail per PJP berdasarkan periode yang dipilih
        st.divider()
        st.subheader("🔍 Detail Growth per PJP (berdasarkan Year-Quarter)")
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        with col_d1:
            trx_choice = st.selectbox("Jenis Transaksi", ["Total", "Incoming", "Outgoing", "Domestik"], key="detail_trx")
        with col_d2:
            year_choice = st.selectbox("Year", sorted(df_preprocessed_time['Year'].unique()), key="detail_year")
        with col_d3:
            quarter_choice = st.selectbox("Quarter", sorted(df_preprocessed_time['Quarter'].unique()), key="detail_quarter")
        with col_d4:
            st.markdown("\u00a0")
            if st.button("Lihat Detail", key="btn_detail_pjp"):
                _render_pjp_detail(df_preprocessed_time, int(year_choice), int(quarter_choice), trx_choice)

        # ============ GROWTH DETAIL ANALYSIS ============
        st.divider()
        st.header("📊 Analisis Detail Growth per PJP")
        
        with st.spinner('Mempersiapkan data detail growth...'):
            # Ambil data preprocessed untuk analisis detail
            df_preprocessed = preprocess_data(df, True)
            
            # Get unique periods dalam range yang dipilih
            df_in_range = df_preprocessed[
                (df_preprocessed['Year'] >= selected_start_year) & 
                (df_preprocessed['Year'] <= selected_end_year)
            ]
            
            unique_pjps = sorted(df_in_range['Nama PJP'].unique().tolist())
            
            st.subheader("Pilih Perbandingan")
            comparison_type = st.radio(
                "Tipe Perbandingan:",
                ("Quarter to Quarter (QtQ)", "Year on Year (YoY)"),
                horizontal=True
            )
            
            if comparison_type == "Quarter to Quarter (QtQ)":
                # QtQ Analysis
                quarters_in_range = ['Q1', 'Q2', 'Q3', 'Q4']
                col1, col2 = st.columns(2)
                with col1:
                    q1_select = st.selectbox('Quarter 1:', quarters_in_range, key='qtq_q1')
                with col2:
                    q2_select = st.selectbox('Quarter 2:', quarters_in_range, key='qtq_q2', index=1)
                
                # Hitung comparison year
                year_select = st.selectbox('Tahun:', sorted(df_in_range['Year'].unique().tolist()), key='qtq_year')
                
                if q1_select != q2_select:
                    # Prepare data untuk QtQ
                    q1_num = int(q1_select[1])
                    q2_num = int(q2_select[1])
                    
                    comparison_data = []
                    
                    for pjp in unique_pjps:
                        # Q1 data
                        q1_months = {1: ['January', 'February', 'March'],
                                    2: ['April', 'May', 'June'],
                                    3: ['July', 'August', 'September'],
                                    4: ['October', 'November', 'December']}[q1_num]
                        
                        q1_data = df_in_range[
                            (df_in_range['Nama PJP'] == pjp) &
                            (df_in_range['Year'] == year_select) &
                            (df_in_range['Month'].astype(str).isin(q1_months))
                        ]
                        
                        q1_jumlah = q1_data['Sum of Fin Jumlah Inc'].sum() + q1_data['Sum of Fin Jumlah Out'].sum() + q1_data['Sum of Fin Jumlah Dom'].sum()
                        q1_nilai = q1_data['Sum of Fin Nilai Inc'].sum() + q1_data['Sum of Fin Nilai Out'].sum() + q1_data['Sum of Fin Nilai Dom'].sum()
                        
                        # Q2 data
                        q2_months = {1: ['January', 'February', 'March'],
                                    2: ['April', 'May', 'June'],
                                    3: ['July', 'August', 'September'],
                                    4: ['October', 'November', 'December']}[q2_num]
                        
                        q2_data = df_in_range[
                            (df_in_range['Nama PJP'] == pjp) &
                            (df_in_range['Year'] == year_select) &
                            (df_in_range['Month'].astype(str).isin(q2_months))
                        ]
                        
                        q2_jumlah = q2_data['Sum of Fin Jumlah Inc'].sum() + q2_data['Sum of Fin Jumlah Out'].sum() + q2_data['Sum of Fin Jumlah Dom'].sum()
                        q2_nilai = q2_data['Sum of Fin Nilai Inc'].sum() + q2_data['Sum of Fin Nilai Out'].sum() + q2_data['Sum of Fin Nilai Dom'].sum()
                        
                        # Calculate growth
                        jumlah_growth = ((q2_jumlah - q1_jumlah) / q1_jumlah * 100) if q1_jumlah > 0 else 0
                        nilai_growth = ((q2_nilai - q1_nilai) / q1_nilai * 100) if q1_nilai > 0 else 0
                        
                        comparison_data.append({
                            'PJP': pjp,
                            f'{q1_select} Jumlah': int(q1_jumlah),
                            f'{q2_select} Jumlah': int(q2_jumlah),
                            'Growth Jumlah (%)': jumlah_growth,
                            f'{q1_select} Nilai': int(q1_nilai),
                            f'{q2_select} Nilai': int(q2_nilai),
                            'Growth Nilai (%)': nilai_growth,
                        })
                    
                    df_comparison = pd.DataFrame(comparison_data)
                    
                    st.subheader(f"Perbandingan {q1_select} vs {q2_select} {year_select} - Per PJP")
                    
                    # Format for display
                    df_display = df_comparison.copy()
                    df_display[f'{q1_select} Jumlah'] = df_display[f'{q1_select} Jumlah'].apply(lambda x: f"{x:,}".replace(',', '.'))
                    df_display[f'{q2_select} Jumlah'] = df_display[f'{q2_select} Jumlah'].apply(lambda x: f"{x:,}".replace(',', '.'))
                    df_display['Growth Jumlah (%)'] = df_display['Growth Jumlah (%)'].apply(lambda x: f"{x:+.2f}%".replace('.', ',').replace(',00%', '%'))
                    df_display[f'{q1_select} Nilai'] = df_display[f'{q1_select} Nilai'].apply(lambda x: f"{x:,}".replace(',', '.'))
                    df_display[f'{q2_select} Nilai'] = df_display[f'{q2_select} Nilai'].apply(lambda x: f"{x:,}".replace(',', '.'))
                    df_display['Growth Nilai (%)'] = df_display['Growth Nilai (%)'].apply(lambda x: f"{x:+.2f}%".replace('.', ',').replace(',00%', '%'))
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                    
                    # Expander untuk detail per PJP
                    for idx, row in df_comparison.iterrows():
                        pjp_name = row['PJP']
                        with st.expander(f"📈 {pjp_name} - Frekuensi: +{row['Growth Jumlah (%)']:+.1f}% | Nilai: +{row['Growth Nilai (%)']:+.1f}%"):
                            st.write(f"**Perbandingan Detail {q1_select} vs {q2_select} {year_select}**")
                            st.write(f"Frekuensi {q1_select}: {row[f'{q1_select} Jumlah']:,}")
                            st.write(f"Frekuensi {q2_select}: {row[f'{q2_select} Jumlah']:,}")
                            st.write(f"**Growth Frekuensi: {row['Growth Jumlah (%)']:+.2f}%**")
                            st.divider()
                            st.write(f"Nilai {q1_select}: Rp {row[f'{q1_select} Nilai']:,}")
                            st.write(f"Nilai {q2_select}: Rp {row[f'{q2_select} Nilai']:,}")
                            st.write(f"**Growth Nilai: {row['Growth Nilai (%)']:+.2f}%**")
                else:
                    st.warning("Pilih dua quarter yang berbeda untuk perbandingan")
            
            else:
                # YoY Analysis
                years_available = sorted(df_in_range['Year'].unique().tolist())
                if len(years_available) >= 2:
                    col1, col2 = st.columns(2)
                    with col1:
                        year1_select = st.selectbox('Tahun 1:', years_available, key='yoy_y1')
                    with col2:
                        year2_select = st.selectbox('Tahun 2:', years_available, key='yoy_y2', index=min(1, len(years_available)-1))
                    
                    quarter_select = st.selectbox('Quarter:', ['Q1', 'Q2', 'Q3', 'Q4'], key='yoy_q')
                    
                    if year1_select != year2_select:
                        q_num = int(quarter_select[1])
                        q_months = {1: ['January', 'February', 'March'],
                                   2: ['April', 'May', 'June'],
                                   3: ['July', 'August', 'September'],
                                   4: ['October', 'November', 'December']}[q_num]
                        
                        comparison_data = []
                        
                        for pjp in unique_pjps:
                            # Year 1 data
                            y1_data = df_in_range[
                                (df_in_range['Nama PJP'] == pjp) &
                                (df_in_range['Year'] == year1_select) &
                                (df_in_range['Month'].astype(str).isin(q_months))
                            ]
                            
                            y1_jumlah = y1_data['Sum of Fin Jumlah Inc'].sum() + y1_data['Sum of Fin Jumlah Out'].sum() + y1_data['Sum of Fin Jumlah Dom'].sum()
                            y1_nilai = y1_data['Sum of Fin Nilai Inc'].sum() + y1_data['Sum of Fin Nilai Out'].sum() + y1_data['Sum of Fin Nilai Dom'].sum()
                            
                            # Year 2 data
                            y2_data = df_in_range[
                                (df_in_range['Nama PJP'] == pjp) &
                                (df_in_range['Year'] == year2_select) &
                                (df_in_range['Month'].astype(str).isin(q_months))
                            ]
                            
                            y2_jumlah = y2_data['Sum of Fin Jumlah Inc'].sum() + y2_data['Sum of Fin Jumlah Out'].sum() + y2_data['Sum of Fin Jumlah Dom'].sum()
                            y2_nilai = y2_data['Sum of Fin Nilai Inc'].sum() + y2_data['Sum of Fin Nilai Out'].sum() + y2_data['Sum of Fin Nilai Dom'].sum()
                            
                            # Calculate growth
                            jumlah_growth = ((y2_jumlah - y1_jumlah) / y1_jumlah * 100) if y1_jumlah > 0 else 0
                            nilai_growth = ((y2_nilai - y1_nilai) / y1_nilai * 100) if y1_nilai > 0 else 0
                            
                            comparison_data.append({
                                'PJP': pjp,
                                f'{year1_select} Jumlah': int(y1_jumlah),
                                f'{year2_select} Jumlah': int(y2_jumlah),
                                'Growth Jumlah (%)': jumlah_growth,
                                f'{year1_select} Nilai': int(y1_nilai),
                                f'{year2_select} Nilai': int(y2_nilai),
                                'Growth Nilai (%)': nilai_growth,
                            })
                        
                        df_comparison = pd.DataFrame(comparison_data)
                        
                        st.subheader(f"Perbandingan YoY {quarter_select} {year1_select} vs {year2_select} - Per PJP")
                        
                        # Format for display
                        df_display = df_comparison.copy()
                        df_display[f'{year1_select} Jumlah'] = df_display[f'{year1_select} Jumlah'].apply(lambda x: f"{x:,}".replace(',', '.'))
                        df_display[f'{year2_select} Jumlah'] = df_display[f'{year2_select} Jumlah'].apply(lambda x: f"{x:,}".replace(',', '.'))
                        df_display['Growth Jumlah (%)'] = df_display['Growth Jumlah (%)'].apply(lambda x: f"{x:+.2f}%".replace('.', ',').replace(',00%', '%'))
                        df_display[f'{year1_select} Nilai'] = df_display[f'{year1_select} Nilai'].apply(lambda x: f"{x:,}".replace(',', '.'))
                        df_display[f'{year2_select} Nilai'] = df_display[f'{year2_select} Nilai'].apply(lambda x: f"{x:,}".replace(',', '.'))
                        df_display['Growth Nilai (%)'] = df_display['Growth Nilai (%)'].apply(lambda x: f"{x:+.2f}%".replace('.', ',').replace(',00%', '%'))
                        
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
                        
                        # Expander untuk detail per PJP
                        for idx, row in df_comparison.iterrows():
                            pjp_name = row['PJP']
                            with st.expander(f"📈 {pjp_name} - Frekuensi: +{row['Growth Jumlah (%)']:+.1f}% | Nilai: +{row['Growth Nilai (%)']:+.1f}%"):
                                st.write(f"**Perbandingan Detail {quarter_select} {year1_select} vs {year2_select}**")
                                st.write(f"Frekuensi {year1_select}: {row[f'{year1_select} Jumlah']:,}")
                                st.write(f"Frekuensi {year2_select}: {row[f'{year2_select} Jumlah']:,}")
                                st.write(f"**Growth Frekuensi: {row['Growth Jumlah (%)']:+.2f}%**")
                                st.divider()
                                st.write(f"Nilai {year1_select}: Rp {row[f'{year1_select} Nilai']:,}")
                                st.write(f"Nilai {year2_select}: Rp {row[f'{year2_select} Nilai']:,}")
                                st.write(f"**Growth Nilai: {row['Growth Nilai (%)']:+.2f}%**")
                else:
                    st.warning("Butuh minimal 2 tahun data untuk analisis YoY")
else:
    st.warning("Please Upload the Main Excel File first in the Summary Section.")