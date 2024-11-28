import streamlit as st
from service.database import *
from service.preprocess import set_page_visuals
from streamlit_js_eval import streamlit_js_eval
import time


def update_selected_update_pjp(code: str, list_pjp_db):
    for pjp_db in list_pjp_db:
        if pjp_db["code"] == code:
            return pjp_db


# Initial Page Setup
set_page_visuals("dm")

db = connect_db()

st.markdown("### Kelola Data PJP")
list_pjp = get_pjp_jkt(db).copy()
st.dataframe(list_pjp, use_container_width=True)
col1, col2 = st.columns(2)
with col1:
    st.markdown("### Tambah Data PJP Baru")
    with st.form(key='add_pjp_form', enter_to_submit=False, clear_on_submit=True):
        pjp_code = st.text_input("Kode PJP", key="pjp_code", help="Isian harus berupa angka")
        pjp_name = st.text_input("Nama PJP", key='pjp_name')
        pjp_second_name = st.text_input("Nama PJP Kedua", key='pjp_second_name', help="Nama kedua PJP (Jika ada)")
        pjp_pt_name = st.text_input("Nama PJP (dalam PT)", key='pjp_pt_name', help="Nama PJP dengan PT sebagai awalan")
        submitted_insert = st.form_submit_button("Submit")
        if submitted_insert:
            if not pjp_code or not pjp_name or not pjp_second_name or not pjp_pt_name:
                st.error("Semua field harus diisi!")
            elif pjp_code and not pjp_code.isdigit():
                st.warning("Kode PJP hanya angka yang diperbolehkan!")
            else:
                try:
                    request = inset_new_pjp(db, pjp_code, pjp_name, pjp_second_name, pjp_pt_name)
                    if request.data is not None:
                        st.success("Data PJP Baru telah berhasil disimpan!")
                        time.sleep(2)
                        streamlit_js_eval(js_expressions="parent.window.location.reload()")
                except Exception as e:
                    if 'duplicate key value violates unique constraint' in str(e):
                        st.error(
                            "Terdapat Error dalam memasukkan PJP baru ke Database: Kode PJP yang sama sudah tersimpan pada database")
                    else:
                        st.error(f"Terdapat Error dalam memasukkan PJP baru ke Database: {e}")
with col2:
    st.markdown("### Update Data PJP")
    list_name_pjp = []
    for pjp in list_pjp:
        list_name_pjp.append(f"{pjp['code']}-{pjp['name']}")
    selected_pjp_update = st.selectbox("Pilih PJP yang ingin diubah: ", options=list_name_pjp,
                                       key="selected_pjp_update", index=0)
    st.info("Pilihan PJP berdasarkan format <Kode PJP>-<Nama PJP>")
    if selected_pjp_update:
        selected_code = selected_pjp_update.split('-')[0]
        selected_pjp = update_selected_update_pjp(selected_code, list_pjp)
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
        submitted_update = st.form_submit_button("Submit")
        if submitted_update:
            if not update_code_pjp or not update_name_pjp or not update_second_name_pjp or not update_pt_name_pjp:
                st.error("Semua field harus diisi!")
            elif pjp_code and not pjp_code.isdigit():
                st.warning("Kode PJP hanya angka yang diperbolehkan!")
            else:
                try:
                    request = update_pjp(db, selected_code, update_code_pjp, update_name_pjp, update_second_name_pjp,
                                         update_pt_name_pjp)
                    if request.data is not None:
                        st.success("Data PJP telah berhasil diubah!")
                        time.sleep(2)
                        streamlit_js_eval(js_expressions="parent.window.location.reload()")
                except Exception as e:
                    if 'duplicate key value violates unique constraint' in str(e):
                        st.error(
                            "Terdapat Error dalam memasukkan PJP baru ke Database: Kode PJP yang sama sudah tersimpan pada database")
                    else:
                        st.error(f"Terdapat Error dalam memasukkan PJP baru ke Database: {e}")
