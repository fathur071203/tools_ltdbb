import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import calendar


def make_stacked_bar_line_chart_combined(df_inc, df_out, df_dom, is_month: bool = False):
    """
    Membuat grafik gabungan dengan stacked bar (Inc, Out, Dom) dan line growth (YoY)
    """
    # Merge dataframes
    if is_month:
        df_merged = df_inc[['Year', 'Month', 'Sum of Fin Nilai Inc']].copy()
        df_merged = df_merged.merge(df_out[['Year', 'Month', 'Sum of Fin Nilai Out']], on=['Year', 'Month'], how='outer')
        df_merged = df_merged.merge(df_dom[['Year', 'Month', 'Sum of Fin Nilai Dom', '%MtM Nom']], on=['Year', 'Month'], how='outer')
        df_merged['Year-Month'] = df_merged['Year'].astype(str) + '-' + df_merged['Month'].astype(str)
        df_merged = df_merged.sort_values(['Year', 'Month'])
        x_col = 'Year-Month'
        period_label = "Bulan"
        growth_col = '%MtM Nom'
        growth_label = 'Growth MtM (%)'
    else:
        df_merged = df_inc[['Year', 'Quarter', 'Sum of Fin Nilai Inc']].copy()
        df_merged = df_merged.merge(df_out[['Year', 'Quarter', 'Sum of Fin Nilai Out']], on=['Year', 'Quarter'], how='outer')
        df_merged = df_merged.merge(df_dom[['Year', 'Quarter', 'Sum of Fin Nilai Dom', '%YoY Nom']], on=['Year', 'Quarter'], how='outer')
        df_merged['Year-Quarter'] = df_merged['Year'].astype(str) + ' Q' + df_merged['Quarter'].astype(str)
        df_merged = df_merged.sort_values(['Year', 'Quarter'])
        x_col = 'Year-Quarter'
        period_label = "Kuartal"
        growth_col = '%YoY Nom'
        growth_label = 'Growth YoY (%)'
    
    # Filter rows with valid growth data
    df_merged = df_merged[df_merged[growth_col].notnull()]
    
    # Scale to Miliar
    scale_factor = 1e9
    
    fig = go.Figure()
    
    # Stacked bars - Incoming (Pink)
    fig.add_trace(go.Bar(
        x=df_merged[x_col],
        y=df_merged['Sum of Fin Nilai Inc'] / scale_factor,
        name='Incoming',
        marker=dict(color='#F5B0CB', line=dict(width=0)),
        hovertemplate='%{x}<br>Incoming: Rp %{y:,.2f} Miliar<extra></extra>',
        yaxis='y1'
    ))
    
    # Stacked bars - Outgoing (Peach/Orange)
    fig.add_trace(go.Bar(
        x=df_merged[x_col],
        y=df_merged['Sum of Fin Nilai Out'] / scale_factor,
        name='Outgoing',
        marker=dict(color='#F5CBA7', line=dict(width=0)),
        hovertemplate='%{x}<br>Outgoing: Rp %{y:,.2f} Miliar<extra></extra>',
        yaxis='y1'
    ))
    
    # Stacked bars - Domestik (Blue)
    fig.add_trace(go.Bar(
        x=df_merged[x_col],
        y=df_merged['Sum of Fin Nilai Dom'] / scale_factor,
        name='Domestik',
        marker=dict(color='#5DADE2', line=dict(width=0)),
        hovertemplate='%{x}<br>Domestik: Rp %{y:,.2f} Miliar<extra></extra>',
        yaxis='y1'
    ))
    
    # Line - Growth (Dark Green) with data labels
    fig.add_trace(go.Scatter(
        x=df_merged[x_col],
        y=df_merged[growth_col],
        name=growth_label,
        yaxis='y2',
        mode='lines+markers+text',
        line=dict(color='#1E8449', width=3),
        marker=dict(size=8, color='#1E8449', line=dict(color='white', width=2)),
        text=[f"{val:.1f}%" for val in df_merged[growth_col]],
        textposition='top center',
        textfont=dict(
            size=11,
            color='#1E8449',
            family='Inter, Arial, sans-serif',
            weight='bold'
        ),
        hovertemplate='%{x}<br>' + growth_label + ': %{y:.2f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=f"Perkembangan Nilai Transaksi Gabungan (Per {period_label})",
            font=dict(size=22, family='Inter, Arial, sans-serif', color='#1f2937', weight=700)
        ),
        barmode='stack',
        xaxis=dict(
            title=dict(text="Periode", font=dict(size=14, family='Inter, Arial, sans-serif')),
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor='#d1d5db',
            tickangle=-45,
            tickfont=dict(size=11, family='Inter, Arial, sans-serif')
        ),
        yaxis=dict(
            title=dict(text="Nilai (Rp Miliar)", font=dict(size=14, family='Inter, Arial, sans-serif')),
            tickformat=",.0f",
            showgrid=True,
            gridwidth=1,
            gridcolor='#e5e7eb',
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='#d1d5db'
        ),
        yaxis2=dict(
            title=dict(text='Growth (%)', font=dict(size=14, family='Inter, Arial, sans-serif')),
            overlaying='y',
            side='right',
            tickformat=".1f",
            showgrid=False
        ),
        template="plotly_white",
        paper_bgcolor='white',
        plot_bgcolor='#f9fafb',
        font=dict(family='Inter, Arial, sans-serif', size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='#e5e7eb',
            borderwidth=1
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Inter, Arial, sans-serif"
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)


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
                 template='plotly_white')

    fig.update_traces(
        hovertemplate='%{label}: %{value:.2f}%',
        textfont=dict(color='#111827', size=14, family='Inter, Arial, sans-serif', weight='bold'),
        textposition='inside',
        marker=dict(line=dict(color='white', width=3))
    )
    
    fig.update_layout(
        title_font=dict(size=20, family='Inter, Arial, sans-serif', color='#1f2937'),
        font=dict(family='Inter, Arial, sans-serif'),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )

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
    
    # Konsisten warna: Orange untuk Jakarta (lebih gelap), Biru untuk National (lebih gelap)
    color_map = {
        'Jakarta': '#E8964F',  # Orange yang lebih gelap dan saturated
        'National': '#2E7D9E'  # Blue yang lebih gelap
    }

    fig = px.pie(df_combined,
                 names='Market Share',
                 values='Percentage',
                 title=f'Market Share {text} {trx_type} Jakarta VS National',
                 template='plotly_white',
                 color='Market Share',
                 color_discrete_map=color_map)

    fig.update_traces(
        hovertemplate='%{label}: %{value:.2f}%',
        textfont=dict(color='white', size=14, family='Inter, Arial, sans-serif', weight='bold'),
        textposition='inside',
        marker=dict(line=dict(color='white', width=3))
    )
    
    fig.update_layout(
        title_font=dict(size=20, family='Inter, Arial, sans-serif', color='#1f2937'),
        font=dict(family='Inter, Arial, sans-serif'),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )

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

    # Warna konsisten dengan Chart.js HTML
    color_map = {
        'Sum of Fin Nilai Inc': '#F5B0CB',  # Pink untuk Incoming
        'Sum of Fin Nilai Out': '#F5CBA7',  # Peach/Orange untuk Outgoing
        'Sum of Fin Nilai Dom': '#5DADE2',  # Blue untuk Domestik
        'Sum of Fin Jumlah Inc': '#F5B0CB',
        'Sum of Fin Jumlah Out': '#F5CBA7',
        'Sum of Fin Jumlah Dom': '#5DADE2'
    }

    fig = px.bar(df_filtered,
                 x=time_label,
                 y='Value',
                 color='Financial Metric',
                 barmode='group',
                 title=f'{label} Income, Outcome, and Domestic Transactions by {time_label}',
                 labels={'Value': label, time_label: time_label},
                 template='plotly_white',
                 color_discrete_map=color_map)
    
    fig.update_layout(
        title_font=dict(size=20, family='Inter, Arial, sans-serif', color='#1f2937'),
        font=dict(family='Inter, Arial, sans-serif', size=12),
        paper_bgcolor='white',
        plot_bgcolor='#f9fafb',
        xaxis=dict(
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor='#e5e7eb'
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='#e5e7eb'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )

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
            df_copy['Year-Quarter'] = df_copy['Year'].astype(str) + ' Q' + df_copy['Quarter'].astype(str)
            target_col = 'Year-Quarter'
    else:
        if is_month:
            df_copy = df_copy[df_copy['%MtM'].notnull()]
            df_copy['Year-Month'] = df_copy['Year'].astype(str) + '-' + df_copy['Month'].astype(str)
            target_col = 'Year-Month'
        else:
            df_copy = df_copy[(df_copy['%YoY'].notnull()) & (df_copy['%QtQ'].notnull())]
            df_copy['Year-Quarter'] = df_copy['Year'].astype(str) + ' Q' + df_copy['Quarter'].astype(str)
            target_col = 'Year-Quarter'

    if sum_trx_type == "Jumlah":
        variabel_trx = "Frekuensi"
    else:
        variabel_trx = "Nominal"

    if trx_type == "Out":
        jenis_trx = "Outgoing"
        bar_color = '#F5CBA7'  # Peach/Orange
    elif trx_type == "Inc":
        jenis_trx = "Incoming"
        bar_color = '#F5B0CB'  # Pink
    elif trx_type == "Dom":
        jenis_trx = "Domestik"
        bar_color = '#5DADE2'  # Blue
    else:  # trx_type == "Total"
        jenis_trx = "Keseluruhan (Incoming, Outgoing, Domestik)"
        bar_color = '#6366f1'  # Indigo untuk Total

    bar_col = f'Sum of Fin {sum_trx_type} {trx_type}'
    bar_title = f"Perkembangan {variabel_trx} Transaksi {jenis_trx}"

    if sum_trx_type == "Jumlah":
        bar_yaxis_title = "Volume (Jutaan)"
        scale_factor = 1e6
    else:
        bar_yaxis_title = "Nilai (Rp Miliar)"
        scale_factor = 1e9  # Ubah ke Miliar sesuai Chart.js

    fig = go.Figure()

    # Bar trace dengan warna sesuai jenis transaksi
    fig.add_trace(go.Bar(
        x=df_copy[target_col],
        y=df_copy[bar_col] / scale_factor,
        name=bar_yaxis_title,
        yaxis='y1',
        marker=dict(
            color=bar_color,
            line=dict(width=0)
        ),
        hovertemplate='%{x}<br>' + bar_yaxis_title + ': %{y:,.2f}<extra></extra>'
    ))

    # Line traces untuk Growth dengan warna hijau gelap (#1E8449)
    if is_combined:
        if is_month:
            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy[f'%MtM {sum_trx_type}'],
                name='Growth MtM (%)',
                yaxis='y2',
                mode='lines+markers',
                line=dict(color='#1E8449', width=3),
                marker=dict(size=8, color='#1E8449', line=dict(color='white', width=2)),
                hovertemplate='%{x}<br>MtM Growth: %{y:.2f}%<extra></extra>'
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy[f'%YoY {sum_trx_type}'],
                name='Growth YoY (%)',
                yaxis='y2',
                mode='lines+markers',
                line=dict(color='#1E8449', width=3),
                marker=dict(size=8, color='#1E8449', line=dict(color='white', width=2)),
                hovertemplate='%{x}<br>YoY Growth: %{y:.2f}%<extra></extra>'
            ))

            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy[f'%QtQ {sum_trx_type}'],
                name='Growth QtQ (%)',
                yaxis='y2',
                mode='lines+markers',
                line=dict(color='#16a34a', width=3, dash='dot'),
                marker=dict(size=8, color='#16a34a', line=dict(color='white', width=2)),
                hovertemplate='%{x}<br>QtQ Growth: %{y:.2f}%<extra></extra>'
            ))
    else:
        if is_month:
            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy['%MtM'],
                name='Growth MtM (%)',
                yaxis='y2',
                mode='lines+markers',
                line=dict(color='#1E8449', width=3),
                marker=dict(size=8, color='#1E8449', line=dict(color='white', width=2)),
                hovertemplate='%{x}<br>MtM Growth: %{y:.2f}%<extra></extra>'
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy['%YoY'],
                name='Growth YoY (%)',
                yaxis='y2',
                mode='lines+markers',
                line=dict(color='#1E8449', width=3),
                marker=dict(size=8, color='#1E8449', line=dict(color='white', width=2)),
                hovertemplate='%{x}<br>YoY Growth: %{y:.2f}%<extra></extra>'
            ))

            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy['%QtQ'],
                name='Growth QtQ (%)',
                yaxis='y2',
                mode='lines+markers',
                line=dict(color='#16a34a', width=3, dash='dot'),
                marker=dict(size=8, color='#16a34a', line=dict(color='white', width=2)),
                hovertemplate='%{x}<br>QtQ Growth: %{y:.2f}%<extra></extra>'
            ))

    fig.update_layout(
        title=dict(
            text=bar_title,
            font=dict(size=22, family='Inter, Arial, sans-serif', color='#1f2937', weight=700)
        ),
        xaxis=dict(
            title=dict(text="Periode", font=dict(size=14, family='Inter, Arial, sans-serif')),
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor='#d1d5db',
            tickangle=-45,
            tickfont=dict(size=11, family='Inter, Arial, sans-serif')
        ),
        yaxis=dict(
            title=dict(text=bar_yaxis_title, font=dict(size=14, family='Inter, Arial, sans-serif')),
            tickformat=",.0f",
            showgrid=True,
            gridwidth=1,
            gridcolor='#e5e7eb',
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='#d1d5db'
        ),
        yaxis2=dict(
            title=dict(text='Growth (%)', font=dict(size=14, family='Inter, Arial, sans-serif')),
            overlaying='y',
            side='right',
            tickformat=".1f",
            showgrid=False
        ),
        template="plotly_white",
        paper_bgcolor='white',
        plot_bgcolor='#f9fafb',
        font=dict(family='Inter, Arial, sans-serif', size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='#e5e7eb',
            borderwidth=1
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Inter, Arial, sans-serif"
        )
    )

    st.plotly_chart(fig, use_container_width=True)

def make_combined_bar_line_chart_profile(df: pd.DataFrame, trx_type: str, nama_pjp: str, selected_year: str):
    # Buat label time-series lintas tahun: YYYY-MM dan urutkan kronologis
    df_copy = df.copy()
    
    if 'Year' in df_copy.columns and 'Month' in df_copy.columns:
        df_copy['MonthNum'] = df_copy['Month'].apply(lambda m: list(calendar.month_name).index(m) if isinstance(m, str) else int(m))
        df_copy['YearMonth'] = df_copy['Year'].astype(int).astype(str) + '-' + df_copy['MonthNum'].astype(int).astype(str).str.zfill(2)
        df_copy = df_copy.sort_values(['Year', 'MonthNum'])
    else:
        df_copy['YearMonth'] = df_copy.index.astype(str)

    if trx_type == 'Inc':
        trx_title = "Incoming"
        bar_color = '#F5B0CB'  # Pink
    elif trx_type == 'Out':
        trx_title = "Outgoing"
        bar_color = '#F5CBA7'  # Peach/Orange
    else:
        trx_title = "Domestik"
        bar_color = '#5DADE2'  # Blue

    fig = go.Figure()

    # Bar trace
    fig.add_trace(go.Bar(
        x=df_copy['YearMonth'],
        y=df_copy[f'Sum of Fin Nilai {trx_type}'],
        name="Nilai",
        yaxis='y1',
        marker=dict(
            color=bar_color,
            line=dict(width=0)
        ),
        hovertemplate="%{x}<br>Nilai: Rp %{y:,.0f}<extra></extra>"
    ))

    # Line trace dengan warna hijau
    fig.add_trace(go.Scatter(
        x=df_copy['YearMonth'],
        y=df_copy[f'Sum of Fin Jumlah {trx_type}'],
        name='Frekuensi',
        yaxis='y2',
        mode='lines+markers',
        line=dict(color='#1E8449', width=3),
        marker=dict(size=8, color='#1E8449', line=dict(color='white', width=2)),
        hovertemplate="%{x}<br>Frekuensi: %{y:,.0f}<extra></extra>"
    ))

    fig.update_layout(
        title=dict(
            text=f"Perkembangan Transaksi {trx_title} - {nama_pjp} ({selected_year})",
            font=dict(size=22, family='Inter, Arial, sans-serif', color='#1f2937', weight=700)
        ),
        xaxis=dict(
            title=dict(text="Periode (YYYY-MM)", font=dict(size=14, family='Inter, Arial, sans-serif')),
            tickangle=-45,
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor='#d1d5db',
            tickfont=dict(size=11, family='Inter, Arial, sans-serif')
        ),
        yaxis=dict(
            title=dict(text="Nilai (Rp Miliar)", font=dict(size=14, family='Inter, Arial, sans-serif')),
            tickformat=",.0f",
            showgrid=True,
            gridwidth=1,
            gridcolor='#e5e7eb',
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='#d1d5db'
        ),
        yaxis2=dict(
            title=dict(text='Frekuensi', font=dict(size=14, family='Inter, Arial, sans-serif')),
            overlaying='y',
            side='right',
            tickformat=",.0f",
            showgrid=False
        ),
        template="plotly_white",
        paper_bgcolor='white',
        plot_bgcolor='#f9fafb',
        font=dict(family='Inter, Arial, sans-serif', size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='#e5e7eb',
            borderwidth=1
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Inter, Arial, sans-serif"
        )
    )

    st.plotly_chart(fig, use_container_width=True)

