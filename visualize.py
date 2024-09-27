import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.express as px

def make_pie_chart(df, top_n):
    df_sorted = df.sort_values('Market Share (%)', ascending=False)

    df_top_n = df_sorted.head(top_n)

    fig = px.pie(df_top_n, values='Market Share (%)', names='Nama PJP', title=f'Top {top_n} PJPs by Market Share')

    fig.update_layout(
        title=f"Top {top_n} PJPs by Market Share",
        template="plotly_white"
    )

    st.plotly_chart(fig)
