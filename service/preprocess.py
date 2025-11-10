import pandas as pd
import streamlit as st
import calendar
import numpy as np

@st.cache_data
def load_data(uploaded_file, is_trx_nasional: bool = False):
    sheet_name = 'Trx_PJPJKT'
    if is_trx_nasional:
        sheet_name = 'Raw_JKTNasional'
    try:
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
    except ValueError as e:
        st.error(f"Sheet '{sheet_name}' not found in the uploaded file. Please upload the file according to the format.")
        return None
    except Exception as e:
        st.error(f"An error occurred while loading the data: {e}")
        return None
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

        df['Sum of Total Nom'] = df[['Sum of Fin Nilai Inc', 'Sum of Fin Nilai Out', 'Sum of Fin Nilai Dom']].sum(
            axis=1)
        df['Sum of Total Jumlah'] = df[['Sum of Fin Jumlah Inc', 'Sum of Fin Jumlah Out', 'Sum of Fin Jumlah Dom']].sum(
            axis=1)
        df.insert(1, 'Sum of Total Nom', df.pop('Sum of Total Nom'))
        df.insert(1, 'Sum of Total Jumlah', df.pop('Sum of Total Jumlah'))

    return df


def filter_start_end_year(df, start_year, end_year, is_month: bool = False):
    if is_month:
        for col in df.columns:
            if 'Sum of Fin' in col:
                df = df[~((df[col] == 0) & (df['Year'] == df['Year'].max()))]
    df_filtered = df[(df['Year'] >= start_year) & (df['Year'] <= end_year)]
    return df_filtered


def set_data_settings():
    pd.set_option('display.float_format', '{:,.2f}'.format)
    return


def set_page_settings():
    pages = [
        st.Page(page="views/summary.py", title="Summary", default=True),
        st.Page(page="views/growth.py", title="Growth"),
        st.Page(page="views/profile.py", title="Profile"),
        st.Page(page="views/market_share.py", title="Market Share"),
        st.Page(page="views/fraud.py", title="Analisis TKM"),
        st.Page(page="views/manage_data.py", title="Kelola Data")
    ]
    st.set_page_config(
        page_title="Tools Analisa Data LTDBB",
        page_icon=".static/favicon.png",
        layout="wide",
        initial_sidebar_state="expanded")
    pg = st.navigation(pages=pages)
    pg.run()


def set_page_visuals(condition):
    if condition == "viz":
        st.title('Data LTDBB PJP LR JKT Visualization')
    elif condition == "fds":
        st.title('Analisis Transaksi Keuangan Mencurigakan (TKM)')
    elif condition == "dm":
        st.title('Kelola Data Sistem')
    with st.sidebar:
        st.image(".static/Logo.png")

def aggregate_data(df, is_trx=False):
    if is_trx:
        group_cols = ['Nama PJP', 'Year', 'Quarter', 'Month']
    else:
        group_cols = ['Nama PJP', 'Year', 'Quarter']
    df = df.drop(columns=['Nama PJP Conv Final'])
    df = df.groupby(group_cols).agg({'Fin Jumlah Inc': 'sum', 'Fin Nilai Inc': 'sum',
                                     'Fin Jumlah Out': 'sum', 'Fin Nilai Out': 'sum',
                                     'Fin Jumlah Dom': 'sum', 'Fin Nilai Dom': 'sum', })
    df = df.rename(columns=lambda x: 'Sum of ' + x)
    df = df.reset_index()
    df['Sum of Total Nom'] = df['Sum of Fin Nilai Inc'] + df['Sum of Fin Nilai Out'] + df['Sum of Fin Nilai Dom']
    return df


def preprocess_data(df_non_agg, is_trx=False):
    if is_trx:
        df = aggregate_data(df_non_agg, is_trx=is_trx)
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


def preprocess_data_growth(df, is_month: bool):
    df['%YoY'] = pd.NA
    df['%QtQ'] = pd.NA
    df['%MtM'] = pd.NA

    first_year = df['Year'].min()
    df.loc[df['Year'] == first_year, ['%YoY', '%QtQ', '%MtM']] = pd.NA

    # TODO: Logic calculations for %YoY, %QtQ, and %MtM
    if is_month:
        df_jumlah_inc_month = df[['Year', 'Month', 'Sum of Fin Jumlah Inc', '%MtM']].copy()
        df_jumlah_inc_month = calculate_month_to_month(df_jumlah_inc_month, first_year, 'Jumlah', 'Inc')

        df_jumlah_out_month = df[['Year', 'Month', 'Sum of Fin Jumlah Out', '%MtM']].copy()
        df_jumlah_out_month = calculate_month_to_month(df_jumlah_out_month, first_year, 'Jumlah', 'Out')

        df_jumlah_dom_month = df[['Year', 'Month', 'Sum of Fin Jumlah Dom', '%MtM']].copy()
        df_jumlah_dom_month = calculate_month_to_month(df_jumlah_dom_month, first_year, 'Jumlah', 'Dom')

        df_nom_inc_month = df[['Year', 'Month', 'Sum of Fin Nilai Inc', '%MtM']].copy()
        df_nom_inc_month = calculate_month_to_month(df_nom_inc_month, first_year, 'Nilai', 'Inc')

        df_nom_out_month = df[['Year', 'Month', 'Sum of Fin Nilai Out', '%MtM']].copy()
        df_nom_out_month = calculate_month_to_month(df_nom_out_month, first_year, 'Nilai', 'Out')

        df_nom_dom_month = df[['Year', 'Month', 'Sum of Fin Nilai Dom', '%MtM']].copy()
        df_nom_dom_month = calculate_month_to_month(df_nom_dom_month, first_year, 'Nilai', 'Dom')

        return (df_jumlah_inc_month, df_jumlah_out_month, df_jumlah_dom_month,
                df_nom_inc_month, df_nom_out_month, df_nom_dom_month)
    else:
        df_jumlah_inc = df[['Year', 'Quarter', 'Sum of Fin Jumlah Inc', '%YoY', '%QtQ']].copy()
        df_jumlah_inc = calculate_growth(df_jumlah_inc, first_year, 'Jumlah', 'Inc')

        df_jumlah_out = df[['Year', 'Quarter', 'Sum of Fin Jumlah Out', '%YoY', '%QtQ']].copy()
        df_jumlah_out = calculate_growth(df_jumlah_out, first_year, 'Jumlah', 'Out')

        df_jumlah_dom = df[['Year', 'Quarter', 'Sum of Fin Jumlah Dom', '%YoY', '%QtQ']].copy()
        df_jumlah_dom = calculate_growth(df_jumlah_dom, first_year, 'Jumlah', 'Dom')

        df_nom_inc = df[['Year', 'Quarter', 'Sum of Fin Nilai Inc', '%YoY', '%QtQ']].copy()
        df_nom_inc = calculate_growth(df_nom_inc, first_year, 'Nilai', 'Inc')

        df_nom_out = df[['Year', 'Quarter', 'Sum of Fin Nilai Out', '%YoY', '%QtQ']].copy()
        df_nom_out = calculate_growth(df_nom_out, first_year, 'Nilai', 'Out')

        df_nom_dom = df[['Year', 'Quarter', 'Sum of Fin Nilai Dom', '%YoY', '%QtQ']].copy()
        df_nom_dom = calculate_growth(df_nom_dom, first_year, 'Nilai', 'Dom')

        return df_jumlah_inc, df_jumlah_out, df_jumlah_dom, df_nom_inc, df_nom_out, df_nom_dom


def preprocess_data_national(df: pd.DataFrame, is_year: bool = False, is_quarter: bool = False) -> pd.DataFrame:
    df_copy = df.copy()

    if 'Nom Nasional Total.1' in df_copy.columns:
        df_copy.drop('Nom Nasional Total.1', axis=1, inplace=True)

    aggregation_dict = {
        'Nom Nasional Out': 'sum',
        'Nom Nasional Inc': 'sum',
        'Nom Nasional Dom': 'sum',
        'Nom Nasional Total': 'sum',
        'Frek Nasional Out': 'sum',
        'Frek Nasional Inc': 'sum',
        'Frek Nasional Dom': 'sum',
        'Frek Nasional Total': 'sum',
    }

    if is_year:
        if is_quarter:
            grouped_df = df_copy.groupby(['Year', 'Quarter']).agg(aggregation_dict).reset_index()
        else:
            grouped_df = df_copy.groupby('Year').agg(aggregation_dict).reset_index()
    else:
        grouped_df = df_copy.groupby(['Year', 'Month']).agg(aggregation_dict).reset_index()

    return grouped_df

def process_combined_df(df_inc: pd.DataFrame, df_out: pd.DataFrame, df_dom: pd.DataFrame,
                        is_month: bool = False) -> pd.DataFrame:
    if is_month:
        group_cols = ['Year', 'Month']
    else:
        group_cols = ['Year', 'Quarter']
    df_total = pd.concat([df_inc, df_out, df_dom])

    df_total = df_total.groupby(group_cols, observed=False).sum().reset_index()

    trx_type = "Jumlah"

    for col in df_total.columns:
        if "Nilai" in col or "Nom" in col:
            trx_type = "Nilai"
            break

    df_total[f'Sum of Fin {trx_type} Total'] = df_total[f'Sum of Fin {trx_type} Inc'] + df_total[
        f'Sum of Fin {trx_type} Out'] + \
                                               df_total[f'Sum of Fin {trx_type} Dom']

    return df_total


def process_growth_combined(df_jumlah_total: pd.DataFrame, df_nom_total: pd.DataFrame, first_year: int,
                            is_month: bool = False) -> pd.DataFrame:
    if is_month:
        group_cols = ['Year', 'Month']
        drop_cols_jumlah = ['%MtM', 'Sum of Fin Jumlah Inc',
                            'Sum of Fin Jumlah Out', 'Sum of Fin Jumlah Dom']
        drop_cols_nom = ['%MtM', 'Sum of Fin Nilai Inc',
                         'Sum of Fin Nilai Out', 'Sum of Fin Nilai Dom']
    else:
        group_cols = ['Year', 'Quarter']
        drop_cols_jumlah = ['%YoY', '%QtQ', 'Sum of Fin Jumlah Inc',
                            'Sum of Fin Jumlah Out', 'Sum of Fin Jumlah Dom']
        drop_cols_nom = ['%YoY', '%QtQ', 'Sum of Fin Nilai Inc',
                         'Sum of Fin Nilai Out', 'Sum of Fin Nilai Dom']
    df_jumlah_total.drop(drop_cols_jumlah, axis=1, inplace=True)
    df_nom_total.drop(drop_cols_nom, axis=1, inplace=True)

    df_total = pd.merge(df_jumlah_total, df_nom_total, on=group_cols)

    if not is_month:
        df_total_jumlah = calculate_growth(df_total, first_year, "Jumlah", "Total")
        df_total_nilai = calculate_growth(df_total, first_year, "Nilai", "Total")
        df_total_combined = (
            pd.merge(df_total_jumlah, df_total_nilai, on=group_cols)
            .drop(['Sum of Fin Jumlah Total_y', 'Sum of Fin Nilai Total_y'], axis=1)
            .rename(columns={'Sum of Fin Jumlah Total_x': 'Sum of Fin Jumlah Total',
                             'Sum of Fin Nilai Total_x': 'Sum of Fin Nilai Total',
                             '%YoY_x': '%YoY Jumlah', '%YoY_y': '%YoY Nilai',
                             '%QtQ_x': '%QtQ Jumlah', '%QtQ_y': '%QtQ Nilai', })
        )
    else:
        df_total_jumlah = calculate_month_to_month(df_total, first_year, "Jumlah", "Total")
        df_total_nilai = calculate_month_to_month(df_total, first_year, "Nilai", "Total")
        df_total_combined = (
            pd.merge(df_total_jumlah, df_total_nilai, on=group_cols)
            .drop(['Sum of Fin Jumlah Total_y', 'Sum of Fin Nilai Total_y'], axis=1)
            .rename(columns={'Sum of Fin Jumlah Total_x': 'Sum of Fin Jumlah Total',
                             'Sum of Fin Nilai Total_x': 'Sum of Fin Nilai Total',
                             '%MtM_x': '%MtM Jumlah', '%MtM_y': '%MtM Nilai'})
        )
    return df_total_combined


def sum_data_time(df, is_month):
    if is_month:
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


def calculate_growth(df: pd.DataFrame, first_year: int, sum_trx_type: str, trx_type: str):
    df_copy = df.copy()
    df_copy = calculate_year_on_year(df_copy, first_year, sum_trx_type, trx_type)
    df_copy = calculate_quarter_to_quarter(df_copy, first_year, sum_trx_type, trx_type)
    return df_copy


def calculate_year_on_year(df: pd.DataFrame, first_year: int, sum_trx_type: str, trx_type: str):
    for i in range(len(df)):
        if df.iloc[i]['Year'] > first_year:
            current_value = df.iloc[i][f'Sum of Fin {sum_trx_type} {trx_type}']
            previous_year_value = df[(df['Year'] == df.iloc[i]['Year'] - 1) &
                                     (df['Quarter'] == df.iloc[i]['Quarter'])][
                f'Sum of Fin {sum_trx_type} {trx_type}']

            if not previous_year_value.empty:
                previous_year_value = previous_year_value.values[0]
                growth_val = (((current_value - previous_year_value) / previous_year_value) * 100).round(2)
                df.at[i, '%YoY'] = growth_val
    return df


def calculate_quarter_to_quarter(df: pd.DataFrame, first_year: int, sum_trx_type: str, trx_type: str):
    for i in range(len(df)):
        if df.iloc[i]['Year'] > first_year:
            current_value = df.iloc[i][f'Sum of Fin {sum_trx_type} {trx_type}']
            previous_year_value = df.iloc[i - 1][f'Sum of Fin {sum_trx_type} {trx_type}']
            if not previous_year_value is None:
                growth_val = (((current_value - previous_year_value) / previous_year_value) * 100).round(2)
                df.at[i, '%QtQ'] = growth_val
    return df


def calculate_month_to_month(df_original: pd.DataFrame, first_year: int, sum_trx_type: str, trx_type: str):
    df = df_original.copy()
    df['Month'] = df['Month'].apply(lambda x: list(calendar.month_name).index(x))

    for i in range(len(df)):
        if df.iloc[i]['Year'] > first_year or (df.iloc[i]['Year'] == first_year and df.iloc[i]['Month'] > 1):
            current_value = df.iloc[i][f'Sum of Fin {sum_trx_type} {trx_type}']
            previous_month_value = df[(df['Year'] == df.iloc[i]['Year']) & (df['Month'] == df.iloc[i]['Month'] - 1)]

            if previous_month_value.empty:
                previous_month_value = df[(df['Year'] == df.iloc[i]['Year'] - 1) & (df['Month'] == 12)]

            if not previous_month_value.empty:
                previous_month_value = previous_month_value[f'Sum of Fin {sum_trx_type} {trx_type}'].values[0]

                if previous_month_value == 0 or np.isnan(previous_month_value):
                    growth_val = np.nan
                else:
                    growth_val = (((current_value - previous_month_value) / previous_month_value) * 100).round(2)

                df.at[i, '%MtM'] = growth_val

    df['Month'] = df['Month'].apply(lambda x: calendar.month_name[x])
    return df


def merge_df_growth(left_df, right_df, is_month: bool = False):
    if not is_month:
        df_combined = pd.merge(left_df, right_df, "inner", on=['Year', 'Quarter'])
        df_combined.rename(columns={"%YoY_x": "%YoY Jumlah", "%QtQ_x": "%QtQ Jumlah",
                                    "%YoY_y": "%YoY Nom", "%QtQ_y": "%QtQ Nom"}, inplace=True)
    else:
        df_combined = pd.merge(left_df, right_df, "inner", on=['Year', 'Month'])
        df_combined.rename(columns={"%MtM_x": "%MtM Jumlah", "%MtM_y": "%MtM Nom"}, inplace=True)
    return df_combined

def compile_data_profile(df: pd.DataFrame, df_national: pd.DataFrame, sum_trx_type: str, trx_type: str) -> pd.DataFrame:
    if len(df_national) <= 0:
        return pd.DataFrame()
    data_pjp = df[f'Sum of Fin {sum_trx_type} {trx_type}'].values[0]
    if sum_trx_type == "Jumlah":
        sum_trx_word = "Frekuensi"
        national_word = "Frek"
    else:
        sum_trx_word = "Nominal Rp Miliar"
        national_word = "Nom"
        data_pjp = (data_pjp / 1_000_000_000).round(2)

    if trx_type == "Inc":
        trx_word = "Incoming"
    elif trx_type == "Out":
        trx_word = "Outgoing"
    else:
        trx_word = "Domestik"

    data_national = df_national[f'{national_word} Nasional {trx_type}'].values[0]
    data_percentage = ((data_pjp / data_national) * 100).round(2)

    data = {
        "Transaction Type": ["Trx Perusahaan", "Trx Nasional", "Persentase (%)"],
        f"{trx_word} ({sum_trx_word})": [data_pjp, data_national, data_percentage],
    }

    return pd.DataFrame(data)

def compile_data_market_share(df: pd.DataFrame, df_national: pd.DataFrame, trx_type: str, df_inc: pd.DataFrame = None,
                              df_out: pd.DataFrame = None, df_dom: pd.DataFrame = None) -> pd.DataFrame:
    if trx_type == "Inc":
        trx_word = "Incoming"
    elif trx_type == "Out":
        trx_word = "Outgoing"
    elif trx_type == "Dom":
        trx_word = "Domestik"
    else:
        trx_word = "Total"

    if trx_type == "Total":
        nominal_jkt = df_inc['Nominal (dalam triliun)'].values[0] + df_out['Nominal (dalam triliun)'].values[0] + \
                      df_dom['Nominal (dalam triliun)'].values[0]
        frek_jkt = df_inc['Frekuensi (dalam jutaan)'].values[0] + df_out['Frekuensi (dalam jutaan)'].values[0] + \
                   df_dom['Frekuensi (dalam jutaan)'].values[0]
        nominal_nasional = df_inc['Nominal (dalam triliun)'].values[1] + df_out['Nominal (dalam triliun)'].values[1] + \
                           df_dom['Nominal (dalam triliun)'].values[1]
        frek_nasional = df_inc['Frekuensi (dalam jutaan)'].values[1] + df_out['Frekuensi (dalam jutaan)'].values[1] + \
                        df_dom['Frekuensi (dalam jutaan)'].values[1]
    else:
        # sums return Python/numpy scalars; use built-in round() to avoid AttributeError on float
        nominal_jkt = round(df[f'Sum of Fin Nilai {trx_type}'].sum() / 1_000_000_000_000, 2)
        frek_jkt = round(df[f'Sum of Fin Jumlah {trx_type}'].sum() / 1_000_000, 2)
        nominal_nasional = round(df_national[f'Nom Nasional {trx_type}'].sum() / 1_000, 2)
        frek_nasional = round(df_national[f'Frek Nasional {trx_type}'].sum() / 1_000_000, 2)

    data = {
        f"Transaksi {trx_word}": ['Jakarta', 'Nasional', 'Market Share (%)'],
    "Nominal (dalam triliun)": [nominal_jkt, nominal_nasional,
                    round(((nominal_jkt / nominal_nasional) * 100), 2) if nominal_nasional else None],
    "Frekuensi (dalam jutaan)": [frek_jkt, frek_nasional,
                     round(((frek_jkt / frek_nasional) * 100), 2) if frek_nasional else None],
    }
    df_out = pd.DataFrame(data)
    return df_out

def process_data_profile_month(df_month: pd.DataFrame, trx_type: str) -> pd.DataFrame:
    df_domestic_month = df_month[['Year', 'Month', f'Sum of Fin Jumlah {trx_type}', f'Sum of Fin Nilai {trx_type}']].copy()
    df_domestic_month[f'Sum of Fin Nilai {trx_type}'] = df_domestic_month[f'Sum of Fin Nilai {trx_type}'] / 1_000_000_000
    return df_domestic_month

def process_grand_total_profile(df: pd.DataFrame, trx_type: str) -> pd.DataFrame:
    grand_total_jumlah_month = df[f'Sum of Fin Jumlah {trx_type}'].sum()
    grand_total_nilai_month = df[f'Sum of Fin Nilai {trx_type}'].sum()
    df_grand_total_month = pd.DataFrame({
        f'Grand Total Jumlah {trx_type}': [grand_total_jumlah_month],
        f'Grand Total Nilai {trx_type}': [grand_total_nilai_month]
    })
    return df_grand_total_month

def add_quarter_column(df: pd.DataFrame) -> pd.DataFrame:
    df['Quarter'] = (df['Month'] - 1) // 3 + 1
    return df

def rename_format_growth_df(df: pd.DataFrame, trx_type: str):
    if trx_type == "Inc":
        trx_var = "Incoming"
    elif trx_type == "Out":
        trx_var = "Outgoing"
    elif trx_type == "Dom":
        trx_var = "Domestik"
    else:
        trx_var = "Total"

    df.rename(columns={
        f"Sum of Fin Jumlah {trx_type}": f"Total Frekuensi {trx_var}",
        f"Sum of Fin Nilai {trx_type}": f"Total Nominal {trx_var}",
        "%YoY Jumlah": "Year-on-Year Frekuensi",
        "%QtQ Jumlah": "Quarter-to-Quarter Frekuensi",
        "%YoY Nom": "Year-on-Year Nominal",
        "%QtQ Nom": "Quarter-to-Quarter Nominal",
    }, inplace=True)

    df = df.style.format(
        {
            "Year": lambda x: "{:.0f}".format(x),
            f"Total Frekuensi {trx_var}": lambda x: '{:,.0f}'.format(x),
            f"Total Nominal {trx_var}": lambda x: '{:,.0f}'.format(x),
            "Year-on-Year Frekuensi": lambda x: '{:,.2f} %'.format(x),
            "Quarter-to-Quarter Frekuensi": lambda x: '{:,.2f} %'.format(x),
            "Year-on-Year Nominal": lambda x: '{:,.2f} %'.format(x),
            "Quarter-to-Quarter Nominal": lambda x: '{:,.2f} %'.format(x),
        },
        thousands=".",
        decimal=",",
    )
    return df

def rename_format_growth_monthly_df(df: pd.DataFrame, trx_type: str):
    if trx_type == "Inc":
        trx_var = "Incoming"
    elif trx_type == "Out":
        trx_var = "Outgoing"
    elif trx_type == "Dom":
        trx_var = "Domestik"
    else:
        trx_var = "Total"

    df.rename(columns={
        f"Sum of Fin Jumlah {trx_type}": f"Total Frekuensi {trx_var}",
        f"Sum of Fin Nilai {trx_type}": f"Total Nominal {trx_var}",
        "%MtM Jumlah": "Month-to-Month Frekuensi",
        "%MtM Nom": "Month-to-Month Nominal",
    }, inplace=True)

    df = df.style.format(
        {
            "Year": lambda x: "{:.0f}".format(x),
            f"Total Frekuensi {trx_var}": lambda x: '{:,.0f}'.format(x),
            f"Total Nominal {trx_var}": lambda x: '{:,.0f}'.format(x),
            "Month-to-Month Frekuensi": lambda x: '{:,.2f} %'.format(x),
            "Month-to-Month Nominal": lambda x: '{:,.2f} %'.format(x),
        },
        thousands=".",
        decimal=",",
    )
    return df

def format_profile_df(df: pd.DataFrame, is_market_share: bool = False):
    df.iloc[:2] = df.iloc[:2].applymap(lambda x: f"{x:,.2f}".replace(",", ".") if isinstance(x, (int, float)) else x)
    df.iloc[-1:] = df.iloc[-1:].applymap(lambda x: f"{x:,.2f} %".replace(".", ",") if isinstance(x, (int, float)) else x)
    df = df.style.format(
        thousands=".",
        decimal=",",
    )
    return df


def rename_format_profile_df(df: pd.DataFrame, trx_type: str):
    if trx_type == "Inc":
        trx_var = "Incoming"
    elif trx_type == "Out":
        trx_var = "Outgoing"
    else:
        trx_var = "Domestik"

    df.rename(columns={
        f"Sum of Fin Jumlah {trx_type}": f"Total Frekuensi {trx_var}",
        f"Sum of Fin Nilai {trx_type}": f"Total Nominal {trx_var} (Miliar)",
    }, inplace=True)

    df = df.style.format(
        {
            "Year": lambda x: "{:.0f}".format(x),
            f"Total Frekuensi {trx_var}": lambda x: '{:,.0f}'.format(x),
            f"Total Nominal {trx_var} (Miliar)": lambda x: '{:,.0f}'.format(x),
        },
        thousands=".",
        decimal=",",
    )
    return df

def format_profile_df_grand_total(df: pd.DataFrame, trx_type: str):
    if trx_type == "Inc":
        trx_var = "Incoming"
    elif trx_type == "Out":
        trx_var = "Outgoing"
    else:
        trx_var = "Domestik"

    df.rename(columns={
        f"Grand Total Jumlah {trx_type}": f"Grand Total Frekuensi {trx_var}",
        f"Grand Total Nilai {trx_type}": f"Grand Total Nominal {trx_var} (Miliar)",
    }, inplace=True)

    df = df.style.format(
        {
            f"Grand Total Frekuensi {trx_var}": lambda x: '{:,.0f}'.format(x),
            f"Grand Total Nominal {trx_var} (Miliar)": lambda x: '{:,.0f}'.format(x),
        },
        thousands=".",
        decimal=",",
    )
    return df