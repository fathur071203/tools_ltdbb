from sys import prefix

import pandas as pd
import streamlit as st
import calendar

from service.preprocess import *
from service.visualize import *

# Initial Page Setup
set_page_visuals()

if st.session_state['df_national'] is not None and st.session_state['df'] is not None:
    df_national = st.session_state['df_national']
    df = st.session_state['df']

    with st.sidebar:
        with st.expander("Filter Profile", True):
            pjp_list = ['All'] + df['Nama PJP'].unique().tolist()
            years = ['All'] + list(df['Year'].unique())

            selected_pjp = st.selectbox('Select PJP:', pjp_list)
            selected_year_pjp = st.selectbox('Select Year:', years, key="key_year_pjp")
        st.info("Use the filters to adjust the PJP name and transaction year.")

    df_national_preprocessed_year = preprocess_data_profile(df_national, True)
    df_national_preprocessed_month = preprocess_data_profile(df_national, False)
    df_preprocessed = preprocess_data(df, True)

    df_preprocessed_grouped_year = df_preprocessed.groupby(['Nama PJP', 'Year']).agg({
        'Sum of Fin Jumlah Inc': 'sum',
        'Sum of Fin Jumlah Out': 'sum',
        'Sum of Fin Jumlah Dom': 'sum',
        'Sum of Fin Nilai Inc': 'sum',
        'Sum of Fin Nilai Out': 'sum',
        'Sum of Fin Nilai Dom': 'sum',
        'Sum of Total Nom': 'sum'
    }).reset_index()
    df_preprocessed_grouped_month = df_preprocessed.groupby(['Nama PJP', 'Year', 'Month'], observed=False).agg({
        'Sum of Fin Jumlah Inc': 'sum',
        'Sum of Fin Jumlah Out': 'sum',
        'Sum of Fin Jumlah Dom': 'sum',
        'Sum of Fin Nilai Inc': 'sum',
        'Sum of Fin Nilai Out': 'sum',
        'Sum of Fin Nilai Dom': 'sum',
        'Sum of Total Nom': 'sum'
    }).reset_index()

    if selected_pjp == 'All' or selected_year_pjp == 'All':
        st.warning("Please Select PJP and Year to show the PJP's Profile")
    else:
        df_grouped_filtered_year = filter_data(df_preprocessed_grouped_year, selected_pjp, selected_year_pjp)
        df_grouped_national_filtered_year = filter_data(df_national_preprocessed_year, selected_year=selected_year_pjp)

        data_jumlah_inc = compile_data_profile(df_grouped_filtered_year, df_grouped_national_filtered_year, "Jumlah", "Inc")
        data_jumlah_out = compile_data_profile(df_grouped_filtered_year, df_grouped_national_filtered_year, "Jumlah", "Out")
        data_jumlah_dom = compile_data_profile(df_grouped_filtered_year, df_grouped_national_filtered_year, "Jumlah", "Dom")

        data_nilai_inc = compile_data_profile(df_grouped_filtered_year, df_grouped_national_filtered_year, "Nilai", "Inc")
        data_nilai_out = compile_data_profile(df_grouped_filtered_year, df_grouped_national_filtered_year, "Nilai", "Out")
        data_nilai_dom = compile_data_profile(df_grouped_filtered_year, df_grouped_national_filtered_year, "Nilai", "Dom")

        merged_data = pd.merge(data_jumlah_inc, data_jumlah_out, on=['Transaction Type'])
        merged_data = pd.merge(merged_data, data_jumlah_dom, on=['Transaction Type'])
        merged_data = pd.merge(merged_data, data_nilai_inc, on=['Transaction Type'])
        merged_data = pd.merge(merged_data, data_nilai_out, on=['Transaction Type'])
        merged_data = pd.merge(merged_data, data_nilai_dom, on=['Transaction Type'])

        st.dataframe(merged_data, use_container_width=True, hide_index=True)

