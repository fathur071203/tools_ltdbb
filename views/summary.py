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

    years = ['All'] + list(df['Year'].unique())
    selected_year = st.sidebar.selectbox('Select Year:', years)
    quarters = ['All'] + list(df['Quarter'].unique())
    selected_quarter = st.sidebar.selectbox('Select Quarter:', quarters)
    months = ['All'] + [calendar.month_name[m] for m in df['Month'].unique()]
    selected_month = st.sidebar.selectbox('Select Month:', months)

    df_preprocessed = preprocess_data(df)
    df_preprocessed_time = preprocess_data_time(df)

    make_pie_chart(df_preprocessed, 5)

    filtered_df_time = filter_data_time(df=df_preprocessed_time,
                                        selected_quarter=selected_quarter,
                                        selected_year=selected_year,
                                        selected_month=selected_month)
    st.dataframe(filtered_df_time)

    df_sum_time = sum_data_time(filtered_df_time)
    st.dataframe(df_sum_time)
    make_bar_chart(df_sum_time)
else:
    st.warning("You Must Upload a CSV or Excel File")