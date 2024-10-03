import pandas as pd
import streamlit as st
import calendar

from service.preprocess import *
from service.visualize import *

# Initial Page Setup
set_page_visuals()

if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None

uploaded_file = st.file_uploader("Choose an Excel file")

if uploaded_file is not None:
    st.session_state['uploaded_file'] = uploaded_file

df = None

if st.session_state['uploaded_file'] is not None:
    df = load_data(st.session_state['uploaded_file'])

    time_option = st.sidebar.selectbox("Choose Time Period", ("Month", "Quarter"))

    years = ['All'] + list(df['Year'].unique())
    selected_year = st.sidebar.selectbox('Select Year:', years)
    
    df_preprocessed = preprocess_data(df)
    df_preprocessed_time = preprocess_data_time(df)

    if time_option == "Month":
        months = ['All'] + [calendar.month_name[m] for m in df['Month'].unique()]
        selected_month = st.sidebar.selectbox('Select Month:', months)
        filtered_df_time = filter_data_month(df=df_preprocessed_time,
                                        selected_year=selected_year,
                                        selected_month=selected_month)
        isMonth = True
    else:
        quarters = ['All'] + list(df['Quarter'].unique())
        selected_quarter = st.sidebar.selectbox('Select Quarter:', quarters)
        filtered_df_time = filter_data_quarter(df=df_preprocessed_time,
                                        selected_year=selected_year,
                                        selected_quarter=selected_quarter)
        isMonth = False
    df_sum_time = sum_data_time(filtered_df_time, isMonth)

    df_sum_time = df_sum_time[(df_sum_time['Sum of Fin Jumlah Inc'] != 0) & (df_sum_time['Sum of Fin Nilai Inc'] != 0) & 
            (df_sum_time['Sum of Fin Jumlah Out'] != 0) & (df_sum_time['Sum of Fin Nilai Out'] != 0) &
            (df_sum_time['Sum of Fin Jumlah Dom'] != 0) & (df_sum_time['Sum of Fin Nilai Dom'] != 0)]
    
    grand_total = int(df_sum_time['Sum of Total Nom'].sum())

    col1 = st.columns(1)
    with col1[0]:
        make_pie_chart(df_preprocessed, 5)

    col2, col3 = st.columns(2)
    with col2:
        make_grouped_bar_chart(df_sum_time, "Jumlah", isMonth)
    with col3:
        make_grouped_bar_chart(df_sum_time, "Nilai", isMonth)
    st.dataframe(df_sum_time)
    st.write(f"**Grand Total: {format_to_rupiah(grand_total)}**")
else:
    st.warning("You Must Upload a CSV or Excel File")