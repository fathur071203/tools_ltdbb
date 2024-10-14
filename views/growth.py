import pandas as pd
import streamlit as st

from service.preprocess import *
from service.visualize import *

# Initial Page Setup
set_page_visuals()

if st.session_state['df'] is not None:
    df = st.session_state['df']
    with st.sidebar:
        unique_years = df['Year'].unique().tolist()

        selected_start_year = st.sidebar.selectbox('Select Start Year:', unique_years)
        selected_end_year = st.sidebar.selectbox('Select End Year:', unique_years, index=len(unique_years) - 1)

        jenis_transaksi = ['All', 'Incoming', 'Outgoing', 'Domestik']
        selected_jenis_transaksi = st.sidebar.selectbox('Select Jenis Transaksi:', jenis_transaksi)

    df_preprocessed_time = preprocess_data(df, True)
    df_sum_time = sum_data_time(df_preprocessed_time, False)
    df_tuple = preprocess_data_growth(df_sum_time)
    df_jumlah_inc, df_jumlah_out, df_jumlah_dom, df_nom_inc, df_nom_out, df_nom_dom = df_tuple

    df_jumlah_inc_filtered = filter_start_end_year(df_jumlah_inc, selected_start_year, selected_end_year)
    df_nom_inc_filtered = filter_start_end_year(df_nom_inc, selected_start_year, selected_end_year)

    df_inc_combined = merge_df_growth(df_jumlah_inc_filtered, df_nom_inc_filtered)

    st.write("Growth in Incoming Transactions")
    st.dataframe(df_inc_combined)

    make_combined_bar_line_chart(df_jumlah_inc_filtered, "Jumlah")
    make_combined_bar_line_chart(df_nom_inc_filtered, "Nominal")
