import pandas as pd
import streamlit as st
from PIL import Image

@st.cache_data
def load_data(uploaded_file):
    df = pd.read_excel(uploaded_file, 'Trx_PJPJKT')
    return df

def filter_data(df, selected_pjp, selected_year, selected_quarter):
    if selected_pjp != 'All':
        df = df[df['Nama PJP'] == selected_pjp]
    if selected_year != 'All':
        df = df[df['Year'] == selected_year]
    if selected_quarter != 'All':
        df = df[df['Quarter'] == selected_quarter]
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
    df['Market Share (%)'] = (df['Sum of Total Nom'] / total_sum_of_nom) * 100
    return df

def preprocess_data_time(df):
    df = df.drop(columns=['Nama PJP Conv Final'])
    df = df.groupby(['Nama PJP', 'Year', 'Quarter']).agg({'Fin Jumlah Inc':'sum', 'Fin Nilai Inc':'sum',
                                                          'Fin Jumlah Out':'sum', 'Fin Nilai Out':'sum',
                                                          'Fin Jumlah Dom':'sum', 'Fin Nilai Dom':'sum'})
    
    df = df.rename(columns=lambda x: 'Sum of ' + x)
    df = df.reset_index()
    
    df['Sum of Total Nom'] = df['Sum of Fin Nilai Inc'] + df['Sum of Fin Nilai Out'] + df['Sum of Fin Nilai Dom']
    
    total_sum_of_nom = df.groupby(['Year', 'Quarter'])['Sum of Total Nom'].transform('sum')
    
    df['Market Share (%)'] = ((df['Sum of Total Nom'] / total_sum_of_nom) * 100).round(2)
    return df