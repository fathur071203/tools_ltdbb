import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.express as px
import calendar

def make_pie_chart(df, top_n):
    df_sorted = df.sort_values('Market Share (%)', ascending=False)

    df_top_n = df_sorted.head(top_n)

    fig = px.pie(df_top_n, 
                 values='Market Share (%)', 
                 names='Nama PJP', 
                 title=f'Top {top_n} PJPs by Market Share', template='plotly_dark')

    fig.update_layout(
        title=f"Top {top_n} PJPs by Market Share",
        template="plotly_white"
    )

    st.plotly_chart(fig)

def make_grouped_bar_chart(df, mode, isMonth):
    time_label = 'Quarter'
    if isMonth:
        time_label = 'Month'

    value_vars = (['Sum of Fin Jumlah Inc', 'Sum of Fin Jumlah Out', 'Sum of Fin Jumlah Dom'] 
                  if mode == "Jumlah" 
                  else ['Sum of Fin Nilai Inc', 'Sum of Fin Nilai Out', 'Sum of Fin Nilai Dom'])
    
    df_melted = df.melt(id_vars=[time_label], 
                        value_vars=value_vars, 
                        var_name='Financial Metric', value_name='Value')

    df_grouped = df_melted.groupby([time_label, 'Financial Metric'], as_index=False, observed=False).sum()
    
    df_filtered = df_grouped.groupby(time_label, observed=False).filter(lambda x: x['Value'].sum() != 0)
    
    if mode == "Jumlah":
        label = "Frequency"
    else:
        label = "Nominal"
        
    fig = px.bar(df_filtered, 
                 x=time_label, 
                 y='Value', 
                 color='Financial Metric', 
                 barmode='group',
                 title=f'{label} Income, Outcome, and Domestic Transactions by {time_label}',
                 labels={'Value': label, time_label: time_label},
                 template='seaborn')
    
    st.plotly_chart(fig)

