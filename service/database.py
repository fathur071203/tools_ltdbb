from datetime import datetime

import streamlit as st
import pandas as pd
from supabase import create_client, Client


@st.cache_resource
def connect_db():
    url = st.secrets.connections.supabase["SUPABASE_URL"]
    key = st.secrets.connections.supabase["SUPABASE_KEY"]
    return create_client(url, key)


def get_pjp_jkt(_db):
    response = _db.table("pjp_reference").select("code, name, second_name, pt_name").execute()
    return response.data

def get_city_ref(_db):
    response = _db.table("city_reference").select("code, name, province_reference(name)").execute()
    transformed_data = []
    for city in response.data:
        province_ref = city['province_reference']
        city_entry = {
            "code": city['code'],
            "name": city['name'],
            "province_reference": province_ref['name']
        }
        transformed_data.append(city_entry)
    return transformed_data

def get_province_ref(_db):
    response = _db.table("province_reference").select("code, name, country_reference(name)").execute()
    return response.data

def transform_options_province(list_province):
    transformed_data = []
    for prov in list_province:
        transformed_data.append(prov['name'])
    transformed_data = sorted(transformed_data)
    return transformed_data

def get_index_options_province(options_provice, prov_name):
    for index, prov in enumerate(options_provice):
        if prov == prov_name:
            return index

def insert_new_pjp(_db, pjp_code: str, pjp_name: str, pjp_second_name: str, pjp_pt_name: str):
    request = _db.table("pjp_reference").insert(
        {"code": pjp_code,
         "name": pjp_name,
         "second_name": pjp_second_name,
         "pt_name": pjp_pt_name}).execute()
    return request

def transform_prov_name_to_prov_code(list_provinces, city_province):
    prov_code = None
    for prov in list_provinces:
        if prov['name'] == city_province:
            prov_code = prov['code']
            break
    return prov_code

def insert_new_city(_db, city_code: str, city_name: str, prov_code: str):
    request = _db.table("city_reference").insert(
        {"code": city_code,
         "name": city_name,
         "province_code": prov_code}
    ).execute()
    return request

def update_pjp(_db, pjp_code_src: str, pjp_code: str, pjp_name: str, pjp_second_name: str, pjp_pt_name: str):
    updated_at = datetime.now().isoformat()
    request = _db.table("pjp_reference").update(
        {"code": pjp_code, "name": pjp_name, "second_name": pjp_second_name, "pt_name": pjp_pt_name,
         "updated_at": updated_at}
    ).eq("code", pjp_code_src).execute()
    return request

def update_city(_db, city_code_src: str, city_code: str, city_name: str, prov_code: str):
    updated_at = datetime.now().isoformat()
    request = _db.table("city_reference").update(
        {
            "code": city_code,
            "name": city_name,
            "province_code": prov_code,
            "updated_at": updated_at
        }
    ).eq("code", city_code_src).execute()
    return request

def delete_pjp(_db, pjp_code: str):
    request = _db.table("pjp_reference").delete().eq("code", pjp_code).execute()
    return request

def delete_city(_db, city_code: str):
    request = _db.table("city_reference").delete().eq("code", city_code).execute()
    return request