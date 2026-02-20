from datetime import datetime
from typing import Any, Callable, TypeVar

import streamlit as st
import pandas as pd
import json
import io
from streamlit_js_eval import streamlit_js_eval
import time

import httpcore
import httpx

from supabase import create_client


T = TypeVar("T")

_DB_LAST_ERROR_KEY = "_tools_ltdbb_db_last_error"


def _is_transient_network_error(exc: Exception) -> bool:
    return isinstance(exc, (httpx.HTTPError, httpcore.HTTPError, OSError, TimeoutError))


def _store_db_error_once(exc: Exception, context: str) -> None:
    if _DB_LAST_ERROR_KEY in st.session_state:
        return
    st.session_state[_DB_LAST_ERROR_KEY] = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "context": context,
        "error": repr(exc),
    }


def show_db_error_banner(clear: bool = True) -> None:
    """Render a friendly DB connection error message if one was captured."""
    err = st.session_state.get(_DB_LAST_ERROR_KEY)
    if not err:
        return

    st.error(
        "Koneksi database bermasalah (Supabase/PostgREST). "
        "Beberapa fitur mungkin tidak tersedia sampai koneksi pulih."
    )
    with st.expander("Detail error"):
        st.code(f"{err['time']} - {err['context']}\n{err['error']}")

    if clear:
        st.session_state.pop(_DB_LAST_ERROR_KEY, None)


def connect_db_safe():
    """Return Supabase client or None; never raises.

    Streamlit pages run top-level code on every rerun; failing fast here keeps
    the app usable when the DB is temporarily unreachable or secrets are missing.
    """
    try:
        return connect_db()
    except Exception as exc:
        _store_db_error_once(exc, context="connect_db")
        return None


def _safe_postgrest_data(
    query_fn: Callable[[], Any],
    *,
    default: T,
    context: str,
    attempts: int = 3,
    initial_delay_s: float = 0.6,
) -> T:
    """Execute a PostgREST/Supabase query with retries for transient network errors."""
    delay_s = initial_delay_s
    last_exc: Exception | None = None

    for attempt in range(1, max(1, attempts) + 1):
        try:
            resp = query_fn().execute()
            return getattr(resp, "data", default)
        except Exception as exc:
            last_exc = exc
            if not _is_transient_network_error(exc):
                raise
            if attempt < attempts:
                time.sleep(delay_s)
                delay_s = min(delay_s * 2, 5.0)
            else:
                _store_db_error_once(exc, context)
                return default

    if last_exc is not None:
        _store_db_error_once(last_exc, context)
    return default


@st.cache_resource
def connect_db():
    url = st.secrets.connections.supabase["SUPABASE_URL"]
    key = st.secrets.connections.supabase["SUPABASE_KEY"]
    return create_client(url, key)

def get_user_logs_data(_db):
    return _safe_postgrest_data(
        lambda: _db.table("user_logs").select("data").eq("username", "Rakan"),
        default=[],
        context="SELECT user_logs (username=Rakan)",
    )


def get_pjp_jkt(_db):
    return _safe_postgrest_data(
        lambda: _db.table("pjp_reference").select("code, name, second_name, pt_name"),
        default=[],
        context="SELECT pjp_reference", 
    )


def get_city_ref(_db):
    response_data = _safe_postgrest_data(
        lambda: _db.table("city_reference").select("code, name, province_reference(name)"),
        default=[],
        context="SELECT city_reference", 
    )
    transformed_data = []
    for city in response_data:
        province_ref = city['province_reference']
        city_entry = {
            "code": city['code'],
            "name": city['name'],
            "province_reference": province_ref['name']
        }
        transformed_data.append(city_entry)
    return transformed_data


def get_province_ref(_db):
    response_data = _safe_postgrest_data(
        lambda: _db.table("province_reference").select("code, name, country_reference(name)"),
        default=[],
        context="SELECT province_reference",
    )
    transformed_data = []
    for province in response_data:
        country_ref = province['country_reference']
        province_entry = {
            "code": province['code'],
            "name": province['name'],
            "country_reference": country_ref['name']
        }
        transformed_data.append(province_entry)
    return transformed_data


def get_country_ref(_db):
    return _safe_postgrest_data(
        lambda: _db.table("country_reference").select("code, name"),
        default=[],
        context="SELECT country_reference",
    )


def get_sus_peoples(_db):
    return _safe_postgrest_data(
        lambda: _db.table("suspicious_person").select("name"),
        default=[],
        context="SELECT suspicious_person",
    )


def get_sus_city(_db, is_sus: bool):
    response_data = _safe_postgrest_data(
        lambda: _db.table("city_reference")
        .select("code, name, province_reference(name)")
        .eq("is_suspicious", is_sus),
        default=[],
        context=f"SELECT city_reference (is_suspicious={is_sus})",
    )
    transformed_data = []
    for cities in response_data:
        prov_ref = cities['province_reference']
        city_entry = {
            "code": cities['code'],
            "name": cities['name'],
            "province_reference": prov_ref['name']
        }
        transformed_data.append(city_entry)
    return transformed_data


def get_sus_prov(_db, is_sus: bool):
    response_data = _safe_postgrest_data(
        lambda: _db.table("province_reference")
        .select("code, name, country_reference(name)")
        .eq("is_suspicious", is_sus),
        default=[],
        context=f"SELECT province_reference (is_suspicious={is_sus})",
    )
    transformed_data = []
    for prov in response_data:
        country_ref = prov['country_reference']
        prov_entry = {
            "code": prov['code'],
            "name": prov['name'],
            "country_reference": country_ref['name']
        }
        transformed_data.append(prov_entry)
    return transformed_data


def get_blacklisted_country(_db, is_blacklisted: bool):
    return _safe_postgrest_data(
        lambda: _db.table("country_reference")
        .select("code, name")
        .eq("is_blacklisted", is_blacklisted),
        default=[],
        context=f"SELECT country_reference (is_blacklisted={is_blacklisted})",
    )


def get_greylisted_country(_db, is_greylisted: bool):
    return _safe_postgrest_data(
        lambda: _db.table("country_reference")
        .select("code, name")
        .eq("is_greylisted", is_greylisted),
        default=[],
        context=f"SELECT country_reference (is_greylisted={is_greylisted})",
    )


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


def upload_df(_db, username: str, df: pd.DataFrame):
    json_data = df.to_json(orient="records")
    file_metadata = {
        "file_name": "uploaded_data.json",
        "json_data": json_data
    }


def get_country_participated(_db, list_countries_code):
    list_countries = []
    for code in list_countries_code:
        rows = _safe_postgrest_data(
            lambda: _db.table("country_reference").select("code, name").eq("code", code),
            default=[],
            context=f"SELECT country_reference (code={code})",
        )
        for country in rows:
            list_countries.append({
                "code": country.get('code'),
                "name": country.get('name'),
            })
    return list_countries


@st.dialog("Konfirmasi Data Baru")
def submit_add_pjp(db, pjp_code, pjp_name, pjp_second_name, pjp_pt_name):
    st.write(f"Apakah Anda yakin ingin menambahkan data baru ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            request = insert_new_pjp(db, pjp_code, pjp_name, pjp_second_name, pjp_pt_name)
            if request.data is not None:
                st.success("Data PJP Baru telah berhasil disimpan!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            if 'duplicate key value violates unique constraint' in str(e):
                st.error(
                    "Terdapat Error dalam memasukkan PJP baru ke Database: Kode PJP yang sama sudah tersimpan pada database")
            else:
                st.error(f"Terdapat Error dalam memasukkan PJP baru ke Database: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Data Baru")
def submit_add_city(db, city_code, city_name, list_provinces, city_province):
    st.write(f"Apakah Anda yakin ingin menambahkan data baru ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            prov_code = transform_prov_name_to_prov_code(list_provinces, city_province)
            request = insert_new_city(db, city_code, city_name, prov_code)
            if request.data is not None:
                st.success("Data Kota Baru telah berhasil disimpan!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            if 'duplicate key value violates unique constraint' in str(e):
                st.error(
                    "Terdapat Error dalam memasukkan Kota baru ke Database: Kode Kota yang sama sudah tersimpan pada database")
            else:
                st.error(f"Terdapat Error dalam memasukkan Kota baru ke Database: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Data Baru")
def submit_add_prov(db, prov_code, prov_name):
    st.write(f"Apakah Anda yakin ingin menambahkan data baru ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            country_code = "ID"
            request = insert_new_province(db, prov_code, prov_name, country_code)
            if request.data is not None:
                st.success("Data Provinsi Baru telah berhasil disimpan!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            if 'duplicate key value violates unique constraint' in str(e):
                st.error(
                    "Terdapat Error dalam memasukkan Provinsi baru ke Database: Kode Provinsi yang sama sudah tersimpan pada database")
            else:
                st.error(f"Terdapat Error dalam memasukkan Provinsi baru ke Database: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Data Baru")
def submit_add_country(db, country_code, country_name):
    st.write(f"Apakah Anda yakin ingin menambahkan data baru ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            request = insert_new_country(db, country_code, country_name)
            if request.data is not None:
                st.success("Data Negara Baru telah berhasil disimpan!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            if 'duplicate key value violates unique constraint' in str(e):
                st.error(
                    "Terdapat Error dalam memasukkan Negara baru ke Database: Kode Negara yang sama sudah tersimpan pada database")
            else:
                st.error(f"Terdapat Error dalam memasukkan Negara baru ke Database: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Data Baru")
def submit_add_sus_person(db, person_name_input):
    st.write(f"Apakah Anda yakin ingin menambahkan data baru ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            request = insert_new_sus_person(db, person_name_input)
            if request.data is not None:
                st.success("Data Orang Tersangka Baru telah berhasil disimpan!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            if 'duplicate key value violates unique constraint' in str(e):
                st.error(
                    "Terdapat Error dalam memasukkan Nama Tersangka baru ke Database: Nama yang sama sudah tersimpan pada database")
            else:
                st.error(f"Terdapat Error dalam memasukkan Data Orang Tersangka baru ke Database: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Data Baru")
def submit_add_blacklisted_country(db, selected_blacklisted_country, is_blacklisted):
    st.write(f"Apakah Anda yakin ingin menambahkan data baru ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            selected_code_blacklisted_country = selected_blacklisted_country.split('-')[0]
            request = update_blacklisted_country(db, selected_code_blacklisted_country, is_blacklisted)
            if request.data is not None:
                st.success("Data Negara Blacklisted Baru telah berhasil disimpan!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            st.error(f"Terdapat Error dalam memasukkan Data Negara Blacklisted Baru ke Database: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Data Baru")
def submit_add_greylisted_country(db, selected_greylisted_country, is_greylisted):
    st.write(f"Apakah Anda yakin ingin menambahkan data baru ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            selected_code_greylisted_country = selected_greylisted_country.split('-')[0]
            request = update_greylisted_country(db, selected_code_greylisted_country, is_greylisted)
            if request.data is not None:
                st.success("Data Negara Greylist Baru telah berhasil disimpan!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            st.error(f"Terdapat Error dalam memasukkan Data Negara Greylist Baru ke Database: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Perubahan Data")
def submit_update_sus_person(db, selected_person_update, update_person_name):
    st.write(f"Apakah Anda yakin ingin mengubah data ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            request = update_sus_person(db, selected_person_update, update_person_name)
            if request.data is not None:
                st.success("Data Nama Tersangka telah berhasil diubah!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            if 'duplicate key value violates unique constraint' in str(e):
                st.error(
                    "Terdapat Error dalam mengupdate data Nama Tersangka: Nama yang sama sudah tersimpan pada database")
            else:
                st.error(f"Terdapat Error dalam mengupdate data Nama Tersangka: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Perubahan Data")
def submit_update_pjp(db, selected_code, update_code_pjp, update_name_pjp,
                      update_second_name_pjp,
                      update_pt_name_pjp):
    st.write(f"Apakah Anda yakin ingin mengubah data ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            request = update_pjp(db, selected_code, update_code_pjp, update_name_pjp,
                                 update_second_name_pjp,
                                 update_pt_name_pjp)
            if request.data is not None:
                st.success("Data PJP telah berhasil diubah!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            if 'duplicate key value violates unique constraint' in str(e):
                st.error(
                    "Terdapat Error dalam mengupdate data PJP: Kode PJP yang sama sudah tersimpan pada database")
            else:
                st.error(f"Terdapat Error dalam mengupdate data PJP: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Perubahan Data")
def submit_update_city(db, selected_city_code, update_city_code, update_city_name, list_provinces,
                       update_city_province):
    st.write(f"Apakah Anda yakin ingin mengubah data ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            prov_code = transform_prov_name_to_prov_code(list_provinces, update_city_province)
            request = update_city(db, selected_city_code, update_city_code, update_city_name, prov_code)
            if request.data is not None:
                st.success("Data Kota telah berhasil diubah!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            if 'duplicate key value violates unique constraint' in str(e):
                st.error(
                    "Terdapat Error dalam mengupdate data Kota: Kode Kota yang sama sudah tersimpan pada database")
            else:
                st.error(f"Terdapat Error dalam mengupdate data Kota: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Perubahan Data")
def submit_update_prov(db, selected_prov_code, update_prov_code, update_prov_name):
    st.write(f"Apakah Anda yakin ingin mengubah data ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            country_code = "ID"
            request = update_province(db, selected_prov_code, update_prov_code, update_prov_name,
                                      country_code)
            if request.data is not None:
                st.success("Data Provinsi telah berhasil diubah!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            if 'duplicate key value violates unique constraint' in str(e):
                st.error(
                    "Terdapat Error dalam mengupdate data Provinsi: Kode Provinsi yang sama sudah tersimpan pada database")
            else:
                st.error(f"Terdapat Error dalam mengupdate data Provinsi: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Perubahan Data")
def submit_update_country(db, selected_country_code, update_country_code, update_country_name):
    st.write(f"Apakah Anda yakin ingin mengubah data ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            request = update_country(db, selected_country_code, update_country_code, update_country_name)
            if request.data is not None:
                st.success("Data Negara telah berhasil diubah!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            if 'duplicate key value violates unique constraint' in str(e):
                st.error(
                    "Terdapat Error dalam mengupdate data Negara: Kode Negara yang sama sudah tersimpan pada database")
            else:
                st.error(f"Terdapat Error dalam mengupdate data Negara: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Penghapusan Data")
def submit_delete_sus_person(db, selected_person_update):
    st.write(f"Apakah Anda yakin ingin menghapus data ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            request = delete_person(db, selected_person_update)
            if request.data is not None:
                st.success("Data Nama Tersangka telah berhasil dihapus!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            st.error(f"Terdapat Error dalam menghapus data Tersangka: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Penghapusan Data")
def submit_delete_pjp(db, selected_code):
    st.write(f"Apakah Anda yakin ingin menghapus data ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            request = delete_pjp(db, selected_code)
            if request.data is not None:
                st.success("Data PJP telah berhasil dihapus!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            st.error(f"Terdapat Error dalam menghapus data PJP: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Penghapusan Data")
def submit_delete_city(db, selected_city_code):
    st.write(f"Apakah Anda yakin ingin menghapus data ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            request = delete_city(db, selected_city_code)
            if request.data is not None:
                st.success("Data Kota telah berhasil dihapus!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            st.error(f"Terdapat Error dalam menghapus data Kota dari Database: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Penghapusan Data")
def submit_delete_prov(db, selected_prov_code):
    st.write(f"Apakah Anda yakin ingin menghapus data ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            request = delete_province(db, selected_prov_code)
            if request.data is not None:
                st.success("Data Provinsi telah berhasil dihapus!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            st.error(f"Terdapat Error dalam menghapus Provinsi dari Database: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Penghapusan Data")
def submit_delete_country(db, selected_country_code):
    st.write(f"Apakah Anda yakin ingin menghapus data ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            request = delete_country(db, selected_country_code)
            if request.data is not None:
                st.success("Data Negara telah berhasil dihapus!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            st.error(f"Terdapat Error dalam menghapus data Negara dari database: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Penghapusan Data")
def submit_delete_blacklisted_country(db, selected_delete_blacklisted_country, is_blacklisted):
    st.write(f"Apakah Anda yakin ingin menghapus data ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            selected_code_delete_blacklisted_country = selected_delete_blacklisted_country.split('-')[0]
            request = update_blacklisted_country(db, selected_code_delete_blacklisted_country, is_blacklisted)
            if request.data is not None:
                st.success("Data Negara Blacklisted telah berhasil dihapus!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            st.error(f"Terdapat Error dalam mengubah Data Negara Blacklisted: {e}")
    elif cancel_button:
        st.rerun()


@st.dialog("Konfirmasi Penghapusan Data")
def submit_delete_greylisted_country(db, selected_delete_greylisted_country, is_greylisted):
    st.write(f"Apakah Anda yakin ingin menghapus data ini?")
    col1, col2 = st.columns(2)
    with col1:
        confirm_button = st.button("Iya", use_container_width=True, type="primary")
    with col2:
        cancel_button = st.button("Batal", use_container_width=True, type="secondary")
    if confirm_button:
        try:
            selected_code_delete_greylisted_country = selected_delete_greylisted_country.split('-')[0]
            request = update_greylisted_country(db, selected_code_delete_greylisted_country, is_greylisted)
            if request.data is not None:
                st.success("Data Negara Greylist telah berhasil dihapus!")
                time.sleep(1.5)
                streamlit_js_eval(js_expressions="parent.window.location.reload()")
        except Exception as e:
            st.error(f"Terdapat Error dalam mengubah Data Negara Greylist: {e}")
    elif cancel_button:
        st.rerun()
