import pandas as pd
import streamlit as st
import calendar

from service.preprocess import *
from service.visualize import *

# Initial Page Setup
set_page_visuals("viz")

if st.session_state['df_national'] is not None and st.session_state['df'] is not None:
    df_national = st.session_state['df_national']
    df = st.session_state['df']

    with st.sidebar:
        with st.expander("Filter Profile", True):
            min_year_national = df_national['Year'].min()
            min_year_df = df['Year'].min()
            max_year_national = df_national['Year'].max()
            max_year_df = df['Year'].max()

            min_year = max(min_year_national, min_year_df)
            max_year = min(max_year_national, max_year_df)

            unique_years = sorted(df['Year'].unique().tolist())

            for index, year in enumerate(unique_years):
                if year >= min_year:
                    sliced_years = unique_years[index:]
                    break

            quarters = df['Quarter'].unique().tolist()

            # Tambahkan filter tahun mulai/akhir dan bulan mulai/akhir
            col1, col2 = st.columns(2)
            with col1:
                selected_start_year = st.selectbox('Tahun Mulai:', sliced_years, key="key_start_year")
            with col2:
                selected_end_year = st.selectbox('Tahun Akhir:', [y for y in sliced_years if y >= selected_start_year], key="key_end_year")

            months = list(calendar.month_name)[1:]
            col3, col4 = st.columns(2)
            with col3:
                selected_start_month = st.selectbox('Bulan Mulai:', months, key="key_start_month")
            with col4:
                selected_end_month = st.selectbox('Bulan Akhir:', [m for m in months if months.index(m) >= months.index(selected_start_month)], key="key_end_month")

                selected_quarter_pjp = st.selectbox('Select Quarter:', quarters, key="key_quarter_pjp")

                # Mode filter: pilih melihat per Quarter atau per Range (start-end)
                selected_mode = st.radio('Mode Filter:', ['Quarter', 'Range'], horizontal=True, key='key_mode_filter')

            df_national = add_quarter_column(df_national)
            # Siapkan versi national/prekspased grouped untuk Quarter dan Month
            df_national_grouped_q = preprocess_data_national(df_national, True, True)
            df_national_grouped_m = preprocess_data_national(df_national, False, False)
            df_preprocessed = preprocess_data(df, True)

            df_preprocessed_grouped_q = df_preprocessed.groupby(['Year', 'Quarter'], observed=False).agg({
                'Sum of Fin Jumlah Inc': 'sum',
                'Sum of Fin Jumlah Out': 'sum',
                'Sum of Fin Jumlah Dom': 'sum',
                'Sum of Fin Nilai Inc': 'sum',
                'Sum of Fin Nilai Out': 'sum',
                'Sum of Fin Nilai Dom': 'sum',
                'Sum of Total Nom': 'sum'
            }).reset_index()

            df_preprocessed_grouped_m = df_preprocessed.groupby(['Year', 'Month'], observed=False).agg({
                'Sum of Fin Jumlah Inc': 'sum',
                'Sum of Fin Jumlah Out': 'sum',
                'Sum of Fin Jumlah Dom': 'sum',
                'Sum of Fin Nilai Inc': 'sum',
                'Sum of Fin Nilai Out': 'sum',
                'Sum of Fin Nilai Dom': 'sum',
                'Sum of Total Nom': 'sum'
            }).reset_index()

    # Filter untuk quarter tertentu (per tahun)
    # Filter untuk quarter tertentu (per tahun)
    df_national_filtered = filter_data(
        df_national_grouped_q,
        selected_quarter=selected_quarter_pjp,
        selected_year=selected_start_year,
    )
    df_preprocessed_filtered = filter_data(
        df_preprocessed_grouped_q,
        selected_quarter=selected_quarter_pjp,
        selected_year=selected_start_year,
    )

    # Filter untuk range tahun dan bulan (all time/range)
    # Konversi nama bulan ke angka
    month_to_num = {m: i+1 for i, m in enumerate(months)}
    start_month_num = month_to_num[selected_start_month]
    end_month_num = month_to_num[selected_end_month]

    # Filter manual untuk range tahun dan bulan
    def filter_year_month_range(df, start_year, end_year, start_month, end_month):
        if 'Month' not in df.columns:
            # Jika tidak ada kolom Month, hanya filter tahun saja
            return df[(df['Year'] >= start_year) & (df['Year'] <= end_year)]
        # Mapping nama bulan ke angka
        month_to_num = {m.lower(): i+1 for i, m in enumerate(months)}

        def to_month_num(v):
            # Handle numeric months or month names
            try:
                if pd.isna(v):
                    return None
            except Exception:
                pass
            # numeric (int/float or string digits)
            try:
                if isinstance(v, (int, float)):
                    return int(v)
                s = str(v).strip()
                if s.isdigit():
                    return int(s)
            except Exception:
                pass
            # name
            s = str(v).strip().lower()
            return month_to_num.get(s)

        df = df.copy()
        df['MonthNum'] = df['Month'].apply(to_month_num)
        # Drop rows where MonthNum could not be parsed
        df = df[df['MonthNum'].notna()]
        # Filter kombinasi tahun dan bulan
        df_filtered = df[(df['Year'] > start_year) | ((df['Year'] == start_year) & (df['MonthNum'] >= start_month))]
        df_filtered = df_filtered[(df_filtered['Year'] < end_year) | ((df_filtered['Year'] == end_year) & (df_filtered['MonthNum'] <= end_month))]
        df_filtered = df_filtered.drop(columns=['MonthNum'], errors='ignore')
        return df_filtered

    # Untuk range (month-level) gunakan grouped by month / raw preprocessed
    df_national_filtered_year = filter_year_month_range(df_national_grouped_m, selected_start_year, selected_end_year, start_month_num, end_month_num)
    # Untuk preprocessed, gunakan versi yang sudah di-group per Month
    df_preprocessed_filtered_year = filter_year_month_range(df_preprocessed_grouped_m, selected_start_year, selected_end_year, start_month_num, end_month_num)

    # Tentukan scope data yang dipakai untuk bagian utama Market Share
    if 'selected_mode' in locals() and selected_mode == 'Range':
        df_scope_preprocessed = df_preprocessed_filtered_year
        df_scope_national = df_national_filtered_year
        scope_label = f"{selected_start_month} {selected_start_year} - {selected_end_month} {selected_end_year}"
    else:
        df_scope_preprocessed = df_preprocessed_filtered
        df_scope_national = df_national_filtered
        scope_label = f"Triwulan {selected_quarter_pjp} Tahun {selected_start_year}"

    st.subheader(f"Market Share PJP LR Jakarta {scope_label}")

    # ===== Average ticket size (DKI vs luar DKI) mengikuti filter Year/Quarter =====
    def _fmt_juta_per_trx(value: float) -> str:
        s = f"Rp {value/1_000_000:,.2f} juta/transaksi"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    def _fmt_rp(value: float) -> str:
        s = f"Rp {value:,.0f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    def _fmt_int(value: float) -> str:
        s = f"{int(round(value)):,.0f}"
        return s.replace(",", ".")

    def _sum_cols(df_: pd.DataFrame, cols: list[str]) -> float:
        present = [c for c in cols if c in df_.columns]
        if not present or df_ is None or df_.empty:
            return 0.0
        values = pd.to_numeric(df_[present].sum(axis=1), errors="coerce").fillna(0)
        return float(values.sum())

    def _national_totals(df_nat_filtered: pd.DataFrame) -> tuple[float, float]:
        """Return (nominal_total, frek_total) from national dataframe.

        Some files have 'Nom Nasional Total' empty/0 while Inc/Out/Dom are filled.
        In that case compute total = Inc+Out+Dom.
        """
        nom_total = _sum_cols(df_nat_filtered, ["Nom Nasional Total"])
        frek_total = _sum_cols(df_nat_filtered, ["Frek Nasional Total"])

        if nom_total == 0.0:
            nom_total = _sum_cols(df_nat_filtered, ["Nom Nasional Inc", "Nom Nasional Out", "Nom Nasional Dom"])
        if frek_total == 0.0:
            frek_total = _sum_cols(df_nat_filtered, ["Frek Nasional Inc", "Frek Nasional Out", "Frek Nasional Dom"])

        return nom_total, frek_total

    # Raw_JKTNasional stores nominal in "miliar" (billions of Rupiah)
    _NOMINAL_NATIONAL_SCALE_TO_RP = 1_000_000_000.0

    try:
        # Gunakan scope (Quarter atau Range) untuk menghitung average ticket
        ticket_scope = compute_average_ticket_size(df_scope_preprocessed, df_scope_national)
        avg_dki_q = float(ticket_scope.get("avg_ticket_dki", 0.0) or 0.0)

        total_nom_dki_q = float(ticket_scope.get("total_nominal_dki", 0.0) or 0.0)
        total_freq_dki_q = float(ticket_scope.get("total_freq_dki", 0.0) or 0.0)

        # Luar DKI: gunakan national totals dari scope
        total_nom_out_q, total_freq_out_q = _national_totals(df_scope_national)
        total_nom_out_q = total_nom_out_q * _NOMINAL_NATIONAL_SCALE_TO_RP
        avg_outside_q = (total_nom_out_q / total_freq_out_q) if total_freq_out_q else 0.0

        st.markdown("#### Rata-rata nominal per transaksi (Average Ticket)")
        colA, colB = st.columns(2)
        with colA:
            st.metric("Average ticket size DKI Jakarta", _fmt_juta_per_trx(avg_dki_q))
            st.caption(f"Total nominal DKI: {_fmt_rp(total_nom_dki_q)} | Total frekuensi DKI: {_fmt_int(total_freq_dki_q)}")
        with colB:
            st.metric("Average ticket size Luar DKI Jakarta", _fmt_juta_per_trx(avg_outside_q))
            st.caption(f"Total nominal luar DKI: {_fmt_rp(total_nom_out_q)} | Total frekuensi luar DKI: {_fmt_int(total_freq_out_q)}")

        if avg_dki_q > 0 and avg_outside_q > 0:
            st.info(
                f"Nominal transaksi PJP LR di wilayah kerja DKI Jakarta cenderung bernilai tinggi, meskipun jumlah "
                f"frekuensinya tidak sebanyak wilayah lain (average ticket size transaksi PJP LR di wilayah kerja DKI "
                f"Jakarta adalah {_fmt_juta_per_trx(avg_dki_q)}). Hal ini berbanding terbalik dengan transaksi PJP LR "
                f"di luar wilayah DKI Jakarta, di mana transaksi memiliki frekuensi tinggi, namun secara nominal bernilai "
                f"rendah yaitu {_fmt_juta_per_trx(avg_outside_q)}."
            )
    except Exception as _ticket_err:
        st.warning(f"Gagal menghitung average ticket size: {_ticket_err}")

    # Compile market share berdasarkan scope yang dipilih (Quarter atau Range)
    df_out = compile_data_market_share(df_scope_preprocessed, df_scope_national, "Out")
    df_inc = compile_data_market_share(df_scope_preprocessed, df_scope_national, "Inc")
    df_dom = compile_data_market_share(df_scope_preprocessed, df_scope_national, "Dom")
    df_total = compile_data_market_share(df_scope_preprocessed, df_scope_national, "Total", df_inc, df_out, df_dom)

    df_out_year = compile_data_market_share(df_preprocessed_filtered_year, df_national_filtered_year, "Out")
    df_inc_year = compile_data_market_share(df_preprocessed_filtered_year, df_national_filtered_year, "Inc")
    df_dom_year = compile_data_market_share(df_preprocessed_filtered_year, df_national_filtered_year, "Dom")
    df_total_year = compile_data_market_share(df_preprocessed_filtered_year, df_national_filtered_year, "Total",
                                              df_inc_year, df_out_year, df_dom_year)
    st.markdown("#### Market Share Outgoing")
    df_out_display = df_out.copy()
    df_out_display = format_profile_df(df_out_display, is_market_share=True)
    st.dataframe(df_out_display, hide_index=True, use_container_width=True)
    st.info("*Market Share merupakan Persentase Market Share Transaksi Jakarta terhadap Transaksi Nasional")
    col1, col2 = st.columns(2)
    with col1:
        make_pie_chart_market_share(df_out, "Outgoing", is_nom=True, key="Out_True_NotAllTime")
    with col2:
        make_pie_chart_market_share(df_out, "Outgoing", is_nom=False, key="Out_False_NotAllTime")
    st.divider()
    st.markdown("#### Market Share Incoming")
    df_inc_display = df_inc.copy()
    df_inc_display = format_profile_df(df_inc_display, is_market_share=True)
    st.dataframe(df_inc_display, hide_index=True, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        make_pie_chart_market_share(df_inc, "Incoming", is_nom=True, key="Inc_True_NotAllTime")
    with col2:
        make_pie_chart_market_share(df_inc, "Incoming", is_nom=False, key="Inc_False_NotAllTime")
    st.divider()
    st.markdown("#### Market Share Domestik")
    df_dom_display = df_dom.copy()
    df_dom_display = format_profile_df(df_dom_display, is_market_share=True)
    st.dataframe(df_dom_display, hide_index=True, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        make_pie_chart_market_share(df_dom, "Domestik", is_nom=True, key="Dom_True_NotAllTime")
    with col2:
        make_pie_chart_market_share(df_dom, "Domestik", is_nom=False, key="Dom_False_NotAllTime")
    st.divider()
    st.markdown("#### Market Share Total (Outgoing & Incoming & Domestik)")
    df_total_display = df_total.copy()
    df_total_display = format_profile_df(df_total_display, is_market_share=True)
    st.dataframe(df_total_display, hide_index=True, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        make_pie_chart_market_share(df_total, "Total", is_nom=True, key="Total_True_NotAllTime")
    with col2:
        make_pie_chart_market_share(df_total, "Total", is_nom=False, key="Total_False_NotAllTime")

    st.subheader(f"Market Share PJP Jakarta LR All-Time ({selected_start_year} {selected_start_month} - {selected_end_year} {selected_end_month})")

    # Average ticket size untuk periode All-Time (mengikuti filter Year start)
    try:
        ticket_y = compute_average_ticket_size(df_preprocessed_filtered_year, df_national_filtered_year)
        avg_dki_y = float(ticket_y.get("avg_ticket_dki", 0.0) or 0.0)

        total_nom_dki_y = float(ticket_y.get("total_nominal_dki", 0.0) or 0.0)
        total_freq_dki_y = float(ticket_y.get("total_freq_dki", 0.0) or 0.0)

        total_nom_out_y, total_freq_out_y = _national_totals(df_national_filtered_year)
        total_nom_out_y = total_nom_out_y * _NOMINAL_NATIONAL_SCALE_TO_RP
        avg_outside_y = (total_nom_out_y / total_freq_out_y) if total_freq_out_y else 0.0

        st.caption(
            f"All-Time average ticket size: DKI {_fmt_juta_per_trx(avg_dki_y)} (Nom {_fmt_rp(total_nom_dki_y)}, Frek {_fmt_int(total_freq_dki_y)}) "
            f"| Luar DKI {_fmt_juta_per_trx(avg_outside_y)} (Nom {_fmt_rp(total_nom_out_y)}, Frek {_fmt_int(total_freq_out_y)})"
        )
    except Exception:
        pass
    st.markdown("#### Market Share Outgoing All-Time")
    df_out_year_display = df_out_year.copy()
    df_out_year_display = format_profile_df(df_out_year_display, is_market_share=True)
    st.dataframe(df_out_year_display, hide_index=True, use_container_width=True)
    st.info("*Market Share merupakan Persentase Market Share Transaksi Jakarta terhadap Transaksi Nasional.")
    st.warning("Pada bagian ini, hanya Filter Profile (Year) yang berpengaruh terhadap data yang ditampilkan.")
    col1, col2 = st.columns(2)
    with col1:
        make_pie_chart_market_share(df_out_year, "Outgoing", is_nom=True, key="Out_True_AllTime")
    with col2:
        make_pie_chart_market_share(df_out_year, "Outgoing", is_nom=False, key="Out_False_AllTime")
    st.divider()
    st.markdown("#### Market Share Incoming All-Time")
    df_inc_year_display = df_inc_year.copy()
    df_inc_year_display = format_profile_df(df_inc_year_display, is_market_share=True)
    st.dataframe(df_inc_year, hide_index=True, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        make_pie_chart_market_share(df_inc_year, "Incoming", is_nom=True, key="Inc_True_AllTime")
    with col2:
        make_pie_chart_market_share(df_inc_year, "Incoming", is_nom=False, key="Inc_False_AllTime")
    st.divider()
    st.markdown("#### Market Share Domestik All-Time")
    df_dom_year_display = df_dom_year.copy()
    df_dom_year_display = format_profile_df(df_dom_year_display, is_market_share=True)
    st.dataframe(df_dom_year_display, hide_index=True, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        make_pie_chart_market_share(df_dom_year, "Domestik", is_nom=True, key="Dom_True_AllTime")
    with col2:
        make_pie_chart_market_share(df_dom_year, "Domestik", is_nom=False, key="Dom_False_AllTime")
    st.divider()
    st.markdown("#### Market Share Total (Outgoing & Incoming & Domestik) All-Time")
    df_total_year_display = df_total_year.copy()
    df_total_year_display = format_profile_df(df_total_year_display, is_market_share=True)
    st.dataframe(df_total_year_display, hide_index=True, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        make_pie_chart_market_share(df_total_year, "Total", is_nom=True, key="Total_True_AllTime")
    with col2:
        make_pie_chart_market_share(df_total_year, "Total", is_nom=False, key="Total_False_AllTime")
else:
    st.warning("Please Upload the Main Excel File first in the Summary Section.")
