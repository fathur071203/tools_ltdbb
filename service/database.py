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


def inset_new_pjp(_db, pjp_code: str, pjp_name: str, pjp_second_name: str, pjp_pt_name: str):
    request = _db.table("pjp_reference").insert(
        {"code": pjp_code,
         "name": pjp_name,
         "second_name": pjp_second_name,
         "pt_name": pjp_pt_name}).execute()
    return request


def update_pjp(_db, pjp_code_src: str, pjp_code: str, pjp_name: str, pjp_second_name: str, pjp_pt_name: str):
    updated_at = datetime.now().isoformat()
    request = _db.table("pjp_reference").update(
        {"code": pjp_code, "name": pjp_name, "second_name": pjp_second_name, "pt_name": pjp_pt_name,
         "updated_at": updated_at}
    ).eq("code", pjp_code_src).execute()
    return request

def delete_pjp(_db, pjp_code: str):
    request = _db.table("pjp_reference").delete().eq("code", pjp_code).execute()
    return request