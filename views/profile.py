import pandas as pd
import streamlit as st
import calendar

from service.preprocess import *
from service.visualize import *

# Initial Page Setup
set_page_visuals("viz")

if st.session_state['df_national'] is not None and st.session_state['df'] is not None:
    df_national = st.session_state['df_national']
    df = st.session_state['df']

    with st.sidebar:
        with st.expander("Filter Individu", True):
            pjp_list = ['All'] + sorted(df['Nama PJP'].unique().tolist())
            years_list = sorted(list(df['Year'].unique()))
            
            # Search filter untuk PJP
            search_pjp = st.text_input("🔍 Cari PJP:", placeholder="Ketik nama PJP...")
            if search_pjp:
                filtered_pjp = [pjp for pjp in pjp_list if search_pjp.lower() in pjp.lower()]
            else:
                filtered_pjp = pjp_list
            
            selected_pjp = st.selectbox('Pilih PJP:', filtered_pjp)
            
            # Range tahun
            col1, col2 = st.columns(2)
            with col1:
                start_year = st.selectbox('Tahun Mulai:', years_list, key="key_start_year")
            with col2:
                # Filter tahun akhir hanya menampilkan tahun >= tahun mulai
                end_years = [y for y in years_list if y >= start_year]
                end_year = st.selectbox('Tahun Akhir:', end_years, key="key_end_year")
            
            # Pastikan end_year >= start_year
            if end_year < start_year:
                end_year = start_year
        st.info("Gunakan filter untuk memilih nama PJP dan rentang tahun transaksi.")

    df_national_preprocessed_year = preprocess_data_national(df_national, True)
    df_national_preprocessed_month = preprocess_data_national(df_national, False)
    df_preprocessed = preprocess_data(df, True)

    df_preprocessed_grouped_year = df_preprocessed.groupby(['Nama PJP', 'Year']).agg({
        'Sum of Fin Jumlah Inc': 'sum',
        'Sum of Fin Jumlah Out': 'sum',
        'Sum of Fin Jumlah Dom': 'sum',
        'Sum of Fin Nilai Inc': 'sum',
        'Sum of Fin Nilai Out': 'sum',
        'Sum of Fin Nilai Dom': 'sum',
        'Sum of Total Nom': 'sum'
    }).reset_index()
    df_preprocessed_grouped_month = df_preprocessed.groupby(['Nama PJP', 'Year', 'Month'], observed=False).agg({
        'Sum of Fin Jumlah Inc': 'sum',
        'Sum of Fin Jumlah Out': 'sum',
        'Sum of Fin Jumlah Dom': 'sum',
        'Sum of Fin Nilai Inc': 'sum',
        'Sum of Fin Nilai Out': 'sum',
        'Sum of Fin Nilai Dom': 'sum',
        'Sum of Total Nom': 'sum'
    }).reset_index()

    if selected_pjp == 'All':
        st.warning("Silakan pilih PJP untuk menampilkan profil.")
    else:
        # Filter data berdasarkan range tahun
        df_grouped_filtered_year = df_preprocessed_grouped_year[
            (df_preprocessed_grouped_year['Nama PJP'] == selected_pjp) &
            (df_preprocessed_grouped_year['Year'] >= start_year) &
            (df_preprocessed_grouped_year['Year'] <= end_year)
        ]
        
        df_grouped_national_filtered_year = df_national_preprocessed_year[
            (df_national_preprocessed_year['Year'] >= start_year) &
            (df_national_preprocessed_year['Year'] <= end_year)
        ]
        
        df_grouped_filtered_month = df_preprocessed_grouped_month[
            (df_preprocessed_grouped_month['Nama PJP'] == selected_pjp) &
            (df_preprocessed_grouped_month['Year'] >= start_year) &
            (df_preprocessed_grouped_month['Year'] <= end_year)
        ]

        df_incoming_month = process_data_profile_month(df_grouped_filtered_month, "Inc")
        df_outgoing_month = process_data_profile_month(df_grouped_filtered_month, "Out")
        df_domestic_month = process_data_profile_month(df_grouped_filtered_month, "Dom")

        data_jumlah_inc = compile_data_profile(df_grouped_filtered_year, df_grouped_national_filtered_year, "Jumlah",
                                               "Inc")
        data_jumlah_out = compile_data_profile(df_grouped_filtered_year, df_grouped_national_filtered_year, "Jumlah",
                                               "Out")
        data_jumlah_dom = compile_data_profile(df_grouped_filtered_year, df_grouped_national_filtered_year, "Jumlah",
                                               "Dom")

        data_nilai_inc = compile_data_profile(df_grouped_filtered_year, df_grouped_national_filtered_year, "Nilai",
                                              "Inc")
        data_nilai_out = compile_data_profile(df_grouped_filtered_year, df_grouped_national_filtered_year, "Nilai",
                                              "Out")
        data_nilai_dom = compile_data_profile(df_grouped_filtered_year, df_grouped_national_filtered_year, "Nilai",
                                              "Dom")

        if len(data_jumlah_inc) > 0 or len(data_jumlah_out) > 0 or len(data_jumlah_dom) > 0 or len(
                data_nilai_inc) > 0 or len(data_nilai_out) > 0 or len(data_nilai_dom):
            merged_data = pd.merge(data_jumlah_inc, data_jumlah_out, on=['Transaction Type'])
            merged_data = pd.merge(merged_data, data_jumlah_dom, on=['Transaction Type'])
            merged_data = pd.merge(merged_data, data_nilai_inc, on=['Transaction Type'])
            merged_data = pd.merge(merged_data, data_nilai_out, on=['Transaction Type'])
            merged_data = pd.merge(merged_data, data_nilai_dom, on=['Transaction Type'])

            df_grand_total_dom = process_grand_total_profile(df_domestic_month, "Dom")
            df_grand_total_inc = process_grand_total_profile(df_incoming_month, "Inc")
            df_grand_total_out = process_grand_total_profile(df_outgoing_month, "Out")

            st.subheader(f"Profil Transaksi - PT {selected_pjp} Tahun {start_year} - {end_year}")
            merged_data = format_profile_df(merged_data)
            st.dataframe(merged_data, use_container_width=True, hide_index=True)
            st.info(
                "*Persentase merupakan persentase jumlah atau nilai transaksi PJP terhadap jumlah atau nilai transaksi nasional")
            col1, col2, col3 = st.columns(3)
            with col1:
                df_domestic_month_display = df_domestic_month.copy()
                df_domestic_month_display = rename_format_profile_df(df_domestic_month_display, "Dom")
                df_grand_total_dom = format_profile_df_grand_total(df_grand_total_dom, "Dom")
                st.dataframe(df_domestic_month_display, use_container_width=True, hide_index=True)
                st.dataframe(df_grand_total_dom, use_container_width=True, hide_index=True)
            with col2:
                df_incoming_month_display = df_incoming_month.copy()
                df_incoming_month_display = rename_format_profile_df(df_incoming_month_display, "Inc")
                df_grand_total_inc = format_profile_df_grand_total(df_grand_total_inc, "Inc")
                st.dataframe(df_incoming_month_display, use_container_width=True, hide_index=True)
                st.dataframe(df_grand_total_inc, use_container_width=True, hide_index=True)
            with col3:
                df_outgoing_month_display = df_outgoing_month.copy()
                df_outgoing_month_display = rename_format_profile_df(df_outgoing_month_display, "Out")
                df_grand_total_out = format_profile_df_grand_total(df_grand_total_out, "Out")
                st.dataframe(df_outgoing_month_display, use_container_width=True, hide_index=True)
                st.dataframe(df_grand_total_out, use_container_width=True, hide_index=True)
            st.warning("""
            Pada visualisasi di bawah saja:
            - Simbol , (koma) berfungsi sebagai pemisah ribuan
            - Simbol . (titik) berfungsi sebagai pemisah desimal
            """)
            
            # Tambahkan section untuk Growth Data
            st.divider()
            st.subheader(f"📊 Data Pertumbuhan Transaksi - {selected_pjp} (Per Kuartal) Tahun {start_year} - {end_year}")
            
            with st.spinner('Memproses data pertumbuhan...'):
                # Get growth data untuk PJP
                pjp_growth_data = get_pjp_growth_data(df_preprocessed, selected_pjp, is_month=False)
                
                if pjp_growth_data and 'total' in pjp_growth_data:
                    df_total_growth = pjp_growth_data['total'].copy()
                    
                    # Format columns untuk display
                    df_total_growth = df_total_growth.rename(columns={
                        'Sum of Fin Jumlah Total': 'Total Frekuensi Total',
                        'Sum of Fin Nilai Total': 'Total Nominal Total',
                        '%YoY': 'Year-on-Year Nominal (%)',
                        '%QtQ': 'Quarter-to-Quarter Nominal (%)',
                    })
                    
                    # Reorder columns
                    display_cols = ['Year', 'Quarter', 'Total Frekuensi Total', 'Total Nominal Total',
                                    'Year-on-Year Nominal (%)', 'Quarter-to-Quarter Nominal (%)']
                    df_total_growth_display = df_total_growth[display_cols].copy()
                    
                    # Format display
                    df_total_growth_display = format_pjp_growth_table(df_total_growth_display, is_total=True)
                    
                    # Buat versi untuk download dengan number yang bersih
                    df_total_growth_download = df_total_growth[display_cols].copy()
                    df_total_growth_download['Year'] = df_total_growth_download['Year'].astype(int)
                    df_total_growth_download['Quarter'] = df_total_growth_download['Quarter'].astype(int)
                    df_total_growth_download['Total Frekuensi Total'] = df_total_growth_download['Total Frekuensi Total'].astype(int)
                    df_total_growth_download['Total Nominal Total'] = df_total_growth_download['Total Nominal Total'].astype(int)
                    
                    st.write("**Total (Incoming + Outgoing + Domestik)**")
                    col_display, col_download = st.columns([3, 1])
                    with col_display:
                        st.dataframe(df_total_growth_display, use_container_width=True, hide_index=True)
                    with col_download:
                        csv_total = df_total_growth_download.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Total",
                            data=csv_total,
                            file_name=f"pertumbuhan_total_{selected_pjp}_{start_year}_{end_year}.csv",
                            mime="text/csv"
                        )
                    
                    # Tampilkan tabel per tipe transaksi
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**Incoming**")
                        df_inc = pjp_growth_data['incoming'].copy()
                        df_inc = df_inc.rename(columns={
                            'Frekuensi': 'Total Frekuensi',
                            'Nominal': 'Total Nominal',
                            '%YoY': 'Year-on-Year (%)',
                            '%QtQ': 'Quarter-to-Quarter (%)',
                        })
                        # Reorder columns
                        inc_cols = ['Year', 'Quarter', 'Total Frekuensi', 'Total Nominal', 'Year-on-Year (%)', 'Quarter-to-Quarter (%)']
                        df_inc_display = df_inc[inc_cols].copy()
                        df_inc_display = format_pjp_growth_table(df_inc_display, is_total=False)
                        st.dataframe(df_inc_display, use_container_width=True, hide_index=True)
                        
                        # Download untuk Incoming
                        df_inc_download = df_inc[inc_cols].copy()
                        df_inc_download['Year'] = df_inc_download['Year'].astype(int)
                        df_inc_download['Quarter'] = df_inc_download['Quarter'].astype(int)
                        df_inc_download['Total Frekuensi'] = df_inc_download['Total Frekuensi'].astype(int)
                        df_inc_download['Total Nominal'] = df_inc_download['Total Nominal'].astype(int)
                        csv_inc = df_inc_download.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Incoming",
                            data=csv_inc,
                            file_name=f"pertumbuhan_incoming_{selected_pjp}_{start_year}_{end_year}.csv",
                            mime="text/csv",
                            key="btn_download_incoming"
                        )
                    
                    with col2:
                        st.write("**Outgoing**")
                        df_out = pjp_growth_data['outgoing'].copy()
                        df_out = df_out.rename(columns={
                            'Frekuensi': 'Total Frekuensi',
                            'Nominal': 'Total Nominal',
                            '%YoY': 'Year-on-Year (%)',
                            '%QtQ': 'Quarter-to-Quarter (%)',
                        })
                        # Reorder columns
                        out_cols = ['Year', 'Quarter', 'Total Frekuensi', 'Total Nominal', 'Year-on-Year (%)', 'Quarter-to-Quarter (%)']
                        df_out_display = df_out[out_cols].copy()
                        df_out_display = format_pjp_growth_table(df_out_display, is_total=False)
                        st.dataframe(df_out_display, use_container_width=True, hide_index=True)
                        
                        # Download untuk Outgoing
                        df_out_download = df_out[out_cols].copy()
                        df_out_download['Year'] = df_out_download['Year'].astype(int)
                        df_out_download['Quarter'] = df_out_download['Quarter'].astype(int)
                        df_out_download['Total Frekuensi'] = df_out_download['Total Frekuensi'].astype(int)
                        df_out_download['Total Nominal'] = df_out_download['Total Nominal'].astype(int)
                        csv_out = df_out_download.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Outgoing",
                            data=csv_out,
                            file_name=f"pertumbuhan_outgoing_{selected_pjp}_{start_year}_{end_year}.csv",
                            mime="text/csv",
                            key="btn_download_outgoing"
                        )
                    
                    with col3:
                        st.write("**Domestik**")
                        df_dom = pjp_growth_data['domestik'].copy()
                        df_dom = df_dom.rename(columns={
                            'Frekuensi': 'Total Frekuensi',
                            'Nominal': 'Total Nominal',
                            '%YoY': 'Year-on-Year (%)',
                            '%QtQ': 'Quarter-to-Quarter (%)',
                        })
                        # Reorder columns
                        dom_cols = ['Year', 'Quarter', 'Total Frekuensi', 'Total Nominal', 'Year-on-Year (%)', 'Quarter-to-Quarter (%)']
                        df_dom_display = df_dom[dom_cols].copy()
                        df_dom_display = format_pjp_growth_table(df_dom_display, is_total=False)
                        st.dataframe(df_dom_display, use_container_width=True, hide_index=True)
                        
                        # Download untuk Domestik
                        df_dom_download = df_dom[dom_cols].copy()
                        df_dom_download['Year'] = df_dom_download['Year'].astype(int)
                        df_dom_download['Quarter'] = df_dom_download['Quarter'].astype(int)
                        df_dom_download['Total Frekuensi'] = df_dom_download['Total Frekuensi'].astype(int)
                        df_dom_download['Total Nominal'] = df_dom_download['Total Nominal'].astype(int)
                        csv_dom = df_dom_download.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Domestik",
                            data=csv_dom,
                            file_name=f"pertumbuhan_domestik_{selected_pjp}_{start_year}_{end_year}.csv",
                            mime="text/csv",
                            key="btn_download_domestik"
                        )
            
            st.divider()
            
            make_combined_bar_line_chart_profile(df_domestic_month, "Dom", selected_pjp, f"{start_year}-{end_year}")
            make_combined_bar_line_chart_profile(df_incoming_month, "Inc", selected_pjp, f"{start_year}-{end_year}")
            make_combined_bar_line_chart_profile(df_outgoing_month, "Out", selected_pjp, f"{start_year}-{end_year}")
        else:
            st.error("Tidak terdapat Data Nasional dari tahun yang dipilih")
else:
    st.warning("Please Upload the Main Excel File first in the Summary Section.")
