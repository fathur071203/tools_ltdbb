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

    with (st.spinner('Loading and filtering data...')):
        df_preprocessed_time = preprocess_data(df, True)

        df_sum_time = sum_data_time(df_preprocessed_time, False)
        df_sum_time_month = sum_data_time(df_preprocessed_time, True)

        df_tuple = preprocess_data_growth(df_sum_time, False)
        df_tuple_month = preprocess_data_growth(df_sum_time_month, True)

        df_jumlah_inc, df_jumlah_out, df_jumlah_dom, df_nom_inc, df_nom_out, df_nom_dom = df_tuple

        (df_jumlah_inc_month, df_jumlah_out_month, df_jumlah_dom_month,
         df_nom_inc_month, df_nom_out_month, df_nom_dom_month) = df_tuple_month

        df_jumlah_inc_filtered = filter_start_end_year(df_jumlah_inc, selected_start_year, selected_end_year)
        df_jumlah_out_filtered = filter_start_end_year(df_jumlah_out, selected_start_year, selected_end_year)
        df_jumlah_dom_filtered = filter_start_end_year(df_jumlah_dom, selected_start_year, selected_end_year)

        df_nom_inc_filtered = filter_start_end_year(df_nom_inc, selected_start_year, selected_end_year)
        df_nom_out_filtered = filter_start_end_year(df_nom_out, selected_start_year, selected_end_year)
        df_nom_dom_filtered = filter_start_end_year(df_nom_dom, selected_start_year, selected_end_year)

        df_jumlah_inc_month_filtered = filter_start_end_year(df_jumlah_inc_month, selected_start_year,
                                                             selected_end_year)
        df_jumlah_out_month_filtered = filter_start_end_year(df_jumlah_out_month, selected_start_year,
                                                             selected_end_year)
        df_jumlah_dom_month_filtered = filter_start_end_year(df_jumlah_dom_month, selected_start_year,
                                                             selected_end_year)

        df_nom_inc_month_filtered = filter_start_end_year(df_nom_inc_month, selected_start_year, selected_end_year)
        df_nom_out_month_filtered = filter_start_end_year(df_nom_out_month, selected_start_year, selected_end_year)
        df_nom_dom_month_filtered = filter_start_end_year(df_nom_dom_month, selected_start_year, selected_end_year)

        df_inc_combined = merge_df_growth(df_jumlah_inc_filtered, df_nom_inc_filtered)
        df_out_combined = merge_df_growth(df_jumlah_out_filtered, df_nom_out_filtered)
        df_dom_combined = merge_df_growth(df_jumlah_dom_filtered, df_nom_dom_filtered)

        df_inc_combined_month = merge_df_growth(df_jumlah_inc_month_filtered, df_nom_inc_month_filtered, True)
        df_out_combined_month = merge_df_growth(df_jumlah_out_month_filtered, df_nom_out_month_filtered, True)
        df_dom_combined_month = merge_df_growth(df_jumlah_dom_month_filtered, df_nom_dom_month_filtered, True)

        # TODO: Refactor code
        df_jumlah_total = pd.concat([df_jumlah_inc_filtered, df_jumlah_out_filtered, df_jumlah_dom_filtered])
        df_nom_total = pd.concat([df_nom_inc_filtered, df_nom_out_filtered, df_nom_dom_filtered])

        df_jumlah_total = df_jumlah_total.groupby(['Year', 'Quarter']).sum().reset_index()
        df_nom_total = df_nom_total.groupby(['Year', 'Quarter']).sum().reset_index()

        df_total = pd.merge(df_jumlah_total, df_nom_total, on=['Year', 'Quarter'])

        df_total['Sum of Fin Jumlah Total'] = df_total['Sum of Fin Jumlah Inc'] + df_total['Sum of Fin Jumlah Out'] + \
                                              df_total['Sum of Fin Jumlah Dom']
        df_total['Sum of Fin Nilai Total'] = df_total['Sum of Fin Nilai Inc'] + df_total['Sum of Fin Nilai Out'] + \
                                             df_total['Sum of Fin Nilai Dom']
        df_total.drop(['%YoY_x', '%QtQ_x', '%YoY_y', '%QtQ_y', 'Sum of Fin Jumlah Inc',
                       'Sum of Fin Jumlah Out', 'Sum of Fin Jumlah Dom', 'Sum of Fin Nilai Inc',
                       'Sum of Fin Nilai Out', 'Sum of Fin Nilai Dom'], axis=1, inplace=True)

        first_year = df_total['Year'].min()

        df_total_jumlah = calculate_growth(df_total, first_year, "Jumlah", "Total")
        df_total_nilai = calculate_growth(df_total, first_year, "Nilai", "Total")

        df_total_combined = (
            pd.merge(df_total_jumlah, df_total_nilai, on=['Year', 'Quarter'])
            .drop(['Sum of Fin Jumlah Total_y', 'Sum of Fin Nilai Total_y'], axis=1)
            .rename(columns={'Sum of Fin Jumlah Total_x': 'Sum of Fin Jumlah Total',
                             'Sum of Fin Nilai Total_x': 'Sum of Fin Nilai Total',
                             '%YoY_x': '%YoY Jumlah', '%YoY_y': 'YoY Nilai',
                             '%QtQ_x': '%QtQ Jumlah', '%QtQ_y': '%QtQ Nilai',})
        )

    st.header("Growth in Transactions")
    if selected_jenis_transaksi == 'Incoming' or selected_jenis_transaksi == 'All':
        st.subheader("Incoming Transactions")
        st.dataframe(df_inc_combined)
        make_combined_bar_line_chart(df_jumlah_inc_filtered, "Jumlah", "Inc")
        make_combined_bar_line_chart(df_nom_inc_filtered, "Nilai", "Inc")

    if selected_jenis_transaksi == 'Outgoing' or selected_jenis_transaksi == 'All':
        st.subheader("Outgoing Transactions")
        st.dataframe(df_out_combined)
        make_combined_bar_line_chart(df_jumlah_out_filtered, "Jumlah", "Out")
        make_combined_bar_line_chart(df_nom_out_filtered, "Nilai", "Out")

    if selected_jenis_transaksi == 'Domestik' or selected_jenis_transaksi == 'All':
        st.subheader("Domestik Transactions")
        st.dataframe(df_dom_combined)
        make_combined_bar_line_chart(df_jumlah_dom_filtered, "Jumlah", "Dom")
        make_combined_bar_line_chart(df_nom_dom_filtered, "Nilai", "Dom")

    st.header("Monthly Transaction Data Overview")
    col1, col2, col3 = st.columns(3)
    if selected_jenis_transaksi == 'Incoming' or selected_jenis_transaksi == 'All':
        with col1:
            st.subheader("Incoming (Monthly)")
            st.dataframe(df_inc_combined_month)
    if selected_jenis_transaksi == 'Outgoing' or selected_jenis_transaksi == 'All':
        with col2:
            st.subheader("Outgoing (Monthly)")
            st.dataframe(df_out_combined_month)
    if selected_jenis_transaksi == 'Domestik' or selected_jenis_transaksi == 'All':
        with col3:
            st.subheader("Domestik (Monthly)")
            st.dataframe(df_dom_combined_month)
    make_combined_bar_line_chart(df_jumlah_inc_month_filtered, "Jumlah", "Inc", True)
    make_combined_bar_line_chart(df_nom_inc_month_filtered, "Nilai", "Inc", True)

    make_combined_bar_line_chart(df_jumlah_out_month_filtered, "Jumlah", "Out", True)
    make_combined_bar_line_chart(df_nom_out_month_filtered, "Nilai", "Out", True)

    make_combined_bar_line_chart(df_jumlah_dom_month_filtered, "Jumlah", "Dom", True)
    make_combined_bar_line_chart(df_nom_dom_month_filtered, "Nilai", "Dom", True)

    st.dataframe(df_total_combined)
