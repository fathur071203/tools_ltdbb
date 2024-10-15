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

    df_preprocessed_time = preprocess_data(df, True)

    df_sum_time = sum_data_time(df_preprocessed_time, False)
    df_sum_time_month = sum_data_time(df_preprocessed_time, True)

    df_tuple = preprocess_data_growth(df_sum_time, False)
    df_tuple_month = preprocess_data_growth(df_sum_time_month, True)

    df_jumlah_inc, df_jumlah_out, df_jumlah_dom, df_nom_inc, df_nom_out, df_nom_dom = df_tuple

    (df_nom_inc_month, df_nom_out_month, df_nom_dom_month,
     df_jumlah_inc_month, df_jumlah_out_month, df_jumlah_dom_month) = df_tuple_month

    # TODO: Filter DF Month
    df_jumlah_inc_filtered = filter_start_end_year(df_jumlah_inc, selected_start_year, selected_end_year)
    df_jumlah_out_filtered = filter_start_end_year(df_jumlah_out, selected_start_year, selected_end_year)
    df_jumlah_dom_filtered = filter_start_end_year(df_jumlah_dom, selected_start_year, selected_end_year)

    df_nom_inc_filtered = filter_start_end_year(df_nom_inc, selected_start_year, selected_end_year)
    df_nom_out_filtered = filter_start_end_year(df_nom_out, selected_start_year, selected_end_year)
    df_nom_dom_filtered = filter_start_end_year(df_nom_dom, selected_start_year, selected_end_year)

    df_jumlah_inc_month_filtered = filter_start_end_year(df_jumlah_inc_month, selected_start_year, selected_end_year)
    df_jumlah_out_month_filtered = filter_start_end_year(df_jumlah_out_month, selected_start_year, selected_end_year)
    df_jumlah_dom_month_filtered = filter_start_end_year(df_jumlah_dom_month, selected_start_year, selected_end_year)

    df_nom_inc_month_filtered = filter_start_end_year(df_nom_inc_month, selected_start_year, selected_end_year)
    df_nom_out_month_filtered = filter_start_end_year(df_nom_out_month, selected_start_year, selected_end_year)
    df_nom_dom_month_filtered = filter_start_end_year(df_nom_dom_month, selected_start_year, selected_end_year)

    df_inc_combined = merge_df_growth(df_jumlah_inc_filtered, df_nom_inc_filtered)
    df_out_combined = merge_df_growth(df_jumlah_out_filtered, df_nom_out_filtered)
    df_dom_combined = merge_df_growth(df_jumlah_dom_filtered, df_nom_dom_filtered)

    st.write("Growth in Transactions")
    st.dataframe(df_inc_combined)

    make_combined_bar_line_chart(df_jumlah_inc_filtered, "Jumlah", "Inc")
    make_combined_bar_line_chart(df_nom_inc_filtered, "Nilai", "Inc")

    st.dataframe(df_out_combined)

    make_combined_bar_line_chart(df_jumlah_out_filtered, "Jumlah", "Out")
    make_combined_bar_line_chart(df_nom_out_filtered, "Nilai", "Out")

    st.dataframe(df_dom_combined)

    make_combined_bar_line_chart(df_jumlah_dom_filtered, "Jumlah", "Dom")
    make_combined_bar_line_chart(df_nom_dom_filtered, "Nilai", "Dom")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.dataframe(df_jumlah_inc_month_filtered)
        st.dataframe(df_nom_inc_month_filtered)
    with col2:
        st.dataframe(df_jumlah_out_month_filtered)
        st.dataframe(df_nom_out_month_filtered)
    with col3:
        st.dataframe(df_jumlah_dom_month_filtered)
        st.dataframe(df_nom_dom_month_filtered)