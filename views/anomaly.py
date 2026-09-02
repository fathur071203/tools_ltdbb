import pandas as pd
import streamlit as st

from service.preprocess import set_page_visuals
from service.visualize import (
    make_anomaly_timeline_chart,
    make_anomaly_type_chart,
    make_ew_series_chart,
    make_swap_inspect_chart,
)
from service.anomaly import (
    EW_METRICS,
    PRESETS,
    SEVERITY_ORDER,
    build_ew_signals,
    build_panel,
    detect_data_quality,
    detect_early_warning,
    make_config,
    summarize,
)


# ---------------------------------------------------------------------------
# Perhitungan berat -> cache supaya ganti filter tampilan tidak menghitung ulang
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _panel(df: pd.DataFrame) -> pd.DataFrame:
    return build_panel(df)


@st.cache_data(show_spinner=False)
def _data_quality(panel: pd.DataFrame, cfg_key: tuple) -> pd.DataFrame:
    return detect_data_quality(panel, make_config(**dict(cfg_key)))


@st.cache_data(show_spinner=False)
def _signals(panel: pd.DataFrame, cfg_key: tuple) -> pd.DataFrame:
    return build_ew_signals(panel, make_config(**dict(cfg_key)))


@st.cache_data(show_spinner=False)
def _early_warning(panel: pd.DataFrame, signals: pd.DataFrame, dq: pd.DataFrame,
                   cfg_key: tuple) -> pd.DataFrame:
    return detect_early_warning(panel, make_config(**dict(cfg_key)), dq=dq, signals=signals)


def _apply_view_filters(df: pd.DataFrame, tahun_range, pjp_terpilih, severitas) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df
    if tahun_range:
        out = out[out["Tahun"].between(tahun_range[0], tahun_range[1])]
    if pjp_terpilih:
        out = out[out["Nama PJP"].isin(pjp_terpilih)]
    if severitas:
        out = out[out["Severitas"].isin(severitas)]
    return out


def _kpi_row(ringkasan: dict, label_total: str) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(label_total, f"{ringkasan['total']:,}".replace(",", "."))
    c2.metric("Kritis", f"{ringkasan['Kritis']:,}".replace(",", "."))
    c3.metric("Tinggi", f"{ringkasan['Tinggi']:,}".replace(",", "."))
    c4.metric("PJP terdampak", f"{ringkasan['pjp']:,}".replace(",", "."))
    c5.metric("Periode terdampak", f"{ringkasan['periode']:,}".replace(",", "."))


_WARNA_SEVERITAS = {
    "Kritis": "background-color: #fee2e2; color: #7f1d1d; font-weight: 600;",
    "Tinggi": "background-color: #ffedd5; color: #7c2d12; font-weight: 600;",
    "Sedang": "background-color: #fef9c3; color: #713f12;",
    "Rendah": "background-color: #f1f5f9; color: #334155;",
}


def _style_severity(df: pd.DataFrame):
    return df.style.map(lambda v: _WARNA_SEVERITAS.get(v, ""), subset=["Severitas"])


# ---------------------------------------------------------------------------
# Halaman
# ---------------------------------------------------------------------------

set_page_visuals("anomali")

df_source = st.session_state.get("df")
if df_source is None:
    st.warning("Unggah dulu file Excel utama di halaman Summary, baru halaman ini bisa dipakai.")
    st.stop()

panel = _panel(df_source)
if panel.empty:
    st.error("Data tidak bisa dibentuk menjadi panel bulanan (kolom Year/Month tidak terbaca).")
    st.stop()

with st.sidebar:
    with st.expander("Sensitivitas Deteksi", True):
        preset = st.radio(
            "Preset ambang",
            options=list(PRESETS.keys()),
            index=list(PRESETS.keys()).index("Seimbang"),
            key="anomaly_preset",
            help=(
                "Konservatif = hanya temuan yang sangat meyakinkan. "
                "Sensitif = jaring lebih lebar, konsekuensinya lebih banyak temuan untuk disaring manual."
            ),
        )
        if st.session_state.get("_anomaly_preset_prev") != preset:
            # Ganti preset harus ikut mengubah nilai turunannya; tanpa ini
            # widget ber-key mempertahankan angka preset sebelumnya.
            st.session_state.pop("anomaly_min_nominal", None)
            st.session_state.pop("anomaly_z", None)
            st.session_state["_anomaly_preset_prev"] = preset

        batas_juta = st.number_input(
            "Batas materialitas nominal (Rp juta)",
            min_value=0.0,
            value=float(make_config(preset).min_nominal / 1_000_000),
            step=100.0,
            key="anomaly_min_nominal",
            help="Periode dengan nominal di bawah batas ini tidak dilaporkan walaupun menyimpang.",
        )
        z_ambang = st.slider(
            "Ambang lonjakan (sigma robust)",
            min_value=2.0, max_value=6.0, step=0.5,
            value=float(make_config(preset).ew_z_threshold),
            key="anomaly_z",
            help="Semakin tinggi, semakin sedikit lonjakan yang dianggap layak peringatan.",
        )

cfg_key = (
    ("preset", preset),
    ("min_nominal", float(batas_juta) * 1_000_000),
    ("ew_z_threshold", float(z_ambang)),
)

with st.spinner("Menghitung deteksi anomali..."):
    dq = _data_quality(panel, cfg_key)
    signals = _signals(panel, cfg_key)
    ew = _early_warning(panel, signals, dq, cfg_key)

tahun_min = int(panel["Year"].min())
tahun_max = int(panel["Year"].max())
default_awal = max(tahun_min, tahun_max - 2)

with st.sidebar:
    with st.expander("Filter Tampilan", True):
        if tahun_min < tahun_max:
            tahun_range = st.slider(
                "Rentang tahun",
                min_value=tahun_min, max_value=tahun_max,
                value=(default_awal, tahun_max),
                key="anomaly_tahun",
            )
        else:
            tahun_range = (tahun_min, tahun_max)
            st.caption(f"Data hanya tersedia untuk tahun {tahun_min}.")

        pjp_terpilih = st.multiselect(
            "PJP (kosongkan untuk semua)",
            options=sorted(panel["Nama PJP"].dropna().unique().tolist()),
            key="anomaly_pjp",
        )
        severitas = st.multiselect(
            "Severitas",
            options=SEVERITY_ORDER,
            default=["Kritis", "Tinggi"],
            key="anomaly_severitas",
        )

dq_view = _apply_view_filters(dq, tahun_range, pjp_terpilih, severitas)
ew_view = _apply_view_filters(ew, tahun_range, pjp_terpilih, severitas)

tab_dq, tab_ew, tab_doc = st.tabs([
    "🧪 Kualitas Data", "🚨 Early Warning Transaksi", "📘 Metodologi",
])


# ---------------------------------------------------------------------------
# Tab 1 - kualitas data
# ---------------------------------------------------------------------------
with tab_dq:
    st.markdown("#### Dugaan angka yang keliru, bukan perilaku yang berubah")
    st.caption(
        "Temuan di sini menandai baris yang angkanya patut diragukan: Incoming/Outgoing "
        "tertukar, nominal tertukar dengan frekuensi, salah satuan, baris ganda, atau "
        "periode yang tidak dilaporkan. Perbaiki di sini dulu sebelum angkanya dipakai "
        "untuk analisis pertumbuhan maupun publikasi."
    )

    _kpi_row(summarize(dq_view), "Total temuan")

    if dq_view.empty:
        st.success("Tidak ada temuan kualitas data pada filter yang dipilih.")
    else:
        c1, c2 = st.columns([1.1, 1])
        with c1:
            make_anomaly_timeline_chart(
                dq_view, "Sebaran temuan kualitas data per bulan", key="dq_timeline"
            )
        with c2:
            make_anomaly_type_chart(
                dq_view, "Jenis Temuan", "Jenis temuan terbanyak", key="dq_types"
            )

        jenis_opsi = sorted(dq_view["Jenis Temuan"].unique().tolist())
        jenis_pilih = st.multiselect(
            "Saring jenis temuan", options=jenis_opsi, key="dq_jenis_filter"
        )
        tabel = dq_view[dq_view["Jenis Temuan"].isin(jenis_pilih)] if jenis_pilih else dq_view

        kolom_tampil = [
            "Label Periode", "Nama PJP", "Jenis Temuan", "Kolom", "Nilai Dilaporkan",
            "Dugaan Nilai Benar", "Skor Keyakinan", "Severitas", "Penjelasan", "Rekomendasi",
        ]
        st.dataframe(
            _style_severity(tabel[kolom_tampil].reset_index(drop=True)),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Label Periode": st.column_config.TextColumn("Periode", width="small"),
                "Nilai Dilaporkan": st.column_config.NumberColumn("Nilai Dilaporkan", format="%.0f"),
                "Dugaan Nilai Benar": st.column_config.NumberColumn("Dugaan Nilai Benar", format="%.0f"),
                "Skor Keyakinan": st.column_config.NumberColumn("Keyakinan", format="%.0f"),
                "Penjelasan": st.column_config.TextColumn("Penjelasan", width="large"),
                "Rekomendasi": st.column_config.TextColumn("Rekomendasi", width="medium"),
            },
        )

        st.divider()
        st.markdown("##### Periksa satu temuan secara visual")
        st.caption(
            "Kalau nilainya memang tertukar, batang Incoming dan Outgoing akan terlihat "
            "bertukar tempat persis pada periode yang disorot."
        )

        tabel_periksa = tabel.reset_index(drop=True)
        opsi = [
            f"{i + 1}. {r['Nama PJP']} - {r['Label Periode']} - {r['Jenis Temuan']}"
            for i, r in tabel_periksa.iterrows()
        ]
        if opsi:
            pilihan = st.selectbox("Pilih temuan", options=opsi, key="dq_drill")
            baris = tabel_periksa.iloc[opsi.index(pilihan)]

            satuan = "Frekuensi" if "frekuensi" in str(baris["Jenis Temuan"]).lower() else "Nominal"
            kol_inc = "Jumlah Inc" if satuan == "Frekuensi" else "Nilai Inc"
            kol_out = "Jumlah Out" if satuan == "Frekuensi" else "Nilai Out"

            t_pusat = int(baris["Tahun"]) * 12 + int(baris["Bulan"])
            deret = panel[
                (panel["Kode"] == baris["Kode"])
                & panel["t"].between(t_pusat - 8, t_pusat + 8)
            ].sort_values("t")

            if deret.empty:
                st.info("Deret pembanding tidak tersedia untuk temuan ini.")
            else:
                make_swap_inspect_chart(
                    pd.DataFrame({
                        "Label Periode": deret["Label Periode"].to_numpy(),
                        "Incoming": deret[kol_inc].to_numpy(),
                        "Outgoing": deret[kol_out].to_numpy(),
                    }),
                    sorot_periode=baris["Label Periode"],
                    judul=f"{baris['Nama PJP']} - Incoming vs Outgoing ({satuan})",
                    key="dq_inspect",
                    satuan=satuan,
                )
                st.info(f"**{baris['Jenis Temuan']}** - {baris['Penjelasan']}")
                st.caption(f"Tindak lanjut: {baris['Rekomendasi']}")


# ---------------------------------------------------------------------------
# Tab 2 - early warning
# ---------------------------------------------------------------------------
with tab_ew:
    st.markdown("#### Peringatan dini perubahan perilaku transaksi")
    st.caption(
        "Setiap PJP dibandingkan dengan kebiasaannya sendiri (baseline musiman, median "
        "dan MAD 12 bulan), lalu disilangkan dengan pergerakan agregat DKI. Lonjakan yang "
        "periodenya juga kena temuan kualitas data berat ditandai khusus supaya tidak "
        "dikejar sebagai lonjakan riil sebelum angkanya diverifikasi."
    )

    _kpi_row(summarize(ew_view), "Total peringatan")

    if not ew_view.empty:
        diduga_data = int((ew_view["Dugaan Penyebab"] == "Diduga isu kualitas data").sum())
        if diduga_data:
            st.warning(
                f"{diduga_data} dari {len(ew_view)} peringatan berada pada periode yang juga "
                "kena temuan kualitas data berat. Verifikasi angkanya di tab Kualitas Data lebih dulu."
            )

    if ew_view.empty:
        st.success("Tidak ada peringatan dini pada filter yang dipilih.")
    else:
        c1, c2 = st.columns([1.1, 1])
        with c1:
            make_anomaly_timeline_chart(
                ew_view, "Sebaran peringatan per bulan", key="ew_timeline"
            )
        with c2:
            make_anomaly_type_chart(
                ew_view, "Metrik", "Metrik yang paling sering memicu", key="ew_metrics"
            )

        c3, c4 = st.columns(2)
        with c3:
            arah_pilih = st.multiselect(
                "Arah perubahan",
                options=sorted(ew_view["Arah"].unique().tolist()),
                key="ew_arah",
            )
        with c4:
            penyebab_pilih = st.multiselect(
                "Dugaan penyebab",
                options=sorted(ew_view["Dugaan Penyebab"].unique().tolist()),
                key="ew_penyebab",
            )

        tabel_ew = ew_view
        if arah_pilih:
            tabel_ew = tabel_ew[tabel_ew["Arah"].isin(arah_pilih)]
        if penyebab_pilih:
            tabel_ew = tabel_ew[tabel_ew["Dugaan Penyebab"].isin(penyebab_pilih)]

        kolom_ew = [
            "Label Periode", "Nama PJP", "Metrik", "Arah", "Nilai", "Baseline",
            "Rasio (x)", "YoY (%)", "Z-Robust", "Skor Risiko", "Severitas",
            "Dugaan Penyebab", "Sinyal", "Narasi", "Rekomendasi",
        ]
        st.dataframe(
            _style_severity(tabel_ew[kolom_ew].reset_index(drop=True)),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Label Periode": st.column_config.TextColumn("Periode", width="small"),
                "Nilai": st.column_config.NumberColumn("Nilai", format="%.0f"),
                "Baseline": st.column_config.NumberColumn("Baseline", format="%.0f"),
                "Rasio (x)": st.column_config.NumberColumn("Rasio (x)", format="%.2f"),
                "YoY (%)": st.column_config.NumberColumn("YoY (%)", format="%+.1f%%"),
                "Z-Robust": st.column_config.NumberColumn("Sigma", format="%.1f"),
                "Skor Risiko": st.column_config.NumberColumn("Skor", format="%.0f"),
                "Narasi": st.column_config.TextColumn("Narasi", width="large"),
                "Rekomendasi": st.column_config.TextColumn("Rekomendasi", width="medium"),
            },
        )

        st.divider()
        st.markdown("##### Telusuri satu PJP")

        c5, c6 = st.columns(2)
        with c5:
            pjp_drill = st.selectbox(
                "PJP",
                options=sorted(tabel_ew["Nama PJP"].unique().tolist()),
                key="ew_drill_pjp",
            )
        with c6:
            metrik_drill = st.selectbox(
                "Metrik",
                options=[f"{s} {j}" for j, s, _ in EW_METRICS],
                index=[f"{s} {j}" for j, s, _ in EW_METRICS].index("Nominal Total"),
                key="ew_drill_metrik",
            )

        kode_drill = (
            tabel_ew.loc[tabel_ew["Nama PJP"] == pjp_drill, "Kode"].iloc[0]
            if not tabel_ew[tabel_ew["Nama PJP"] == pjp_drill].empty else None
        )

        deret = signals[
            (signals["Kode"] == kode_drill) & (signals["Metrik"] == metrik_drill)
        ].sort_values("t") if kode_drill is not None else pd.DataFrame()

        if deret.empty:
            st.info("Deret untuk kombinasi PJP dan metrik tersebut tidak tersedia.")
        else:
            alert_map = (
                ew[(ew["Kode"] == kode_drill) & (ew["Metrik"] == metrik_drill)]
                .set_index("Periode")["Severitas"]
            )
            deret = deret.assign(
                **{"Severitas Alert": deret["Periode"].map(alert_map)}
            )
            satuan = "Nominal" if metrik_drill.startswith("Nominal") else "Frekuensi"
            make_ew_series_chart(
                deret[["Periode", "Nilai", "Baseline", "Severitas Alert"]],
                judul=f"{pjp_drill} - {metrik_drill}",
                key="ew_series",
                satuan=satuan,
            )

            riwayat = ew[(ew["Kode"] == kode_drill) & (ew["Metrik"] == metrik_drill)]
            if not riwayat.empty:
                for _, r in riwayat.sort_values("Periode", ascending=False).head(5).iterrows():
                    st.markdown(f"**{r['Label Periode']} - {r['Severitas']} (skor {r['Skor Risiko']:.0f})**")
                    st.caption(r["Narasi"])


# ---------------------------------------------------------------------------
# Tab 3 - metodologi
# ---------------------------------------------------------------------------
with tab_doc:
    st.markdown("#### Cara kerja deteksi")
    st.markdown(
        """
Semua pemeriksaan membandingkan satu PJP dengan **kebiasaan PJP itu sendiri**, bukan
dengan rata-rata industri. PJP besar dan PJP kecil karena itu tidak saling menyeret.

Baseline dihitung dengan **median dan MAD**, bukan rata-rata dan standar deviasi:
satu lonjakan besar tidak boleh ikut membesarkan ambangnya sendiri. Titik yang sedang
diuji selalu dikeluarkan dari baselinenya sendiri (*leave-one-out*), dan nilai
ditransformasi `log1p` supaya "naik lima kali lipat" berbobot sama untuk PJP besar
maupun kecil.
        """
    )

    st.markdown("##### Lapis 1 - Kualitas data")
    st.dataframe(
        pd.DataFrame([
            {
                "Pemeriksaan": "Incoming/Outgoing tertukar",
                "Cara deteksi": (
                    "Porsi Incoming terhadap Inc+Out dibandingkan baseline PJP. Ditandai bila "
                    "porsinya jauh menyimpang TAPI porsi cerminnya justru pas di baseline."
                ),
                "Pembeda dari lonjakan riil": (
                    "Menukar dua kolom tidak mengubah total Inc+Out. Total yang tetap utuh "
                    "menaikkan keyakinan; total yang ikut bergeser menurunkannya."
                ),
            },
            {
                "Pemeriksaan": "Nominal tertukar dengan frekuensi",
                "Cara deteksi": (
                    "Rata-rata nilai per transaksi (ATS). Menukar nominal dengan frekuensi "
                    "membalik ATS menjadi 1/ATS, jadi log ATS yang jauh dari baseline tetapi "
                    "negatifnya justru pas adalah bukti kuat."
                ),
                "Pembeda dari lonjakan riil": (
                    "Kasus paling telanjang: nominal lebih kecil daripada jumlah transaksi, "
                    "artinya kurang dari Rp 1 per transaksi."
                ),
            },
            {
                "Pemeriksaan": "Salah satuan (x1.000 / x1.000.000)",
                "Cara deteksi": (
                    "Nilai berada sekitar 10^3 atau 10^6 kali dari baseline, pada seri yang "
                    "riwayat bulanannya sangat stabil."
                ),
                "Pembeda dari lonjakan riil": (
                    "Kolom pasangannya tidak ikut bergerak. Nominal naik 1.000 kali sementara "
                    "frekuensi diam lebih mungkin salah satuan daripada pertumbuhan usaha."
                ),
            },
            {
                "Pemeriksaan": "Nilai tanpa pasangan",
                "Cara deteksi": "Nominal terisi tetapi frekuensi nol, atau sebaliknya.",
                "Pembeda dari lonjakan riil": "Tidak mungkin ada nilai transaksi tanpa transaksi.",
            },
            {
                "Pemeriksaan": "Baris ganda",
                "Cara deteksi": "Lebih dari satu baris untuk kombinasi PJP dan periode yang sama.",
                "Pembeda dari lonjakan riil": (
                    "Kalau baris itu duplikat dan bukan rincian produk, totalnya terhitung ganda."
                ),
            },
            {
                "Pemeriksaan": "Nilai stagnan berulang",
                "Cara deteksi": "Nominal identik sampai satuan rupiah beberapa bulan berturut-turut.",
                "Pembeda dari lonjakan riil": "Pola khas salin-tempel atau laporan yang belum diperbarui.",
            },
            {
                "Pemeriksaan": "Periode bolong & nihil mendadak",
                "Cara deteksi": (
                    "Bulan yang hilang di dalam masa aktif PJP, atau seluruh nilai nol padahal "
                    "bulan sebelum dan sesudahnya material."
                ),
                "Pembeda dari lonjakan riil": (
                    "Bulan yang hilang membuat YoY dan MtM periode berikutnya ikut menyesatkan."
                ),
            },
        ]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("##### Lapis 2 - Early warning transaksi")
    st.dataframe(
        pd.DataFrame([
            {
                "Sinyal": "Lonjakan / penurunan statistik",
                "Dasar": (
                    "Simpangan robust (sigma berbasis MAD) terhadap baseline musiman 12 bulan, "
                    "disyaratkan sekaligus minimal 2x atau maksimal 0,5x baseline."
                ),
                "Bobot": "sampai 32",
            },
            {
                "Sinyal": "Pergeseran level",
                "Dasar": (
                    "Median tiga bulan terakhir dibandingkan median 12 bulan sebelumnya. "
                    "Membedakan lonjakan sesaat dari perubahan yang bertahan."
                ),
                "Bobot": "18",
            },
            {
                "Sinyal": "Menyimpang dari pasar",
                "Dasar": (
                    "PJP melonjak sementara agregat DKI pada bulan yang sama bergerak normal, "
                    "jadi perubahan itu khas PJP tersebut dan bukan efek pasar."
                ),
                "Bobot": "14",
            },
            {
                "Sinyal": "Reaktivasi dormant",
                "Dasar": "Nihil beberapa bulan berturut-turut lalu langsung melapor nilai material.",
                "Bobot": "14",
            },
            {
                "Sinyal": "Divergensi nilai vs frekuensi",
                "Dasar": (
                    "Nominal melonjak tanpa kenaikan frekuensi (nilai per transaksi membesar), "
                    "atau frekuensi melonjak tanpa kenaikan nominal (transaksi terpecah - perlu "
                    "dicek terhadap indikasi structuring)."
                ),
                "Bobot": "12",
            },
            {
                "Sinyal": "Pangsa melonjak",
                "Dasar": "Kenaikan pangsa terhadap total DKI melebihi ambang poin persen.",
                "Bobot": "10",
            },
            {
                "Sinyal": "YoY ekstrem",
                "Dasar": "Pertumbuhan tahunan melampaui ambang, dengan pembanding yang material.",
                "Bobot": "10",
            },
            {
                "Sinyal": "Pelaporan perdana material",
                "Dasar": "Periode pelaporan pertama yang sudah langsung material.",
                "Bobot": "8",
            },
            {
                "Sinyal": "Bobot materialitas",
                "Dasar": "Tambahan proporsional terhadap pangsa PJP pada total DKI.",
                "Bobot": "sampai 12",
            },
        ]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        """
##### Tingkat severitas

| Skor | Severitas | Tindak lanjut |
|---|---|---|
| 75 - 100 | Kritis | Prioritaskan pendalaman pada siklus berjalan |
| 55 - 74 | Tinggi | Masukkan daftar pantau, konfirmasi pemicunya ke PJP |
| ambang - 54 | Sedang | Pantau pada siklus pengawasan berikutnya |

##### Batasan yang perlu diketahui

- Baseline butuh riwayat. PJP dengan data kurang dari enam bulan tidak akan
  menghasilkan sinyal statistik, hanya sinyal pelaporan perdana.
- Faktor musiman dihitung dari pola bulanan PJP sendiri yang ditarik
  (*shrinkage*) ke pola bulanan seluruh metrik, supaya PJP berdata pendek tidak
  mendapat faktor musiman yang dibentuk satu-dua tahun saja.
- Semua temuan adalah **dugaan berbasis pola**, bukan kesimpulan. Kolom
  Keyakinan dan Skor Risiko dipakai untuk mengurutkan prioritas verifikasi,
  bukan menggantikan konfirmasi ke PJP.
        """
    )
