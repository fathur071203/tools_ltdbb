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


def get_selected_country(code: str, list_country_db):
    for country_db in list_country_db:
        if country_db["code"] == code:
            return country_db


def get_selected_person(name: str, list_person_db):
    for person_db in list_person_db:
        if person_db["name"] == name:
            return person_db


# Initial Page Setup
set_page_visuals("dm")

db = connect_db()

list_pjp = get_pjp_jkt(db).copy()
list_sus_people = get_sus_peoples(db).copy()
list_sus_cities = get_sus_city(db, True).copy()
list_non_sus_cities = get_sus_city(db, False).copy()
list_sus_prov = get_sus_prov(db, True).copy()
list_non_sus_prov = get_sus_prov(db, False).copy()

list_non_blacklisted = get_blacklisted_country(db, False).copy()
list_non_greylisted = get_greylisted_country(db, False).copy()
list_blacklisted = get_blacklisted_country(db, True).copy()
list_greylisted = get_greylisted_country(db, True).copy()

list_non_blacklisted = sorted(list_non_blacklisted, key=lambda x: x['name'])
list_non_greylisted = sorted(list_non_greylisted, key=lambda x: x['name'])
list_blacklisted = sorted(list_blacklisted, key=lambda x: x['name'])
list_greylisted = sorted(list_greylisted, key=lambda x: x['name'])

tab1, tab2 = st.tabs(["Kelola Data Terduga Mencurigakan", "Kelola Data Referensi"])

with tab1:
    st.markdown("### Kelola Data Nama Terduga Mencurigakan")
    if len(list_sus_people) > 0:
        df_sus_people = st.data_editor(
            list_sus_people,
            column_config={
                "name": "Nama Terduga"
            },
            key="suspicious_person"
        )
    else:
        st.warning("Tidak ada data nama Terduga untuk ditampilkan.")
    col_sus1, col_sus2 = st.columns(2)
    with col_sus1:
        st.markdown("#### Tambah Data Nama Terduga Mencurigakan Baru")
        with st.form(key='add_sus_person_form', enter_to_submit=False):
            person_name = st.text_input("Nama Orang Terduga", key='person_name')
            submitted_suspected = st.form_submit_button("Submit", use_container_width=True, type="secondary")
            if submitted_suspected:
                if not person_name:
                    st.error("Semua field harus diisi!")
                else:
                    submit_add_sus_person(db, person_name_input=person_name)
    with col_sus2:
        st.markdown("#### Update Data Nama Terduga Mencurigakan")
        options_sus_people = []
        if len(list_sus_people) > 0:
            for person in list_sus_people:
                options_sus_people.append(person['name'])
            selected_person_update = st.selectbox("Pilih Nama Terduga yang ingin diubah: ",
                                                  options=options_sus_people,
                                                  key="selected_person_update", index=0)
            if selected_person_update:
                selected_person = get_selected_person(selected_person_update, list_sus_people)
            with st.form(key='update_person_form', enter_to_submit=False):
                update_person_name = st.text_input("Nama Terduga",
                                                   key="update_person_name", value=selected_person['name'])
                col_sus3, col_sus4 = st.columns(2)
                with col_sus3:
                    submitted_update = st.form_submit_button("Update", use_container_width=True, type="secondary")
                with col_sus4:
                    submitted_delete = st.form_submit_button("Delete", use_container_width=True, type="primary")

                if submitted_update:
                    if not update_person_name:
                        st.error("Semua field harus diisi!")
                    else:
                        submit_update_sus_person(db, selected_person_update, update_person_name)
                elif submitted_delete:
                    submit_delete_sus_person(db, selected_person_update)
        else:
            st.warning("Tidak ada data nama Terduga untuk diubah atau dihapus.")
    st.divider()
    # st.markdown("### Kelola Data Daerah Mencurigakan")
    # if len(list_sus_cities) > 0:
    #     df_sus_cities = st.data_editor(
    #         list_sus_cities,
    #         column_config={
    #             "code": "Kode Daerah Mencurigakan",
    #             "name": "Daerah Mencurigakan",
    #             "province_reference": "Provinsi Daerah",
    #         },
    #     )
    # else:
    #     st.warning("Tidak ada data daerah mencurigakan untuk ditampilkan.")
    # col_sus3, col_sus4 = st.columns(2)
    # with col_sus3:
    #     st.markdown("#### Tambah Data Daerah Mencurigakan Baru")
    #     with st.form(key='add_sus_city_form', enter_to_submit=False, clear_on_submit=True):
    #         options_non_sus_city = []
    #         for cities in list_non_sus_cities:
    #             options_non_sus_city.append(f"{cities['code']}-{cities['name']}-{cities['province_reference']}")
    #         selected_city = st.selectbox("Pilih Daerah yang ingin dibuat Mencurigakan", options=options_non_sus_city)
    #         submitted_suspected_city = st.form_submit_button("Submit", use_container_width=True, type="secondary")
    #         if submitted_suspected_city:
    #             if not selected_city:
    #                 st.error("Semua field harus diisi!")
    #             else:
    #                 try:
    #                     selected_code_city = selected_city.split('-')[0]
    #                     request = update_sus_city(db, selected_code_city, True)
    #                     if request.data is not None:
    #                         st.success("Data Daerah Mencurigakan Baru telah berhasil disimpan!")
    #                         time.sleep(1.5)
    #                         streamlit_js_eval(js_expressions="parent.window.location.reload()")
    #                 except Exception as e:
    #                     st.error(f"Terdapat Error dalam memasukkan Data Daerah Mencurigakan baru ke Database: {e}")
    # with col_sus4:
    #     st.markdown("#### Hapus Data Daerah Mencurigakan")
    #     if len(list_sus_cities) > 0:
    #         with st.form(key='remove_sus_city_form', enter_to_submit=False, clear_on_submit=True):
    #             options_sus_city = []
    #             for cities in list_sus_cities:
    #                 options_sus_city.append(f"{cities['code']}-{cities['name']}-{cities['province_reference']}")
    #             selected_city_delete = st.selectbox("Pilih Daerah yang ingin dibuat tidak Mencurigakan", options=options_sus_city)
    #             submitted_update_suspected_city = st.form_submit_button("Delete", use_container_width=True, type="primary")
    #             if submitted_update_suspected_city:
    #                 if not selected_city_delete:
    #                     st.error("Semua field harus diisi!")
    #                 else:
    #                     try:
    #                         selected_code_city_delete = selected_city_delete.split('-')[0]
    #                         request = update_sus_city(db, selected_code_city_delete, False)
    #                         if request.data is not None:
    #                             st.success("Data Daerah Mencurigakan Baru telah berhasil diubah!")
    #                             time.sleep(1.5)
    #                             streamlit_js_eval(js_expressions="parent.window.location.reload()")
    #                     except Exception as e:
    #                         st.error(f"Terdapat Error dalam memasukkan Data Daerah Mencurigakan baru ke Database: {e}")
    #     else:
    #         st.warning("Tidak ada data daerah mencurigakan untuk dihapus atau diubah.")
    # st.info("Pilihan Daerah berdasarkan format <Kode Daerah>-<Nama Daerah>-<Nama Provinsi>")
    # st.divider()
    # st.markdown("### Kelola Data Provinsi Mencurigakan")
    # if len(list_sus_prov) > 0:
    #     df_sus_prov = st.data_editor(
    #         list_sus_prov,
    #         column_config={
    #             "code": "Kode Provinsi Mencurigakan",
    #             "name": "Provinsi Mencurigakan",
    #             "country_reference": "Negara Provinsi",
    #         },
    #     )
    # else:
    #     st.warning("Tidak ada data Provinsi mencurigakan untuk ditampilkan.")
    # col_sus5, col_sus6 = st.columns(2)
    # with col_sus5:
    #     st.markdown("#### Tambah Data Provinsi Mencurigakan Baru")
    #     with st.form(key='add_sus_prov_form', enter_to_submit=False, clear_on_submit=True):
    #         options_non_sus_prov = []
    #         for prov in list_non_sus_prov:
    #             options_non_sus_prov.append(f"{prov['code']}-{prov['name']}-{prov['country_reference']}")
    #         selected_prov_sus = st.selectbox("Pilih Provinsi yang ingin dibuat Mencurigakan", options=options_non_sus_prov)
    #         submitted_suspected_prov = st.form_submit_button("Submit", use_container_width=True, type="secondary")
    #         if submitted_suspected_prov:
    #             if not selected_prov_sus:
    #                 st.error("Semua field harus diisi!")
    #             else:
    #                 try:
    #                     selected_code_prov = selected_prov_sus.split('-')[0]
    #                     request = update_sus_prov(db, selected_code_prov, True)
    #                     if request.data is not None:
    #                         st.success("Data Provinsi Mencurigakan Baru telah berhasil disimpan!")
    #                         time.sleep(1.5)
    #                         streamlit_js_eval(js_expressions="parent.window.location.reload()")
    #                 except Exception as e:
    #                     st.error(f"Terdapat Error dalam memasukkan Data Provinsi Mencurigakan baru ke Database: {e}")
    # with col_sus6:
    #     st.markdown("#### Hapus Data Provinsi Mencurigakan")
    #     if len(list_sus_prov) > 0:
    #         with st.form(key='remove_sus_prov_form', enter_to_submit=False, clear_on_submit=True):
    #             options_sus_prov = []
    #             for prov in list_sus_prov:
    #                 options_sus_prov.append(f"{prov['code']}-{prov['name']}-{prov['country_reference']}")
    #             selected_prov_delete = st.selectbox("Pilih Provinsi yang ingin dibuat tidak Mencurigakan",
    #                                                 options=options_sus_prov)
    #             submitted_update_suspected_prov = st.form_submit_button("Delete", use_container_width=True,
    #                                                                     type="primary")
    #             if submitted_update_suspected_prov:
    #                 if not selected_prov_delete:
    #                     st.error("Semua field harus diisi!")
    #                 else:
    #                     try:
    #                         selected_code_prov_delete = selected_prov_delete.split('-')[0]
    #                         request = update_sus_prov(db, selected_code_prov_delete, False)
    #                         if request.data is not None:
    #                             st.success("Data Provinsi Mencurigakan Baru telah berhasil diubah!")
    #                             time.sleep(1.5)
    #                             streamlit_js_eval(js_expressions="parent.window.location.reload()")
    #                     except Exception as e:
    #                         st.error(f"Terdapat Error dalam memasukkan Data Provinsi Mencurigakan baru ke Database: {e}")
    #     else:
    #         st.warning("Tidak ada data Provinsi mencurigakan untuk dihapus atau diubah.")
    # st.divider()
    st.markdown("### Kelola Data Negara Blacklist & Greylist")
    col_sus7, col_sus8 = st.columns(2)
    with col_sus7:
        if len(list_blacklisted) > 0:
            df_blacklisted_countries = st.data_editor(
                list_blacklisted,
                column_config={
                    "code": "Kode Negara",
                    "name": "Nama Negara"
                },
                key="blacklisted_countries",
                use_container_width=True
            )
            st.markdown("#### Hapus Data Negara Blacklist")
            with st.form(key='remove_blacklisted_country_form', enter_to_submit=False):
                options_blacklisted_countries = []
                for country in list_blacklisted:
                    options_blacklisted_countries.append(f"{country['code']}-{country['name']}")
                selected_delete_blacklisted_country = st.selectbox("Pilih Negara yang ingin dihilangkan blacklist-nya",
                                                                   options=options_blacklisted_countries)
                submitted_del_blacklist = st.form_submit_button("Delete", use_container_width=True, type="primary")
                if submitted_del_blacklist:
                    if not selected_delete_blacklisted_country:
                        st.error("Semua field harus diisi!")
                    else:
                        submit_delete_blacklisted_country(db, selected_delete_blacklisted_country, False)
        else:
            st.warning("Tidak ada data Negara yang masuk dalam blacklist")
        st.markdown("#### Tambah Data Negara Blacklist Baru")
        with st.form(key='add_blacklisted_country_form', enter_to_submit=False):
            options_insert_blacklisted_countries = []
            for country in list_non_blacklisted:
                options_insert_blacklisted_countries.append(f"{country['code']}-{country['name']}")
            selected_blacklisted_country = st.selectbox("Pilih Negara yang ingin di-blacklist",
                                                        options=options_insert_blacklisted_countries)
            submitted_blacklist = st.form_submit_button("Submit", use_container_width=True, type="secondary")
            if submitted_blacklist:
                if not selected_blacklisted_country:
                    st.error("Semua field harus diisi!")
                else:
                    submit_add_blacklisted_country(db, selected_blacklisted_country, True)
    with col_sus8:
        if len(list_greylisted) > 0:
            df_greylisted_countries = st.data_editor(
                list_greylisted,
                column_config={
                    "code": "Kode Negara",
                    "name": "Nama Negara"
                },
                key="greylisted_countries",
                use_container_width=True
            )

            st.markdown("#### Hapus Data Negara Greylist")
            with st.form(key='remove_greylist_country_form', enter_to_submit=False):
                options_greylist_countries = []
                for country in list_greylisted:
                    options_greylist_countries.append(f"{country['code']}-{country['name']}")
                selected_delete_greylisted_country = st.selectbox("Pilih Negara yang ingin dihilangkan greylist-nya",
                                                                  options=options_greylist_countries)
                submitted_del_greylisted = st.form_submit_button("Delete", use_container_width=True, type="primary")
                if submitted_del_greylisted:
                    if not selected_delete_greylisted_country:
                        st.error("Semua field harus diisi!")
                    else:
                        submit_delete_greylisted_country(db, selected_delete_greylisted_country, False)
        else:
            st.warning("Tidak ada data Negara yang masuk dalam greylist")
        st.markdown("#### Tambah Data Negara Greylist Baru")
        with st.form(key='add_greylist_country_form', enter_to_submit=False):
            options_insert_greylisted_countries = []
            for country in list_non_greylisted:
                options_insert_greylisted_countries.append(f"{country['code']}-{country['name']}")
            selected_greylisted_country = st.selectbox("Pilih Negara yang ingin di-greylist",
                                                       options=options_insert_greylisted_countries)
            submitted_greylist = st.form_submit_button("Submit", use_container_width=True, type="secondary")
            if submitted_greylist:
                if not selected_greylisted_country:
                    st.error("Semua field harus diisi!")
                else:
                    submit_add_greylisted_country(db, selected_greylisted_country, True)
    st.divider()
with tab2:
    st.markdown("### Kelola Data PJP")
    df_pjp = st.data_editor(
        list_pjp,
        column_config={
            "code": "Kode Penyelenggara",
            "name": "Nama Penyelenggara",
            "second_name": "Nama Penyelenggara 2",
            "pt_name": "Nama Penyelenggara PT"
        },
        use_container_width=True,
        hide_index=False
    )
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Tambah Data PJP Baru")
        with st.form(key='add_pjp_form', enter_to_submit=False):
            pjp_code = st.text_input("Kode PJP", key="pjp_code", help="Isian harus berupa angka")
            pjp_name = st.text_input("Nama PJP", key='pjp_name')
            pjp_second_name = st.text_input("Nama PJP Kedua", key='pjp_second_name', help="Nama kedua PJP (Jika ada)")
            pjp_pt_name = st.text_input("Nama PJP (dalam PT)", key='pjp_pt_name',
                                        help="Nama PJP dengan PT sebagai awalan")
            submitted_insert = st.form_submit_button("Submit", use_container_width=True, type="secondary")
            if submitted_insert:
                if not pjp_code or not pjp_name or not pjp_second_name or not pjp_pt_name:
                    st.error("Semua field harus diisi!")
                elif pjp_code and not pjp_code.isdigit():
                    st.warning("Kode PJP hanya angka yang diperbolehkan!")
                else:
                    submit_add_pjp(db, pjp_code, pjp_name, pjp_second_name, pjp_pt_name)
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
        with st.form(key='update_pjp_form', enter_to_submit=False):
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
                    submit_update_pjp(db, selected_code, update_code_pjp, update_name_pjp, update_second_name_pjp, update_pt_name_pjp)
            elif submitted_delete:
                submit_delete_pjp(db, selected_code)

    st.markdown("### Kelola Data Referensi Kota")

    list_cities = get_city_ref(db)
    list_provinces = get_province_ref(db)

    options_province = transform_options_province(list_provinces)
    df_cities = st.data_editor(
        list_cities,
        column_config={
            "code": "Kode Kota",
            "name": "Nama Kota",
            "province_reference": "Provinsi Kota",
        },
        use_container_width=True,
        hide_index=False
    )
    col5, col6 = st.columns(2)
    with col5:
        st.markdown("#### Tambah Data Kota Baru")
        with st.form(key='add_city_form', enter_to_submit=False):
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
                    submit_add_city(db, city_code, city_name, list_provinces, city_province)
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
        with st.form(key='update_city_form', enter_to_submit=False):
            update_city_code = st.text_input("Kode Kota",
                                             key="update_code_city",
                                             help="Isian harus berupa angka", value=selected_city['code'])
            update_city_name = st.text_input("Nama Kota", key='update_name_city', value=selected_city['name'])
            update_city_province = st.selectbox("Pilih Provinsi Kota", key='update_city_province',
                                                options=options_province
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
                    submit_update_city(db, selected_city_code, update_city_code, update_city_name, list_provinces, update_city_province)
            elif submitted_delete:
                submit_delete_city(db, selected_city_code)

    st.markdown("### Kelola Data Referensi Provinsi")

    df_cities = st.data_editor(
        list_provinces,
        column_config={
            "code": "Kode Provinsi",
            "name": "Nama Provinsi",
            "country_reference": "Negara Kota",
        },
        use_container_width=True,
        hide_index=False
    )
    col9, col10 = st.columns(2)
    with col9:
        st.markdown("#### Tambah Data Provinsi Baru")
        with st.form(key='add_prov_form', enter_to_submit=False):
            prov_code = st.text_input("Kode Provinsi", key="prov_code", help="Isian harus berupa angka")
            prov_name = st.text_input("Nama Provinsi", key='prov_name')
            province_country = st.selectbox("Pilih Negara Provinsi", key='province_country', options=['Indonesia'],
                                            disabled=True)
            submitted_insert_province = st.form_submit_button("Submit", use_container_width=True, type="secondary")
            if submitted_insert_province:
                if not prov_code or not prov_name or not province_country:
                    st.error("Semua field harus diisi!")
                elif prov_code and not prov_code.isdigit():
                    st.warning("Kode Provinsi hanya angka yang diperbolehkan!")
                else:
                    submit_add_prov(db, prov_code, prov_name)
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
        with st.form(key='update_prov_form', enter_to_submit=False):
            update_prov_code = st.text_input("Kode Provinsi",
                                             key="update_prov_code",
                                             help="Isian harus berupa angka", value=selected_prov['code'])
            update_prov_name = st.text_input("Nama Provinsi", key='update_prov_name', value=selected_prov['name'])
            update_prov_country = st.selectbox("Pilih Negara Kota", key='update_prov_country', options=['Indonesia'],
                                               disabled=True)

            col11, col12 = st.columns(2)
            with col11:
                submitted_update = st.form_submit_button("Update", use_container_width=True, type="secondary")
            with col12:
                submitted_delete = st.form_submit_button("Delete", use_container_width=True, type="primary")

            if submitted_update:
                if not update_prov_code or not update_prov_name or not update_prov_country:
                    st.error("Semua field harus diisi!")
                elif update_prov_code and not update_prov_code.isdigit():
                    st.warning("Kode Provinsi hanya angka yang diperbolehkan!")
                else:
                    submit_update_prov(db, selected_prov_code, update_prov_code, update_prov_name)
            elif submitted_delete:
                submit_delete_prov(db, selected_prov_code)

    st.markdown("### Kelola Data Referensi Negara")

    list_countries = get_country_ref(db)

    df_countries = st.data_editor(
        list_countries,
        column_config={
            "code": "Kode Negara",
            "name": "Nama Negara",
        },
        use_container_width=True,
        hide_index=False
    )
    col13, col14 = st.columns(2)
    with col13:
        st.markdown("#### Tambah Data Negara Baru")
        with st.form(key='add_country_form', enter_to_submit=False):
            country_code = st.text_input("Kode Negara", key="country_code", help="Isian harus berupa non-angka")
            country_name = st.text_input("Nama Negara", key='country_name')
            submitted_insert_country = st.form_submit_button("Submit", use_container_width=True, type="secondary")
            if submitted_insert_country:
                if not country_code or not country_name:
                    st.error("Semua field harus diisi!")
                else:
                    submit_add_country(db, country_code, country_name)
    with col14:
        st.markdown("#### Update Data Negara")
        list_name_countries = []
        for countries in list_countries:
            list_name_countries.append(f"{countries['code']}-{countries['name']}")
        selected_country_update = st.selectbox("Pilih Negara yang ingin diubah: ", options=list_name_countries,
                                               key="selected_country_update", index=0)
        st.info("Pilihan Negara berdasarkan format <Kode Negara>-<Nama Negara>")
        if selected_country_update:
            # TODO: Belum handle kalo selected_country == None
            selected_country_code = selected_country_update.split('-')[0]
            selected_country = get_selected_country(selected_country_code, list_countries)
        with st.form(key='update_country_form', enter_to_submit=False):
            update_country_code = st.text_input("Kode Negara",
                                                key="update_country_code",
                                                help="Isian harus berupa non-angka", value=selected_country['code'])
            update_country_name = st.text_input("Nama Negara", key='update_country_name',
                                                value=selected_country['name'])

            col15, col16 = st.columns(2)
            with col15:
                submitted_update = st.form_submit_button("Update", use_container_width=True, type="secondary")
            with col16:
                submitted_delete = st.form_submit_button("Delete", use_container_width=True, type="primary")

            if submitted_update:
                if not update_country_code or not update_country_name:
                    st.error("Semua field harus diisi!")
                else:
                    submit_update_country(db, selected_country_code, update_country_code, update_country_name)
            elif submitted_delete:
                submit_delete_country(db, selected_country_code)