import pandas as pd
import streamlit as st

def main():
    st.write("""
    # My first app Hello *world!*
    """)

    uploaded_file = st.file_uploader("Choose a Excel file")
    df = None
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file, 'Trx_PJPJKT')
        st.dataframe(df)
    else:
        st.warning("You Must Upload a CSV or Excel File")

if __name__ == '__main__':
    main()