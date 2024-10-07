import pandas as pd
import streamlit as st
import calendar

from PIL import Image

@st.cache_data
def load_data(uploaded_file):
    df = pd.read_excel(uploaded_file, 'Trx_PJPJKT')
    return df

def format_to_rupiah(amount):
    return "Rp {:,}".format(amount)

def filter_data_pjp(df, selected_pjp, selected_year, selected_quarter):
    if selected_year != 'All':
        df = df[df['Year'] == selected_year]
    if selected_quarter != 'All':
        df = df[df['Quarter'] == selected_quarter]
    if selected_pjp != 'All':
        df = df[df['Nama PJP'] == selected_pjp]

    df = df.groupby('Nama PJP').agg({
        'Sum of Fin Nilai Out': 'sum',
        'Sum of Fin Nilai Inc': 'sum',
        'Sum of Fin Nilai Dom': 'sum',
        'Sum of Fin Jumlah Out': 'sum',
        'Sum of Fin Jumlah Inc': 'sum',
        'Sum of Fin Jumlah Dom': 'sum',
    }).reset_index()

    df['Sum of Total Nominal'] = df['Sum of Fin Nilai Inc'] + df['Sum of Fin Nilai Out'] + df['Sum of Fin Nilai Dom']
    df.insert(1, 'Sum of Total Nominal', df.pop('Sum of Total Nominal'))
    return df

def filter_data_month(df, selected_year, selected_month):
    if selected_year != 'All':
        df = df[df['Year'] == selected_year]
    if selected_month != 'All':
        df = df[df['Month'] == selected_month]
    return df

def filter_data_quarter(df, selected_year, selected_quarter):
    if selected_year != 'All':
        df = df[df['Year'] == selected_year]
    if selected_quarter != 'All':
        df = df[df['Quarter'] == selected_quarter]
    return df

def set_data_settings():
    pd.set_option('display.float_format', '{:,.2f}'.format)
    return

def set_page_settings():
    summary_page = st.Page(
        page="views/summary.py",
        title="Summary",
        default=True
    )
    growth_page = st.Page(
        page="views/growth.py",
        title="Growth",
    )
    profile_page = st.Page(
        page="views/profile.py",
        title="Profile",
    )
    market_share_page = st.Page(
        page="views/market_share.py",
        title="Market Share",
    )
    pg = st.navigation(pages=[summary_page,growth_page,profile_page,market_share_page])
    st.set_page_config(
        page_title="Tools Analisa Data LTDBB",
        page_icon="./static/favicon.png",
        layout="wide",
        initial_sidebar_state="expanded")
    pg.run()

def set_page_visuals():
    st.title('Data LTDBB PJP LR JKT Visualization')
    with st.sidebar:
        st.image("./static/Logo.png")

def preprocess_data(df):
    df = df.drop(columns=['Nama PJP Conv Final'])
    df = df.groupby(['Nama PJP', 'Year', 'Quarter']).agg({'Fin Jumlah Inc':'sum', 'Fin Nilai Inc':'sum',
                                'Fin Jumlah Out':'sum', 'Fin Nilai Out':'sum',
                                'Fin Jumlah Dom':'sum', 'Fin Nilai Dom':'sum',})
    df = df.rename(columns=lambda x: 'Sum of ' + x)
    df = df.reset_index()
    df['Sum of Total Nom'] = df['Sum of Fin Nilai Inc'] + df['Sum of Fin Nilai Out'] + df['Sum of Fin Nilai Dom']

    total_sum_of_nom = df.groupby(['Year', 'Quarter'])['Sum of Total Nom'].transform('sum')
    
    df['Market Share (%)'] = ((df['Sum of Total Nom'] / total_sum_of_nom) * 100).round(2)
    return df

def preprocess_data_time(df):
    df = df.drop(columns=['Nama PJP Conv Final'])
    df = df.groupby(['Nama PJP', 'Year', 'Quarter', 'Month']).agg({'Fin Jumlah Inc':'sum', 'Fin Nilai Inc':'sum',
                                                          'Fin Jumlah Out':'sum', 'Fin Nilai Out':'sum',
                                                          'Fin Jumlah Dom':'sum', 'Fin Nilai Dom':'sum'})
    
    df = df.rename(columns=lambda x: 'Sum of ' + x)
    df = df.reset_index()

    df['Month'] = df['Month'].apply(lambda x: calendar.month_name[x])

    months = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]
    
    df['Month'] = pd.Categorical(df['Month'], categories=months, ordered=True)

    df['Sum of Total Nom'] = df['Sum of Fin Nilai Inc'] + df['Sum of Fin Nilai Out'] + df['Sum of Fin Nilai Dom']
    
    total_sum_of_nom = df.groupby(['Year', 'Quarter', 'Month'], observed=False)['Sum of Total Nom'].transform('sum')
    
    df['Market Share (%)'] = ((df['Sum of Total Nom'] / total_sum_of_nom) * 100).round(2)
    return df

def preprocess_data_growth(df):
    df['%YoY'] = pd.NA
    df['%QtQ'] = pd.NA
    df['%MtM'] = pd.NA

    first_year = df['Year'].min()
    df.loc[df['Year'] == first_year, ['%YoY', '%QtQ', '%MtM']] = pd.NA

    #TODO: Logic calculations for %YoY, %QtQ, and %MtM

    df_jumlah_inc = df[['Year', 'Quarter', 'Sum of Fin Jumlah Inc', '%YoY', '%QtQ', '%MtM']].copy()
    df_jumlah_out = df[['Year', 'Quarter', 'Sum of Fin Jumlah Out', '%YoY', '%QtQ', '%MtM']].copy()
    df_jumlah_dom = df[['Year', 'Quarter', 'Sum of Fin Jumlah Dom', '%YoY', '%QtQ', '%MtM']].copy()
    df_freq_inc = df[['Year', 'Quarter', 'Sum of Fin Nilai Inc', '%YoY', '%QtQ', '%MtM']].copy()
    df_freq_out = df[['Year', 'Quarter', 'Sum of Fin Nilai Out', '%YoY', '%QtQ', '%MtM']].copy()
    df_freq_dom = df[['Year', 'Quarter', 'Sum of Fin Nilai Dom', '%YoY', '%QtQ', '%MtM']].copy()

    return df_jumlah_inc, df_jumlah_out, df_jumlah_dom, df_freq_inc, df_freq_out, df_freq_dom

def sum_data_time(df, isMonth):
    if isMonth:
        df_sum = df.groupby(['Year', 'Month'], observed=False).agg({
            'Sum of Fin Jumlah Inc': 'sum',
            'Sum of Fin Nilai Inc': 'sum',
            'Sum of Fin Jumlah Out': 'sum',
            'Sum of Fin Nilai Out': 'sum',
            'Sum of Fin Jumlah Dom': 'sum',
            'Sum of Fin Nilai Dom': 'sum',
            'Sum of Total Nom': 'sum',
        }).reset_index()
    else:
        df_sum = df.groupby(['Year', 'Quarter']).agg({
            'Sum of Fin Jumlah Inc': 'sum',
            'Sum of Fin Nilai Inc': 'sum',
            'Sum of Fin Jumlah Out': 'sum',
            'Sum of Fin Nilai Out': 'sum',
            'Sum of Fin Jumlah Dom': 'sum',
            'Sum of Fin Nilai Dom': 'sum',
            'Sum of Total Nom': 'sum',
        }).reset_index()
    return df_sum

def calculate_market_share(df):
    total_sum_of_nom = df['Sum of Total Nominal'].sum()
    df['Market Share (%)'] = ((df['Sum of Total Nominal'] / total_sum_of_nom) * 100).round(2)

    return df