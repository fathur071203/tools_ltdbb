import pandas as pd
import streamlit as st
import plotly.express as px


def make_pie_chart(df, top_n):
    df_sorted = df.sort_values('Market Share (%)', ascending=False)
    
    df_top_n = df_sorted.head(top_n)
    
    other_share = df_sorted['Market Share (%)'].sum() - df_top_n['Market Share (%)'].sum()
    
    df_other = pd.DataFrame([{'Nama PJP': 'Other', 'Market Share (%)': other_share}])
    df_combined = pd.concat([df_top_n, df_other], ignore_index=True)
    
    fig = px.pie(df_combined, 
                 values='Market Share (%)', 
                 names='Nama PJP', 
                 title=f'Top {top_n} PJPs by Market Share (Including Others)',
                 template='plotly_dark')
    
    fig.update_traces(hovertemplate='%{label}: %{value:.2f}%')

    fig.update_layout(
        title=f"Top {top_n} PJPs by Market Share (Including Others)",
        template="plotly_white"
    )

    st.plotly_chart(fig)

def make_grouped_bar_chart(df, mode, is_month):
    time_label = 'Quarter'
    if is_month:
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

def make_bar_chart_growth(df, mode="Jumlah"):
    df_copy = df.copy()

    df_copy['Year-Quarter'] = df_copy['Year'].astype(str) + ' Q-' + df_copy['Quarter'].astype(str)

    if mode == "Jumlah":
        bar_col = 'Sum of Fin Jumlah Inc'
        title = "Incoming Transactions - Volume & Growth"
        bar_yaxis_title = "Jutaan"
    else:
        bar_col = 'Sum of Fin Nilai Inc'
        title = "Incoming Transactions - Value & Growth"
        bar_yaxis_title = "Rp Triliun"

    fig = px.bar(df_copy, x='Year-Quarter', y=bar_col, title=title, labels={
        bar_col: bar_yaxis_title
    })

    fig.update_yaxes(
        tickprefix="",
        tickformat=",",
        title_text=bar_yaxis_title
    )

    st.plotly_chart(fig)
