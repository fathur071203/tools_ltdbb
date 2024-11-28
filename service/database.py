import streamlit as st
import pandas as pd
from supabase import create_client, Client

@st.cache_resource
def connect_db():
    url = st.secrets.connections.supabase["SUPABASE_URL"]
    key = st.secrets.connections.supabase["SUPABASE_KEY"]
    return create_client(url, key)

@st.cache_data(ttl=600)
def get_pjp_jkt(_db):
    response = _db.table("pjp_reference").select("code, name, second_name, pt_name").execute()
    return response.data
