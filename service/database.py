import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def connect_db():
    url = st.secrets.connections.supabase["SUPABASE_URL"]
    key = st.secrets.connections.supabase["SUPABASE_KEY"]
    return create_client(url, key)

@st.cache_data
def get_provinces(_db):
    response = _db.table("province_reference").select("*").execute()
    return response.data
