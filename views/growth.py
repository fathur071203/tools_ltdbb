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

        start_year = unique_years
        end_year = unique_years

        selected_start_year = st.sidebar.selectbox('Select Start Year:', start_year)
        selected_end_year = st.sidebar.selectbox('Select End Year:', end_year, index=len(unique_years) - 1)

        jenis_transaksi = ['All', 'Incoming', 'Outgoing', 'Domestik']
        selected_jenis_transaksi = st.sidebar.selectbox('Select Jenis Transaksi:', jenis_transaksi)

    df_preprocessed_time = preprocess_data(df, True)
    filtered_df_time = filter_data(df=df_preprocessed_time,
                                        selected_year='All',
                                        selected_quarter='All')
    df_sum_time = sum_data_time(filtered_df_time, False)
    df_tuple = preprocess_data_growth(df_sum_time)
    df_jumlah_inc, df_jumlah_out, df_jumlah_dom, df_nom_inc, df_nom_out, df_nom_dom = df_tuple

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("Jumlah Incoming Transactions")
        st.dataframe(df_jumlah_inc)
        st.write("Nominal of Incoming Transactions")
        st.dataframe(df_nom_inc)
    
    with col2:
        st.write("Jumlah Outgoing Transactions")
        st.dataframe(df_jumlah_out)
        st.write("Nominal of Outgoing Transactions")
        st.dataframe(df_nom_out)
    
    with col3:
        st.write("Jumlah Domestic Transactions")
        st.dataframe(df_jumlah_dom)
        st.write("Nominal of Domestic Transactions")
        st.dataframe(df_nom_dom)
