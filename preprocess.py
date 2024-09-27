import pandas as pd
import streamlit as st

def set_data_settings():
    st.title('Data LTDBB PJP LR JKT Visualization')
    pd.set_option('display.float_format', '{:,.2f}'.format)

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