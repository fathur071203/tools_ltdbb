import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


def make_pie_chart_summary(df, top_n):
    df_sorted = df.sort_values('Market Share (%)', ascending=False)

    df_top_n = df_sorted.head(top_n)

    other_share = df_sorted['Market Share (%)'].sum() - df_top_n['Market Share (%)'].sum()

    df_other = pd.DataFrame([{'Nama PJP': 'Other', 'Market Share (%)': other_share}])
    df_combined = pd.concat([df_top_n, df_other], ignore_index=True)

    fig = px.pie(df_combined,
                 values='Market Share (%)',
                 names='Nama PJP',
                 title=f'Top {top_n} PJPs by Market Share (Including Others)',
                 template='seaborn')

    fig.update_traces(hovertemplate='%{label}: %{value:.2f}%',
                      textfont=dict(color='white'))

    st.plotly_chart(fig, use_container_width=True)


def make_pie_chart_market_share(df: pd.DataFrame, trx_type: str, key: str ,is_nom: bool = True):
    if is_nom:
        data = {
            "Market Share": ["Jakarta", "National"],
            "Percentage": [df['Nominal (dalam triliun)'].values[2], 100 - df['Nominal (dalam triliun)'].values[2]]
        }
        text = "Nominal"
    else:
        data = {
            "Market Share": ["Jakarta", "National"],
            "Percentage": [df['Frekuensi (dalam jutaan)'].values[2], 100 - df['Frekuensi (dalam jutaan)'].values[2]]
        }
        text = "Frekuensi"

    df_combined = pd.DataFrame(data)

    fig = px.pie(df_combined,
                 names='Market Share',
                 values='Percentage',
                 title=f'Market Share {text} {trx_type} Jakarta VS National',
                 template='seaborn')

    fig.update_traces(hovertemplate='%{label}: %{value:.2f}%',
                      textfont=dict(color='white'))

    st.plotly_chart(fig, use_container_width=True, key=key)


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

    st.plotly_chart(fig, use_container_width=True)


def make_combined_bar_line_chart(df, sum_trx_type: str, trx_type: str, is_month: bool = False, is_combined: bool = False):
    df_copy = df.copy()

    if is_combined:
        if is_month:
            df_copy = df_copy[df_copy[f'%MtM {sum_trx_type}'].notnull()]
            df_copy['Year-Month'] = df_copy['Year'].astype(str) + '-' + df_copy['Month'].astype(str)
            target_col = 'Year-Month'
        else:
            df_copy = df_copy[(df_copy[f'%YoY {sum_trx_type}'].notnull()) & (df_copy[f'%QtQ {sum_trx_type}'].notnull())]
            df_copy['Year-Quarter'] = df_copy['Year'].astype(str) + ' Q-' + df_copy['Quarter'].astype(str)
            target_col = 'Year-Quarter'
    else:
        if is_month:
            df_copy = df_copy[df_copy['%MtM'].notnull()]
            df_copy['Year-Month'] = df_copy['Year'].astype(str) + '-' + df_copy['Month'].astype(str)
            target_col = 'Year-Month'
        else:
            df_copy = df_copy[(df_copy['%YoY'].notnull()) & (df_copy['%QtQ'].notnull())]
            df_copy['Year-Quarter'] = df_copy['Year'].astype(str) + ' Q-' + df_copy['Quarter'].astype(str)
            target_col = 'Year-Quarter'

    if sum_trx_type == "Jumlah":
        variabel_trx = "Frekuensi"
    else:
        variabel_trx = "Nominal"

    if trx_type == "Out":
        jenis_trx = "Outgoing"
    elif trx_type == "Inc":
        jenis_trx = "Incoming"
    else:
        jenis_trx = "Domestik"

    bar_col = f'Sum of Fin {sum_trx_type} {trx_type}'
    bar_title = f"Transactions Volume & Growth untuk {variabel_trx} {jenis_trx}"

    if sum_trx_type == "Jumlah":
        bar_yaxis_title = "Volume (Jutaan)"
        scale_factor = 1e6
    else:
        bar_yaxis_title = "Value (Rp Triliun)"
        scale_factor = 1e12

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_copy[target_col],
        y=df_copy[bar_col] / scale_factor,
        name=bar_yaxis_title,
        yaxis='y1',
        hovertemplate='%{x} <br>' + bar_yaxis_title + ': %{y:,.2f}' + '<extra></extra>'
    ))

    if is_combined:
        if is_month:
            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy[f'%MtM {sum_trx_type}'],
                name='Month-to-Month Growth (%)',
                yaxis='y2',
                mode='lines+markers',
                hovertemplate='%{x} <br>Month-to-Month Growth: %{y:,.2f}%' + '<extra></extra>'
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy[f'%YoY {sum_trx_type}'],
                name='Year-on-Year Growth (%)',
                yaxis='y2',
                mode='lines+markers',
                hovertemplate='%{x} <br>Year-on-Year Growth: %{y:,.2f}%' + '<extra></extra>'
            ))

            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy[f'%QtQ {sum_trx_type}'],
                name='Quarter-to-Quarter Growth (%)',
                yaxis='y2',
                mode='lines+markers',
                hovertemplate='%{x} <br>Quarter-to-Quarter Growth: %{y:,.2f}%' + '<extra></extra>'
            ))
    else:
        if is_month:
            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy['%MtM'],
                name='Month-to-Month Growth (%)',
                yaxis='y2',
                mode='lines+markers',
                hovertemplate='%{x} <br>Month-to-Month Growth: %{y:,.2f}%' + '<extra></extra>'
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy['%YoY'],
                name='Year-on-Year Growth (%)',
                yaxis='y2',
                mode='lines+markers',
                hovertemplate='%{x} <br>Year-on-Year Growth: %{y:,.2f}%' + '<extra></extra>'
            ))

            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy['%QtQ'],
                name='Quarter-to-Quarter Growth (%)',
                yaxis='y2',
                mode='lines+markers',
                hovertemplate='%{x} <br>Quarter-to-Quarter Growth: %{y:,.2f}%' + '<extra></extra>'
            ))

    fig.update_layout(
        title=bar_title,
        xaxis=dict(title=target_col),
        yaxis=dict(
            title=bar_yaxis_title,
            tickformat=",.0f",
        ),
        yaxis2=dict(
            title='Growth (%)',
            overlaying='y',
            side='right',
            tickformat=".1f"
        ),
        template="seaborn",
        legend=dict(
            x=1.05,
            y=1,
            xanchor='left',
            yanchor='top',
        )
    )

    st.plotly_chart(fig, use_container_width=True)

def make_combined_bar_line_chart_profile(df: pd.DataFrame, trx_type: str, nama_pjp: str, selected_year: str):
    if trx_type == 'Inc':
        trx_title = "Incoming"
    elif trx_type == 'Out':
        trx_title = "Outgoing"
    else:
        trx_title = "Domestik"

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df['Month'],
        y=df[f'Sum of Fin Nilai {trx_type}'],
        name="Nilai",
        yaxis='y1',
        hovertemplate="%{y:,.0f} <extra></extra>"
    ))

    # Line trace
    fig.add_trace(go.Scatter(
        x=df['Month'],
        y=df[f'Sum of Fin Jumlah {trx_type}'],
        name='Frekuensi',
        yaxis='y2',
        mode='lines+markers',
        hovertemplate="%{y:,.0f} <extra></extra>"
    ))

    fig.update_layout(
        title=f"Perkembangan Transaksi {trx_title} {nama_pjp} Tahun {selected_year} s.d. 2024",
        xaxis=dict(title="Bulan"),
        yaxis=dict(
            title="Nilai (Rp Miliar)",
            tickformat=",.0f",
        ),
        yaxis2=dict(
            title='Frekuensi',
            overlaying='y',
            side='right',
            tickformat=",.0f",
        ),
        template="seaborn",
        legend=dict(
            x=1.05,
            y=1,
            xanchor='left',
            yanchor='top',
        )
    )

    st.plotly_chart(fig, use_container_width=True)

