import pandas as pd
import streamlit as st

from preprocess import *
from visualize import *

def main():
    # Initial Web Setup
    set_page_settings()
    set_data_settings()
    uploaded_file = st.file_uploader("Choose a Excel file")
    df = None
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file, 'Trx_PJPJKT')
        df = preprocess_data(df)
        make_pie_chart(df, 5)
    else:
        st.warning("You Must Upload a CSV or Excel File")

if __name__ == '__main__':
    main()