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

    pjp_list = ['All'] + df['Nama PJP'].unique().tolist()
    years = ['All'] + list(df['Year'].unique())
    quarters = ['All'] + list(df['Quarter'].unique())
    months = ['All'] + [calendar.month_name[m] for m in df['Month'].unique()]

    with st.sidebar:
        with st.expander("Filter Market Share", True):
            selected_pjp = st.selectbox('Select PJP:', pjp_list)
            selected_year_pjp = st.selectbox('Select Year:', years, key="key_year_pjp")
            selected_quarter_pjp = st.selectbox('Select Quarter:', quarters, key="key_quarter_pjp")
        with st.expander("Filter Transactions", True):
            time_option = st.selectbox("Choose Time Period:", ("Month", "Quarter"))
            selected_year = st.selectbox('Select Year:', years, key="key_year_trx")

            if time_option == 'Month':
                selected_month = st.selectbox('Select Month:', months, key="key_month_trx")
            else:
                selected_quarter = st.selectbox('Select Quarter:', quarters, key="key_quarter_trx")
        
    df_preprocessed = preprocess_data(df)
    df_preprocessed_time = preprocess_data(df, isTrx=True)

    filtered_df = filter_data(df=df_preprocessed,
                                selected_pjp=selected_pjp,
                                selected_quarter=selected_quarter_pjp,
                                selected_year=selected_year_pjp,
                                group_by_pjp=True)
    if time_option == "Month":
        filtered_df_time = filter_data(df=df_preprocessed_time,
                                        selected_year=selected_year,
                                        selected_month=selected_month)
        isMonth = True
    else:
        filtered_df_time = filter_data(df=df_preprocessed_time,
                                        selected_year=selected_year,
                                        selected_quarter=selected_quarter)
        isMonth = False
    df_sum_time = sum_data_time(filtered_df_time, isMonth)

    total_sum_of_nom = filtered_df['Sum of Total Nom'].sum()
    df_with_market_share = calculate_market_share(filtered_df, total_sum_of_nom)
    df_sum_time = df_sum_time[(df_sum_time['Sum of Fin Jumlah Inc'] != 0) & (df_sum_time['Sum of Fin Nilai Inc'] != 0) & 
            (df_sum_time['Sum of Fin Jumlah Out'] != 0) & (df_sum_time['Sum of Fin Nilai Out'] != 0) &
            (df_sum_time['Sum of Fin Jumlah Dom'] != 0) & (df_sum_time['Sum of Fin Nilai Dom'] != 0)]
    
    grand_total_inc_nominal = int(df_sum_time['Sum of Fin Nilai Inc'].sum())
    grand_total_inc_jumlah = int(df_sum_time['Sum of Fin Jumlah Inc'].sum())
    grand_total_out_nominal = int(df_sum_time['Sum of Fin Nilai Out'].sum())
    grand_total_out_jumlah = int(df_sum_time['Sum of Fin Jumlah Out'].sum())
    grand_total_dom_nominal = int(df_sum_time['Sum of Fin Nilai Dom'].sum())
    grand_total_dom_jumlah = int(df_sum_time['Sum of Fin Jumlah Dom'].sum())

    grand_total_nominal = int(df_sum_time['Sum of Total Nom'].sum())
    grand_total_frequency = int(df_sum_time['Sum of Fin Jumlah Inc'].sum() + 
                                df_sum_time['Sum of Fin Jumlah Out'].sum() + 
                                df_sum_time['Sum of Fin Jumlah Dom'].sum() )

    col1 = st.columns(1)
    with col1[0]:
        make_pie_chart(df_with_market_share, 5)
    st.dataframe(df_with_market_share)
    col2, col3 = st.columns(2)
    with col2:
        make_grouped_bar_chart(df_sum_time, "Jumlah", isMonth)
    with col3:
        make_grouped_bar_chart(df_sum_time, "Nilai", isMonth)
    st.dataframe(df_sum_time)
    df_grand_totals = pd.DataFrame({
        'Category': ['Incoming', 'Outgoing', 'Domestic', 'All'],
        'Grand Total Jumlah': [grand_total_inc_jumlah, grand_total_out_jumlah, grand_total_dom_jumlah, grand_total_frequency],
        'Grand Total Nominal': [grand_total_inc_nominal, grand_total_out_nominal, grand_total_dom_nominal, grand_total_nominal]
    })
    st.dataframe(df_grand_totals.set_index(df_grand_totals.columns[0]))
else:
    st.warning("You Must Upload a CSV or Excel File")