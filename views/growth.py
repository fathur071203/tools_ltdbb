import pandas as pd
import streamlit as st

from service.preprocess import *
from service.visualize import *

# Initial Page Setup
set_page_visuals()

if st.session_state['df'] is not None:
    df = st.session_state['df']
    with st.sidebar:
        with st.expander("Filter Growth", True):
            unique_years = df['Year'].unique().tolist()
            selected_start_year = st.selectbox('Select Start Year:', unique_years)
            selected_end_year = st.selectbox('Select End Year:', unique_years, index=len(unique_years) - 1)

            jenis_transaksi = ['All', 'Incoming', 'Outgoing', 'Domestik']
            selected_jenis_transaksi = st.selectbox('Select Jenis Transaksi:', jenis_transaksi)
        st.info("Use the filters to adjust the year range and transaction type.")

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

        df_total_combined = filter_start_end_year(df_total_combined, selected_start_year, selected_end_year)
        df_total_month_combined = filter_start_end_year(df_total_month_combined, selected_start_year, selected_end_year,
                                                        True)

        df_jumlah_inc_filtered = filter_start_end_year(df_jumlah_inc, selected_start_year, selected_end_year)
        df_jumlah_out_filtered = filter_start_end_year(df_jumlah_out, selected_start_year, selected_end_year)
        df_jumlah_dom_filtered = filter_start_end_year(df_jumlah_dom, selected_start_year, selected_end_year)

        df_nom_inc_filtered = filter_start_end_year(df_nom_inc, selected_start_year, selected_end_year)
        df_nom_out_filtered = filter_start_end_year(df_nom_out, selected_start_year, selected_end_year)
        df_nom_dom_filtered = filter_start_end_year(df_nom_dom, selected_start_year, selected_end_year)

        df_jumlah_inc_month_filtered = filter_start_end_year(df_jumlah_inc_month, selected_start_year,
                                                             selected_end_year, True)
        df_jumlah_out_month_filtered = filter_start_end_year(df_jumlah_out_month, selected_start_year,
                                                             selected_end_year, True)
        df_jumlah_dom_month_filtered = filter_start_end_year(df_jumlah_dom_month, selected_start_year,
                                                             selected_end_year, True)

        df_nom_inc_month_filtered = filter_start_end_year(df_nom_inc_month, selected_start_year, selected_end_year,
                                                          True)
        df_nom_out_month_filtered = filter_start_end_year(df_nom_out_month, selected_start_year, selected_end_year,
                                                          True)
        df_nom_dom_month_filtered = filter_start_end_year(df_nom_dom_month, selected_start_year, selected_end_year,
                                                          True)

        df_inc_combined = merge_df_growth(df_jumlah_inc_filtered, df_nom_inc_filtered)
        df_out_combined = merge_df_growth(df_jumlah_out_filtered, df_nom_out_filtered)
        df_dom_combined = merge_df_growth(df_jumlah_dom_filtered, df_nom_dom_filtered)

        df_inc_combined_month = merge_df_growth(df_jumlah_inc_month_filtered, df_nom_inc_month_filtered, True)
        df_out_combined_month = merge_df_growth(df_jumlah_out_month_filtered, df_nom_out_month_filtered, True)
        df_dom_combined_month = merge_df_growth(df_jumlah_dom_month_filtered, df_nom_dom_month_filtered, True)

        st.header("Growth in Transactions")
        if selected_jenis_transaksi == 'Incoming' or selected_jenis_transaksi == 'All':
            st.markdown("### 📥 Incoming Transactions")
            st.dataframe(df_inc_combined, use_container_width=True, hide_index=True)
            make_combined_bar_line_chart(df_jumlah_inc_filtered, "Jumlah", "Inc")
            make_combined_bar_line_chart(df_nom_inc_filtered, "Nilai", "Inc")

        if selected_jenis_transaksi == 'Outgoing' or selected_jenis_transaksi == 'All':
            st.markdown("### 📤 Outgoing Transactions")
            st.dataframe(df_out_combined, use_container_width=True, hide_index=True)
            make_combined_bar_line_chart(df_jumlah_out_filtered, "Jumlah", "Out")
            make_combined_bar_line_chart(df_nom_out_filtered, "Nilai", "Out")

        if selected_jenis_transaksi == 'Domestik' or selected_jenis_transaksi == 'All':
            st.markdown("### 🇮🇩 Domestik Transactions")
            st.dataframe(df_dom_combined, use_container_width=True, hide_index=True)
            make_combined_bar_line_chart(df_jumlah_dom_filtered, "Jumlah", "Dom")
            make_combined_bar_line_chart(df_nom_dom_filtered, "Nilai", "Dom")

        st.subheader("📅 Monthly Transaction Data Overview")
        col1, col2, col3 = st.columns(3)
        if selected_jenis_transaksi == 'Incoming' or selected_jenis_transaksi == 'All':
            with col1:
                st.markdown("### 📥 Incoming (Monthly)")
                st.dataframe(df_inc_combined_month, use_container_width=True, hide_index=True)
        if selected_jenis_transaksi == 'Outgoing' or selected_jenis_transaksi == 'All':
            with col2:
                st.markdown("### 📤 Outgoing (Monthly)")
                st.dataframe(df_out_combined_month, use_container_width=True, hide_index=True)
        if selected_jenis_transaksi == 'Domestik' or selected_jenis_transaksi == 'All':
            with col3:
                st.markdown("### 🇮🇩 Domestik (Monthly)")
                st.dataframe(df_dom_combined_month, use_container_width=True, hide_index=True)

        make_combined_bar_line_chart(df_jumlah_inc_month_filtered, "Jumlah", "Inc", True)
        make_combined_bar_line_chart(df_nom_inc_month_filtered, "Nilai", "Inc", True)

        make_combined_bar_line_chart(df_jumlah_out_month_filtered, "Jumlah", "Out", True)
        make_combined_bar_line_chart(df_nom_out_month_filtered, "Nilai", "Out", True)

        make_combined_bar_line_chart(df_jumlah_dom_month_filtered, "Jumlah", "Dom", True)
        make_combined_bar_line_chart(df_nom_dom_month_filtered, "Nilai", "Dom", True)

        st.subheader("🔍 Overall Summary")
        st.write("Here is a combined view of the total transaction counts and values across all types.")
        st.dataframe(df_total_combined, use_container_width=True, hide_index=True)

        st.markdown("### 📊 Total Transactions Overview")
        make_combined_bar_line_chart(df_total_combined, "Jumlah", "Total", False, True)
        make_combined_bar_line_chart(df_total_combined, "Nilai", "Total", False, True)

        st.subheader("🔍 Overall Summary (Monthly)")
        st.write("Here is a combined view of the total transaction counts and values across all types.")
        st.dataframe(df_total_month_combined, use_container_width=True, hide_index=True)

        st.markdown("### 📊 Total Transactions Overview (Monthly)")
        make_combined_bar_line_chart(df_total_month_combined, "Jumlah", "Total", True, True)
        make_combined_bar_line_chart(df_total_month_combined, "Nilai", "Total", True, True)
else:
    st.warning("Please Upload the Main Excel File first in the Summary Section.")