import pandas as pd
import streamlit as st
import calendar

from PIL import Image


@st.cache_data
def load_data(uploaded_file):
    df = pd.read_excel(uploaded_file, 'Trx_PJPJKT')
    return df

def filter_data_time(df, selected_year, selected_quarter, selected_month):
    month_mapping = {v: k for k, v in enumerate(calendar.month_name) if v}
    if selected_year != 'All':
        df = df[df['Year'] == selected_year]
    if selected_quarter != 'All':
        df = df[df['Quarter'] == selected_quarter]
    if selected_month != 'All':
        df = df[df['Month'] == month_mapping[selected_month]]
    return df

def set_data_settings():
    pd.set_option('display.float_format', '{:,.2f}'.format)

def set_page_settings():
    st.set_page_config(
        page_title="Tools Analisa Data LTDBB",
        page_icon="./static/favicon.png",
        layout="wide",
        initial_sidebar_state="expanded")
    st.title('Data LTDBB PJP LR JKT Visualization')
    col = st.columns((1.5, 4.5, 2), gap='medium')
    with st.sidebar:
        st.image("./static/Logo.png")
    return col

def preprocess_data(df):
    df = df.drop(columns=['Nama PJP Conv Final'])
    df = df.groupby('Nama PJP').agg({'Fin Jumlah Inc':'sum', 'Fin Nilai Inc':'sum',
                                'Fin Jumlah Out':'sum', 'Fin Nilai Out':'sum',
                                'Fin Jumlah Dom':'sum', 'Fin Nilai Dom':'sum',})
    df = df.rename(columns=lambda x: 'Sum of ' + x)
    df = df.reset_index()
    df['Sum of Total Nom'] = df['Sum of Fin Nilai Inc'] + df['Sum of Fin Nilai Out'] + df['Sum of Fin Nilai Dom']

    total_sum_of_nom = df['Sum of Total Nom'].sum()
    df['Market Share (%)'] = ((df['Sum of Total Nom'] / total_sum_of_nom) * 100).round(2)
    return df

def preprocess_data_time(df):
    df = df.drop(columns=['Nama PJP Conv Final'])
    df = df.groupby(['Nama PJP', 'Year', 'Quarter', 'Month']).agg({'Fin Jumlah Inc':'sum', 'Fin Nilai Inc':'sum',
                                                          'Fin Jumlah Out':'sum', 'Fin Nilai Out':'sum',
                                                          'Fin Jumlah Dom':'sum', 'Fin Nilai Dom':'sum'})
    
    df = df.rename(columns=lambda x: 'Sum of ' + x)
    df = df.reset_index()
    
    df['Sum of Total Nom'] = df['Sum of Fin Nilai Inc'] + df['Sum of Fin Nilai Out'] + df['Sum of Fin Nilai Dom']
    
    total_sum_of_nom = df.groupby(['Year', 'Quarter', 'Month'])['Sum of Total Nom'].transform('sum')
    
    df['Market Share (%)'] = ((df['Sum of Total Nom'] / total_sum_of_nom) * 100).round(2)
    return df

def sum_data_time(df):
    df_sum = df.groupby(['Year', 'Quarter', 'Month']).agg({
        'Sum of Fin Jumlah Inc': 'sum',
        'Sum of Fin Nilai Inc': 'sum',
        'Sum of Fin Jumlah Out': 'sum',
        'Sum of Fin Nilai Out': 'sum',
        'Sum of Fin Jumlah Dom': 'sum',
        'Sum of Fin Nilai Dom': 'sum',
        'Sum of Total Nom': 'sum',
    }).reset_index()

    return df_sum