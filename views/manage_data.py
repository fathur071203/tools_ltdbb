import streamlit as st
from service.database import *
from service.preprocess import set_page_visuals
from streamlit_js_eval import streamlit_js_eval
import time


def get_selected_pjp(code: str, list_pjp_db):
    for pjp_db in list_pjp_db:
        if pjp_db["code"] == code:
            return pjp_db

def get_selected_city(code: str, list_city_db):
    for city_db in list_city_db:
        if city_db["code"] == code:
            return city_db

def get_selected_prov(code: str, list_prov_db):
    for prov_db in list_prov_db:
        if prov_db["code"] == code:
            return prov_db

# Initial Page Setup
set_page_visuals("dm")

db = connect_db()

st.markdown("### Kelola Data PJP")
list_pjp = get_pjp_jkt(db).copy()
df_pjp = st.data_editor(
    list_pjp,
    column_config={
        "code" : "Kode Penyelenggara",
        "name" : "Nama Penyelenggara",
        "second_name" : "Nama Penyelenggara 2",
        "pt_name" : "Nama Penyelenggara PT"
    },
    use_container_width=True,
    hide_index=False
)
col1, col2 = st.columns(2)
with col1:
    st.markdown("#### Tambah Data PJP Baru")
    with st.form(key='add_pjp_form', enter_to_submit=False, clear_on_submit=True):
        pjp_code = st.text_input("Kode PJP", key="pjp_code", help="Isian harus berupa angka")
        pjp_name = st.text_input("Nama PJP", key='pjp_name')
        pjp_second_name = st.text_input("Nama PJP Kedua", key='pjp_second_name', help="Nama kedua PJP (Jika ada)")
        pjp_pt_name = st.text_input("Nama PJP (dalam PT)", key='pjp_pt_name', help="Nama PJP dengan PT sebagai awalan")
        submitted_insert = st.form_submit_button("Submit", use_container_width=True, type="secondary")
        if submitted_insert:
            if not pjp_code or not pjp_name or not pjp_second_name or not pjp_pt_name:
                st.error("Semua field harus diisi!")
            elif pjp_code and not pjp_code.isdigit():
                st.warning("Kode PJP hanya angka yang diperbolehkan!")
            else:
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
with col2:
    st.markdown("#### Update Data PJP")
    list_name_pjp = []
    for pjp in list_pjp:
        list_name_pjp.append(f"{pjp['code']}-{pjp['name']}")
    selected_pjp_update = st.selectbox("Pilih PJP yang ingin diubah: ", options=list_name_pjp,
                                       key="selected_pjp_update", index=0)
    st.info("Pilihan PJP berdasarkan format <Kode PJP>-<Nama PJP>")
    if selected_pjp_update:
        # TODO: Belum handle kalo selected_pjp == None
        selected_code = selected_pjp_update.split('-')[0]
        selected_pjp = get_selected_pjp(selected_code, list_pjp)
    with st.form(key='update_pjp_form', enter_to_submit=False, clear_on_submit=True):
        update_code_pjp = st.text_input("Kode PJP",
                                        key="update_code_pjp",
                                        help="Isian harus berupa angka", value=selected_pjp['code'])
        update_name_pjp = st.text_input("Nama PJP", key='update_name_pjp', value=selected_pjp['name'])
        update_second_name_pjp = st.text_input("Nama PJP Kedua", key='update_second_name_pjp',
                                               help="Nama kedua PJP (Jika ada)",
                                               value=selected_pjp['second_name'])
        update_pt_name_pjp = st.text_input("Nama PJP (dalam PT)", key='update_pt_name_pjp',
                                           help="Nama PJP dengan PT sebagai awalan", value=selected_pjp['pt_name'])
        col3, col4 = st.columns(2)
        with col3:
            submitted_update = st.form_submit_button("Update", use_container_width=True, type="secondary")
        with col4:
            submitted_delete = st.form_submit_button("Delete", use_container_width=True, type="primary")

        if submitted_update:
            if not update_code_pjp or not update_name_pjp or not update_second_name_pjp or not update_pt_name_pjp:
                st.error("Semua field harus diisi!")
            elif update_code_pjp and not update_code_pjp.isdigit():
                st.warning("Kode PJP hanya angka yang diperbolehkan!")
            else:
                try:
                    request = update_pjp(db, selected_code, update_code_pjp, update_name_pjp, update_second_name_pjp,
                                         update_pt_name_pjp)
                    if request.data is not None:
                        st.success("Data PJP telah berhasil diubah!")
                        time.sleep(1.5)
                        streamlit_js_eval(js_expressions="parent.window.location.reload()")
                except Exception as e:
                    if 'duplicate key value violates unique constraint' in str(e):
                        st.error(
                            "Terdapat Error dalam memasukkan PJP baru ke Database: Kode PJP yang sama sudah tersimpan pada database")
                    else:
                        st.error(f"Terdapat Error dalam memasukkan PJP baru ke Database: {e}")
        elif submitted_delete:
            try:
                request = delete_pjp(db, selected_code)
                if request.data is not None:
                    st.success("Data PJP telah berhasil dihapus!")
                    time.sleep(1.5)
                    streamlit_js_eval(js_expressions="parent.window.location.reload()")
            except Exception as e:
                st.error(f"Terdapat Error dalam memasukkan PJP baru ke Database: {e}")

st.markdown("### Kelola Data Referensi Kota")

list_cities = get_city_ref(db)
list_provinces = get_province_ref(db)

options_province = transform_options_province(list_provinces)
df_cities = st.data_editor(
    list_cities,
    column_config={
        "code" : "Kode Kota",
        "name" : "Nama Kota",
        "province_reference": "Provinsi Kota",
    },
    use_container_width=True,
    hide_index=False
)
col5, col6 = st.columns(2)
with col5:
    st.markdown("#### Tambah Data Kota Baru")
    with st.form(key='add_city_form', enter_to_submit=False, clear_on_submit=True):
        city_code = st.text_input("Kode Kota", key="city_code", help="Isian harus berupa angka")
        city_name = st.text_input("Nama Kota", key='city_name')
        city_province = st.selectbox("Pilih Provinsi Kota", key='city_province', options=options_province)
        submitted_insert_city = st.form_submit_button("Submit", use_container_width=True, type="secondary")
        if submitted_insert_city:
            if not city_code or not city_name or not city_province:
                st.error("Semua field harus diisi!")
            elif city_code and not city_code.isdigit():
                st.warning("Kode Kota hanya angka yang diperbolehkan!")
            else:
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
with col6:
    st.markdown("#### Update Data Kota")
    list_name_cities = []
    for city in list_cities:
        list_name_cities.append(f"{city['code']}-{city['name']}")
    selected_city_update = st.selectbox("Pilih Kota yang ingin diubah: ", options=list_name_cities,
                                       key="selected_city_update", index=0)
    st.info("Pilihan Kota berdasarkan format <Kode Kota>-<Nama Kota>")
    if selected_city_update:
        # TODO: Belum handle kalo selected_city == None
        selected_city_code = selected_city_update.split('-')[0]
        selected_city = get_selected_city(selected_city_code, list_cities)
        index_select_update_prov = get_index_options_province(options_province, selected_city['province_reference'])
    with st.form(key='update_city_form', enter_to_submit=False, clear_on_submit=True):
        update_city_code = st.text_input("Kode Kota",
                                        key="update_code_city",
                                        help="Isian harus berupa angka", value=selected_city['code'])
        update_city_name = st.text_input("Nama Kota", key='update_name_city', value=selected_city['name'])
        update_city_province = st.selectbox("Pilih Provinsi Kota", key='update_city_province', options=options_province
                                            , index=index_select_update_prov)

        col7, col8 = st.columns(2)
        with col7:
            submitted_update = st.form_submit_button("Update", use_container_width=True, type="secondary")
        with col8:
            submitted_delete = st.form_submit_button("Delete", use_container_width=True, type="primary")

        if submitted_update:
            if not update_city_code or not update_city_name or not update_city_province:
                st.error("Semua field harus diisi!")
            elif update_city_code and not update_city_code.isdigit():
                st.warning("Kode Kota hanya angka yang diperbolehkan!")
            else:
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
                            "Terdapat Error dalam memasukkan Kota baru ke Database: Kode Kota yang sama sudah tersimpan pada database")
                    else:
                        st.error(f"Terdapat Error dalam memasukkan Kota baru ke Database: {e}")
        elif submitted_delete:
            try:
                request = delete_city(db, selected_city_code)
                if request.data is not None:
                    st.success("Data Kota telah berhasil dihapus!")
                    time.sleep(1.5)
                    streamlit_js_eval(js_expressions="parent.window.location.reload()")
            except Exception as e:
                st.error(f"Terdapat Error dalam memasukkan Kota baru ke Database: {e}")

st.markdown("### Kelola Data Referensi Provinsi")

df_cities = st.data_editor(
    list_provinces,
    column_config={
        "code" : "Kode Provinsi",
        "name" : "Nama Provinsi",
        "country_reference": "Negara Kota",
    },
    use_container_width=True,
    hide_index=False
)
col9, col10 = st.columns(2)
with col9:
    st.markdown("#### Tambah Data Provinsi Baru")
    with st.form(key='add_prov_form', enter_to_submit=False, clear_on_submit=True):
        prov_code = st.text_input("Kode Provinsi", key="prov_code", help="Isian harus berupa angka")
        prov_name = st.text_input("Nama Provinsi", key='prov_name')
        province_country = st.selectbox("Pilih Negara Provinsi", key='province_country', options=['Indonesia'], disabled=True)
        submitted_insert_province = st.form_submit_button("Submit", use_container_width=True, type="secondary")
        if submitted_insert_province:
            if not prov_code or not prov_name or not province_country:
                st.error("Semua field harus diisi!")
            elif prov_code and not prov_code.isdigit():
                st.warning("Kode Kota hanya angka yang diperbolehkan!")
            else:
                try:
                    # Hardcode Indonesia code
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
with col10:
    st.markdown("#### Update Data Provinsi")
    list_name_provinces = []
    for province in list_provinces:
        list_name_provinces.append(f"{province['code']}-{province['name']}")
    selected_province_update = st.selectbox("Pilih Provinsi yang ingin diubah: ", options=list_name_provinces,
                                        key="selected_province_update", index=0)
    st.info("Pilihan Provinsi berdasarkan format <Kode Provinsi>-<Nama Provinsi>")
    if selected_province_update:
        # TODO: Belum handle kalo selected_province == None
        selected_prov_code = selected_province_update.split('-')[0]
        selected_prov = get_selected_prov(selected_prov_code, list_provinces)
    with st.form(key='update_prov_form', enter_to_submit=False, clear_on_submit=True):
        update_prov_code = st.text_input("Kode Provinsi",
                                         key="update_prov_code",
                                         help="Isian harus berupa angka", value=selected_prov['code'])
        update_prov_name = st.text_input("Nama Provinsi", key='update_prov_name', value=selected_prov['name'])
        update_prov_country = st.selectbox("Pilih Negara Kota", key='update_prov_country', options=['Indonesia'], disabled=True)

        col11, col12 = st.columns(2)
        with col11:
            submitted_update = st.form_submit_button("Update", use_container_width=True, type="secondary")
        with col12:
            submitted_delete = st.form_submit_button("Delete", use_container_width=True, type="primary")

        if submitted_update:
            if not update_prov_code or not update_prov_name or not update_prov_country:
                st.error("Semua field harus diisi!")
            elif update_prov_code and not update_prov_code.isdigit():
                st.warning("Kode Kota hanya angka yang diperbolehkan!")
            else:
                try:
                    country_code = "ID"
                    request = update_province(db, selected_prov_code, update_prov_code, update_prov_name, country_code)
                    if request.data is not None:
                        st.success("Data Provinsi telah berhasil diubah!")
                        time.sleep(1.5)
                        streamlit_js_eval(js_expressions="parent.window.location.reload()")
                except Exception as e:
                    if 'duplicate key value violates unique constraint' in str(e):
                        st.error(
                            "Terdapat Error dalam memasukkan Provinsi baru ke Database: Kode Provinsi yang sama sudah tersimpan pada database")
                    else:
                        st.error(f"Terdapat Error dalam memasukkan Provinsi baru ke Database: {e}")
        elif submitted_delete:
            try:
                request = delete_province(db, selected_prov_code)
                if request.data is not None:
                    st.success("Data Kota telah berhasil dihapus!")
                    time.sleep(1.5)
                    streamlit_js_eval(js_expressions="parent.window.location.reload()")
            except Exception as e:
                st.error(f"Terdapat Error dalam memasukkan Kota baru ke Database: {e}")