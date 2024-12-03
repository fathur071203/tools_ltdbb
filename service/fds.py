import streamlit as st
import pandas as pd
import joblib
import os
import io

@st.cache_resource
def load_models(folder_path="./models"):
    models = {}
    for filename in os.listdir(folder_path):
        if filename.endswith(".joblib"):
            filepath = os.path.join(folder_path, filename)
            models[filename] = joblib.load(filepath)
    return models

@st.cache_data
def read_parquets(uploaded_file) -> pd.DataFrame:
    dataframes = []
    for files in uploaded_file:
        if files.name.endswith(".parquet"):
            df = pd.read_parquet(io.BytesIO(files.read()))
            dataframes.append(df)
    combined_df = pd.concat(dataframes, ignore_index=True)
    return combined_df

def read_excel(uploaded_file) -> pd.DataFrame:
    excel_data = pd.read_excel(uploaded_file, sheet_name=None)
    combined_df = pd.concat(excel_data.values(), ignore_index=True)
    return combined_df

def get_unique_tujuan(df) -> pd.DataFrame:
    unique_values = df['TUJUAN'].unique()
    return unique_values

def get_ml_model(tipe_trx: str, models: dict):
    tipe_trx = tipe_trx.lower()[:3]
    list_models = []
    for key in models.keys():
        if tipe_trx in key:
            list_models.append(models.get(key))
    return list_models

def check_df_null(df):
    col_na = df.isnull().sum().sort_values(ascending=True)
    percent = col_na / len(df)
    missing_data = pd.concat([col_na, percent], axis=1, keys=['Total', 'Percent'])

    if missing_data[missing_data['Total'] > 0].shape[0] == 0:
        print("Tidak ditemukan missing value pada dataset")
    else:
        print(missing_data[missing_data['Total'] > 0])

def split_df(df: pd.DataFrame, tipe_trx: str):
    if tipe_trx == "Outgoing":
        col = 'TUJUAN'
    else:
        col = 'TUJUAN_TRX'
    unique_values = df[col].unique()
    df_split = {}

    for value in unique_values:
        df_split[value] = df[df[col] == value]
    return df_split

def get_pjp_suspected_blacklisted_greylisted(df, list_pjp):
    pjp_dict = {pjp['code']: pjp['name'] for pjp in list_pjp}
    list_pjp_name = df['SANDI_PELAPOR'].apply(lambda code: pjp_dict.get(code, None)).dropna().tolist()
    return list_pjp_name


