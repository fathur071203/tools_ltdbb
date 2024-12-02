from datetime import datetime

import streamlit as st
from supabase import create_client


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
    transformed_data = []
    for province in response.data:
        country_ref = province['country_reference']
        province_entry = {
            "code": province['code'],
            "name": province['name'],
            "country_reference": country_ref['name']
        }
        transformed_data.append(province_entry)
    return transformed_data


def get_country_ref(_db):
    response = _db.table("country_reference").select("code, name").execute()
    return response.data


def get_sus_peoples(_db):
    response = _db.table("suspicious_person").select("name").execute()
    return response.data


def get_sus_city(_db, is_sus: bool):
    response = _db.table("city_reference").select("code, name, province_reference(name)").eq("is_suspicious",
                                                                                             is_sus).execute()
    transformed_data = []
    for cities in response.data:
        prov_ref = cities['province_reference']
        city_entry = {
            "code": cities['code'],
            "name": cities['name'],
            "province_reference": prov_ref['name']
        }
        transformed_data.append(city_entry)
    return transformed_data


def get_sus_prov(_db, is_sus: bool):
    response = _db.table("province_reference").select("code, name, country_reference(name)").eq("is_suspicious",
                                                                                                is_sus).execute()
    transformed_data = []
    for prov in response.data:
        country_ref = prov['country_reference']
        prov_entry = {
            "code": prov['code'],
            "name": prov['name'],
            "country_reference": country_ref['name']
        }
        transformed_data.append(prov_entry)
    return transformed_data


def get_blacklisted_country(_db, is_blacklisted: bool):
    response = _db.table("country_reference").select("code, name").eq("is_blacklisted", is_blacklisted).execute()
    return response.data


def get_greylisted_country(_db, is_greylisted: bool):
    response = _db.table("country_reference").select("code, name").eq("is_greylisted", is_greylisted).execute()
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


def transform_prov_name_to_prov_code(list_provinces, city_province):
    prov_code = None
    for prov in list_provinces:
        if prov['name'] == city_province:
            prov_code = prov['code']
            break
    return prov_code


def insert_new_pjp(_db, pjp_code: str, pjp_name: str, pjp_second_name: str, pjp_pt_name: str):
    request_insert_pjp = _db.table("pjp_reference").insert(
        {"code": pjp_code,
         "name": pjp_name,
         "second_name": pjp_second_name,
         "pt_name": pjp_pt_name}).execute()
    return request_insert_pjp


def insert_new_city(_db, city_code: str, city_name: str, prov_code: str):
    request_insert_city = _db.table("city_reference").insert(
        {"code": city_code,
         "name": city_name,
         "province_code": prov_code}
    ).execute()
    return request_insert_city


def insert_new_province(_db, prov_code: str, prov_name: str, country_code: str):
    request_insert_prov = _db.table("province_reference").insert(
        {"code": prov_code,
         "name": prov_name,
         "country_code": country_code}
    ).execute()
    return request_insert_prov


def insert_new_country(_db, country_code: str, country_name: str):
    request_insert_country = _db.table("country_reference").insert(
        {"code": country_code,
         "name": country_name}
    ).execute()
    return request_insert_country


def insert_new_sus_person(_db, person_name: str):
    request_insert_sus = _db.table("suspicious_person").insert(
        {"name": person_name}
    ).execute()
    return request_insert_sus


def update_sus_city(_db, city_code: str, is_sus: bool):
    request = _db.table("city_reference").update(
        {"is_suspicious": is_sus},
    ).eq("code", city_code).execute()
    return request


def update_sus_prov(_db, prov_code: str, is_sus: bool):
    request = _db.table("province_reference").update(
        {"is_suspicious": is_sus},
    ).eq("code", prov_code).execute()
    return request


def update_blacklisted_country(_db, country_code: str, is_blacklisted: bool):
    request = _db.table("country_reference").update(
        {"is_blacklisted": is_blacklisted},
    ).eq("code", country_code).execute()
    return request


def update_greylisted_country(_db, country_code: str, is_greylisted: bool):
    request = _db.table("country_reference").update(
        {"is_greylisted": is_greylisted},
    ).eq("code", country_code).execute()
    return request


def update_pjp(_db, pjp_code_src: str, pjp_code: str, pjp_name: str, pjp_second_name: str, pjp_pt_name: str):
    updated_at = datetime.now().isoformat()
    request_update_pjp = _db.table("pjp_reference").update(
        {"code": pjp_code, "name": pjp_name, "second_name": pjp_second_name, "pt_name": pjp_pt_name,
         "updated_at": updated_at}
    ).eq("code", pjp_code_src).execute()
    return request_update_pjp


def update_city(_db, city_code_src: str, city_code: str, city_name: str, prov_code: str):
    updated_at = datetime.now().isoformat()
    request_update_city = _db.table("city_reference").update(
        {
            "code": city_code,
            "name": city_name,
            "province_code": prov_code,
            "updated_at": updated_at
        }
    ).eq("code", city_code_src).execute()
    return request_update_city


def update_province(_db, prov_code_src: str, prov_code: str, prov_name: str, country_code: str):
    updated_at = datetime.now().isoformat()
    request_update_prov = _db.table("province_reference").update(
        {
            "code": prov_code,
            "name": prov_name,
            "country_code": country_code,
            "updated_at": updated_at
        }
    ).eq("code", prov_code_src).execute()
    return request_update_prov


def update_country(_db, country_code_src: str, country_code: str, country_name: str):
    updated_at = datetime.now().isoformat()
    request_update_country = _db.table("country_reference").update(
        {
            "code": country_code,
            "name": country_name,
            "updated_at": updated_at
        }
    ).eq("code", country_code_src).execute()
    return request_update_country


def update_sus_person(_db, name_src: str, name: str):
    updated_at = datetime.now().isoformat()
    request_update_sus = _db.table("suspicious_person").update(
        {"name": name,
         "updated_at": updated_at}
    ).eq("name", name_src).execute()
    return request_update_sus


def delete_pjp(_db, pjp_code: str):
    request_delete_pjp = _db.table("pjp_reference").delete().eq("code", pjp_code).execute()
    return request_delete_pjp


def delete_city(_db, city_code: str):
    request_delete_city = _db.table("city_reference").delete().eq("code", city_code).execute()
    return request_delete_city


def delete_province(_db, prov_code: str):
    request_delete_prov = _db.table("province_reference").delete().eq("code", prov_code).execute()
    return request_delete_prov


def delete_country(_db, country_code: str):
    request_delete_country = _db.table("country_reference").delete().eq("code", country_code).execute()
    return request_delete_country


def delete_person(_db, person_name: str):
    request_delete_person = _db.table("suspicious_person").delete().eq("name", person_name).execute()
    return request_delete_person
