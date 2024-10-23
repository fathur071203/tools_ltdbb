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

            selected_year_pjp = st.selectbox('Select Year:', sliced_years, key="key_year_pjp")
            selected_quarter_pjp = st.selectbox('Select Quarter:', quarters, key="key_quarter_pjp")

    df_national = add_quarter_column(df_national)
    df_national_grouped = preprocess_data_national(df_national, True, True)
    df_preprocessed = preprocess_data(df, True)

    df_preprocessed_grouped = df_preprocessed.groupby(['Year', 'Quarter'], observed=False).agg({
        'Sum of Fin Jumlah Inc': 'sum',
        'Sum of Fin Jumlah Out': 'sum',
        'Sum of Fin Jumlah Dom': 'sum',
        'Sum of Fin Nilai Inc': 'sum',
        'Sum of Fin Nilai Out': 'sum',
        'Sum of Fin Nilai Dom': 'sum',
        'Sum of Total Nom': 'sum'
    }).reset_index()

    df_national_filtered = filter_data(df_national_grouped, selected_quarter=selected_quarter_pjp,
                                       selected_year=selected_year_pjp)
    df_preprocessed_filtered = filter_data(df_preprocessed_grouped, selected_quarter=selected_quarter_pjp,
                                           selected_year=selected_year_pjp)

    st.subheader(f"Market Share PJP Jakarta Triwulan {selected_quarter_pjp} Tahun {selected_year_pjp}")

    st.dataframe(df_national_filtered, hide_index=True, use_container_width=True)
    st.dataframe(df_preprocessed_filtered, hide_index=True, use_container_width=True)

    df_out = compile_data_market_share(df_preprocessed_filtered, df_national_filtered, "Out")
    df_inc = compile_data_market_share(df_preprocessed_filtered, df_national_filtered, "Inc")
    df_dom = compile_data_market_share(df_preprocessed_filtered, df_national_filtered, "Dom")

    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(df_out, hide_index=True, use_container_width=True)
        st.dataframe(df_inc, hide_index=True, use_container_width=True)
    with col2:
        st.dataframe(df_dom, hide_index=True, use_container_width=True)
    st.info("*Market Share merupakan Market Share Transaksi Jakarta terhadap Transaksi Nasional")
