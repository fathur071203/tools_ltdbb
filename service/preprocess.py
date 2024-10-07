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

def filter_data(df, selected_pjp=None, selected_year=None, 
                selected_quarter=None, selected_month=None, 
                group_by_pjp=False):
    
    if selected_year and selected_year != 'All':
        df = df[df['Year'] == selected_year]
    if selected_quarter and selected_quarter != 'All':
        df = df[df['Quarter'] == selected_quarter]
    if selected_month and selected_month != 'All':
        df = df[df['Month'] == selected_month]
    if selected_pjp and selected_pjp != 'All':
        df = df[df['Nama PJP'] == selected_pjp]

    if group_by_pjp:
        df = df.groupby('Nama PJP').agg({
            'Sum of Fin Nilai Out': 'sum',
            'Sum of Fin Nilai Inc': 'sum',
            'Sum of Fin Nilai Dom': 'sum',
            'Sum of Fin Jumlah Out': 'sum',
            'Sum of Fin Jumlah Inc': 'sum',
            'Sum of Fin Jumlah Dom': 'sum',
        }).reset_index()

        df['Sum of Total Nom'] = df[['Sum of Fin Nilai Inc', 'Sum of Fin Nilai Out', 'Sum of Fin Nilai Dom']].sum(axis=1)
        df.insert(1, 'Sum of Total Nom', df.pop('Sum of Total Nom'))

    return df


def set_data_settings():
    pd.set_option('display.float_format', '{:,.2f}'.format)
    return

def set_page_settings():
    pages = [
        st.Page(page="views/summary.py", title="Summary", default=True),
        st.Page(page="views/growth.py", title="Growth"),
        st.Page(page="views/profile.py", title="Profile"),
        st.Page(page="views/market_share.py", title="Market Share"),
    ]
    st.set_page_config(
        page_title="Tools Analisa Data LTDBB",
        page_icon="./static/favicon.png",
        layout="wide",
        initial_sidebar_state="expanded")
    pg = st.navigation(pages=pages)
    pg.run()

def set_page_visuals():
    st.title('Data LTDBB PJP LR JKT Visualization')
    with st.sidebar:
        st.image("./static/Logo.png")

def aggregate_data(df, isTrx=False):
    if isTrx:
        group_cols = ['Nama PJP', 'Year', 'Quarter', 'Month']
    else:
        group_cols = ['Nama PJP', 'Year', 'Quarter']
    df = df.drop(columns=['Nama PJP Conv Final'])
    df = df.groupby(group_cols).agg({'Fin Jumlah Inc':'sum', 'Fin Nilai Inc':'sum',
                                'Fin Jumlah Out':'sum', 'Fin Nilai Out':'sum',
                                'Fin Jumlah Dom':'sum', 'Fin Nilai Dom':'sum',})
    df = df.rename(columns=lambda x: 'Sum of ' + x)
    df = df.reset_index()
    df['Sum of Total Nom'] = df['Sum of Fin Nilai Inc'] + df['Sum of Fin Nilai Out'] + df['Sum of Fin Nilai Dom']
    return df


def preprocess_data(df_non_agg, isTrx=False):
    if isTrx:
        df = aggregate_data(df_non_agg, isTrx=isTrx)
        df['Month'] = df['Month'].apply(lambda x: calendar.month_name[x])

        months = ["January", "February", "March", "April", "May", "June", 
                  "July", "August", "September", "October", "November", "December"]
        df['Month'] = pd.Categorical(df['Month'], categories=months, ordered=True)

        group_cols = ['Year', 'Quarter', 'Month']
    else:
        df = aggregate_data(df_non_agg)
        group_cols = ['Year', 'Quarter']

    total_sum_of_nom = df.groupby(group_cols, observed=False)['Sum of Total Nom'].transform('sum')

    df = calculate_market_share(df, total_sum_of_nom)

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
        group_cols = ['Year', 'Month']
    else:
        group_cols = ['Year', 'Quarter']
    df_sum = df.groupby(group_cols, observed=False).agg({
        'Sum of Fin Jumlah Inc': 'sum',
        'Sum of Fin Nilai Inc': 'sum',
        'Sum of Fin Jumlah Out': 'sum',
        'Sum of Fin Nilai Out': 'sum',
        'Sum of Fin Jumlah Dom': 'sum',
        'Sum of Fin Nilai Dom': 'sum',
        'Sum of Total Nom': 'sum',
    }).reset_index()
    return df_sum

def calculate_market_share(df, total_sum_of_nom):
    df['Market Share (%)'] = ((df['Sum of Total Nom'] / total_sum_of_nom) * 100).round(2)
    return df