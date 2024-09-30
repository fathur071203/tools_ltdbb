import pandas as pd
import streamlit as st

from preprocess import *
from visualize import *

def main():
    # Initial Web Setup
    col = set_page_settings()
    set_data_settings()

    with col[0]:
        st.text("Column 1")
    with col[1]:
        st.text("Column 2")
    with col[2]:
        st.text("Column 3")

    uploaded_file = st.file_uploader("Choose a Excel file")
    df = None
    if uploaded_file is not None:
        df = load_data(uploaded_file)

        pjps = ['All'] + list(df['Nama PJP'].unique())
        selected_pjp = st.sidebar.selectbox('Select PJP:', pjps)
        quarter = ['All'] + list(df['Quarter'].unique())
        selected_quarter = st.sidebar.selectbox('Select Quarter:', quarter)
        year = ['All'] + list(df['Year'].unique())
        selected_year = st.sidebar.selectbox('Select Year:', year)

        df_preprocessed = preprocess_data(df)
        df_preprocessed_time = preprocess_data_time(df)

        make_pie_chart(df_preprocessed, 5)

        filtered_data = filter_data(df=df_preprocessed_time,
                                    selected_pjp=selected_pjp,
                                    selected_quarter=selected_quarter,
                                    selected_year=selected_year)
        st.dataframe(filtered_data)
    else:
        st.warning("You Must Upload a CSV or Excel File")

if __name__ == '__main__':
    main()