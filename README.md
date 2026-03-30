# Tools Analisa Data LTDBB (Lembaga Transfer Dana Bukan Bank)

Dokumentasi ini menjelaskan **alur pengolahan data secara end-to-end**: mulai dari data input, pembersihan, agregasi, filtering, perhitungan indikator (YoY, QtQ, MtM, Market Share, average ticket size), sampai ke visualisasi di setiap halaman.

---

## 1. Ringkasan Aplikasi

Tools ini adalah aplikasi Streamlit untuk:

1. Visualisasi transaksi LTDBB PJP LR Jakarta.
2. Analisis pertumbuhan transaksi (quarterly, monthly, yearly).
3. Profil transaksi per PJP.
4. Market share Jakarta vs nasional.
5. Analisis TKM (deteksi transaksi mencurigakan) berbasis model + rule.
6. Kelola data referensi pada database (PJP, negara blacklist/greylist, suspicious person, dll).

Navigasi halaman:

- Summary
- Growth
- Profile
- Market Share
- Analisis TKM
- Kelola Data

---

## 2. Struktur Data Input

## 2.1 Input utama visualisasi

Upload 1 file Excel yang memiliki 2 sheet:

1. `Trx_PJPJKT` (data transaksi PJP Jakarta)
2. `Raw_JKTNasional` (data nasional pembanding)

## 2.2 Kolom utama yang dipakai

Minimal kolom penting (tergantung halaman):

- Dimensi waktu: `Year`, `Quarter`, `Month`
- Identitas PJP: `Nama PJP`, `Kode` (atau varian kode lain)
- Transaksi:
  - `Fin Jumlah Inc`, `Fin Nilai Inc`
  - `Fin Jumlah Out`, `Fin Nilai Out`
  - `Fin Jumlah Dom`, `Fin Nilai Dom`
- Nasional:
  - `Nom Nasional Inc/Out/Dom/Total`
  - `Frek Nasional Inc/Out/Dom/Total`

---

## 3. Alur End-to-End (Input -> Visual)

## 3.1 Load data

Saat file di-upload:

1. Sheet dibaca sesuai konteks (`Trx_PJPJKT` atau `Raw_JKTNasional`).
2. Kolom numerik dinormalisasi robust (mengatasi format seperti:
	- `Rp 1.234,56`
	- `1,234.56`
	- angka sebagai string
	- karakter non-printable).

## 3.2 Normalisasi angka

Konversi numerik dilakukan dengan pendekatan best effort:

- Hilangkan `Rp`, spasi, NBSP.
- Deteksi pola separator:
  - jika ada `.` dan `,` -> asumsi format Indonesia (`.` ribuan, `,` desimal)
  - jika hanya `,` -> evaluasi apakah desimal atau ribuan
  - jika hanya `.` -> evaluasi desimal/ribuan
- Sisakan digit, tanda minus, titik desimal.

## 3.3 Agregasi inti

Data `Trx_PJPJKT` diagregasi menjadi:

- per `Nama PJP, Year, Quarter` (mode quarter)
- atau per `Nama PJP, Year, Quarter, Month` (mode month)

Hasil agregat:

- `Sum of Fin Jumlah Inc/Out/Dom`
- `Sum of Fin Nilai Inc/Out/Dom`
- `Sum of Total Nom = Inc + Out + Dom (nilai)`

## 3.4 Filter waktu dan entitas

Filter yang dipakai lintas halaman:

- PJP (All / spesifik)
- Year (All / spesifik)
- Quarter (All / spesifik)
- Month (All / spesifik)
- Range Year-Quarter kontinu
- Range Year-Month (start-end)

## 3.5 Visualisasi

Setelah data teragregasi & difilter:

- dihitung metrik turunan (growth, share, total, average ticket)
- dikirim ke tabel dan chart Plotly

---

## 4. Aturan Multilicense

Di halaman Summary, Growth, dan Market Share tersedia mode:

- **Termasuk Multilicense**
- **Tanpa Multilicense**

Jika mode **Tanpa Multilicense**, baris transaksi PJP tertentu dikeluarkan bila periodenya sudah melewati tanggal efektif.

Rule aktif:

1. 777930115 - Brankas Teknologi Indonesia - efektif 2024-09-20
2. 777930112 - Durian Pay Indonesia - efektif 2025-06-25
3. 777962497 - Ionpay Network - efektif 2021-07-01
4. 777930038 - Kharisma Catur Mandala - efektif 2021-07-01
5. 777962104 - MCP Indo Utama - efektif 2021-07-01
6. 777930118 - Smart Fintech For You - efektif 2024-04-24

Evaluasi periode:

- jika ada `Month`: pakai akhir bulan
- jika hanya `Quarter`: pakai akhir kuartal
- jika tidak ada keduanya: akhir tahun

---

## 5. Rumus-Rumus Inti

## 5.1 Total nominal transaksi

`Sum of Total Nom = Sum of Fin Nilai Inc + Sum of Fin Nilai Out + Sum of Fin Nilai Dom`

## 5.2 Market share internal (antar PJP pada periode yang sama)

Dipakai di halaman Summary:

`Market Share PJP (%) = (Total Nominal PJP / Total Nominal seluruh PJP pada periode filter) x 100`

## 5.3 Market share Jakarta vs Nasional

Dipakai di halaman Market Share:

`Market Share Jakarta (%) = (Nominal Jakarta / Nominal Nasional) x 100`

dan

`Market Share Frekuensi Jakarta (%) = (Frekuensi Jakarta / Frekuensi Nasional) x 100`

Catatan unit:

- nominal Jakarta ditampilkan dalam **triliun**
- frekuensi ditampilkan dalam **jutaan**

## 5.4 YoY (Year-on-Year)

Untuk data kuartalan:

`YoY (%) = ((Nilai_t - Nilai_{t-4}) / Nilai_{t-4}) x 100`

Implementasi aktual menggunakan pembanding **tahun sebelumnya, kuartal yang sama**.

## 5.5 QtQ (Quarter-to-Quarter)

Untuk data kuartalan:

`QtQ (%) = ((Nilai_t - Nilai_{t-1}) / Nilai_{t-1}) x 100`

`t-1` adalah baris periode sebelumnya setelah urutan waktu.

## 5.6 MtM (Month-to-Month)

Untuk data bulanan:

`MtM (%) = ((Nilai_bulan_ini - Nilai_bulan_lalu) / Nilai_bulan_lalu) x 100`

Jika bulan sebelumnya tidak ada di tahun yang sama, sistem cek Desember tahun sebelumnya.

## 5.7 Average ticket size

`Avg Ticket = Total Nominal / Total Frekuensi`

Dipakai untuk:

- DKI (data Jakarta)
- luar DKI (nasional dikurangi DKI pada scope filter)

## 5.8 Deteksi rata-rata nominal per transaksi tinggi (TKM)

`Rata2 Nominal per Trx = NOMINAL_TRX / FREKUENSI`

Flag jika:

`Rata2 Nominal per Trx > 100.000.000`

---

## 6. Logika Filtering (Detail)

## 6.1 Filter sederhana (Summary/Profile)

Urutan filter umumnya:

1. `Year` (jika bukan All)
2. `Quarter` (jika bukan All)
3. `Month` (jika bukan All)
4. `Nama PJP` (jika bukan All)

## 6.2 Filter range Year-Quarter kontinu (Growth)

Rentang `start_year/start_quarter` sampai `end_year/end_quarter` bersifat **kontinu**:

- baris awal: `Year == start_year` dan `Quarter >= start_quarter`
- baris akhir: `Year == end_year` dan `Quarter <= end_quarter`
- tahun di tengah: semua kuartal ikut

## 6.3 Filter range Year-Month (Profile/Market Share range mode)

Jika beda tahun:

- tahun awal: bulan >= bulan mulai
- tahun akhir: bulan <= bulan akhir
- tahun di tengah: semua bulan

## 6.4 Filter visual-only

Di Growth (overall chart), multiselect “Tampilkan Kuartal” hanya menyaring **tampilan chart**.
Nilai YoY/QtQ tetap nilai hasil hitung asli (tidak dihitung ulang karena hidden periode).

---

## 7. Dokumentasi per Halaman

## 7.1 Summary

Tujuan:

- ringkasan transaksi dan market share antar PJP

Filter:

- Market Share: PJP, Year, Quarter
- Transactions: period mode (Month/Quarter), Year, Month/Quarter
- (opsional) mode multilicense

Proses:

1. Preprocess + agregasi
2. Filter dataset sesuai sidebar
3. Hitung market share internal per PJP
4. Hitung agregasi time series untuk bar chart

Visual utama:

1. **Pie Top-N Market Share PJP**
	- Top 5 + Others
	- basis: `Market Share (%)`

2. **Grouped Bar Chart (Jumlah)**
	- per Month/Quarter
	- seri: Inc/Out/Dom

3. **Grouped Bar Chart (Nilai)**
	- per Month/Quarter
	- seri: Inc/Out/Dom

4. Tabel detail market share + tabel total transaksi

## 7.2 Growth

Tujuan:

- analisis pertumbuhan frekuensi/nominal dengan YoY, QtQ, MtM
- membandingkan periode A vs B
- melihat driver PJP yang mendorong/menahan perubahan

Mode view:

1. Quarterly
2. Monthly
3. Yearly

### A. Quarterly

Output:

- KPI cards (Inc/Out/Dom/Total)
- chart gabungan stacked + growth line
- VS chart (2 kuartal)
- tabel VS market share Jakarta vs nasional
- tabel detail Incoming/Outgoing/Domestik/Total
- detail per PJP per periode

Rumus growth:

- YoY dan QtQ untuk frekuensi + nominal
- total = penjumlahan Inc/Out/Dom

### B. Monthly

Output:

- KPI cards bulanan
- chart gabungan dengan growth MtM
- tabel dan detail per PJP bulanan

Rumus growth:

- MtM untuk frekuensi + nominal
- YoY level detail bulan tertentu juga disajikan di tabel detail tertentu

### C. Yearly

Output:

- KPI tahunan per tahun terpilih
- tabel ringkasan tahunan
- chart yearly stacked + YoY
- chart YTD khusus (2025 Jan-Sep vs pembanding)

Catatan yearly:

- tanda `*` berarti data tahun parsial (kuartal tidak lengkap karena filter)

## 7.3 Profile

Tujuan:

- profil transaksi **per PJP individu** dalam rentang tanggal

Filter:

- pilih PJP
- tahun/bulan mulai
- tahun/bulan akhir

Proses:

1. Ambil data PJP terpilih
2. Agregasi tahunan + bulanan
3. Hitung kontribusi terhadap nasional (jumlah dan nilai)
4. Hitung growth data PJP (quarterly)

Output:

- tabel kontribusi PJP vs nasional (Incoming/Outgoing/Domestik)
- tabel bulanan per arus + grand total
- tabel pertumbuhan (total + breakdown)
- download CSV per kategori
- chart kombinasi bar (nominal) + line (frekuensi)

## 7.4 Market Share

Tujuan:

- market share Jakarta terhadap nasional (per arus dan total)

Filter:

- mode multilicense
- profile filter: start/end year, start/end month
- quarter tertentu
- mode filter: Quarter / Range

Proses:

1. Siapkan scope data (Quarter atau Range)
2. Hitung average ticket DKI vs luar DKI
3. Hitung market share untuk:
	- Outgoing
	- Incoming
	- Domestik
	- Total
4. Hitung juga versi All-Time

Visual:

- tabel market share per kategori
- pie Jakarta vs National untuk nominal & frekuensi

## 7.5 Analisis TKM

Tujuan:

- mendeteksi transaksi mencurigakan dari data laporan transaksi

Input:

- pilih tahun-bulan
- upload file transaksi (parquet; multi-file)

Tahapan analisis:

1. Bersihkan teks (normalisasi unicode, buang control chars)
2. Filter PJP DKI berdasarkan referensi DB
3. Tentukan tipe laporan berdasarkan `FORM_NO`:
	- FORMG0001 -> Outgoing
	- FORMG0002 -> Incoming
	- selain itu -> Domestik
4. Pilih model Isolation Forest sesuai tipe transaksi
5. Prediksi anomali:
	- output model `-1` dianggap TKM
6. Tampilkan transaksi TKM
7. Rule-based tambahan:
	- transaksi ke/dari negara greylist
	- transaksi ke/dari negara blacklist
	- nama terduga (sender/receiver)
	- pola fan-out/fan-in nominal mirip per periode
	- rata-rata nominal per transaksi > 100 juta

Kriteria rule penting:

- **Fan-out suspicious**: 1 pengirim -> >1 penerima unik dalam bulan sama, nominal mirip
  - mirip jika `(max-min) < 100.000` atau `< 1% rata-rata` atau identik
- **Fan-in suspicious**: 1 penerima <- >1 pengirim unik, dengan kriteria mirip/identik nominal

Catatan:

- fitur fuzzy matching tersedia di kode, saat ini di-disable (`ENABLE_FUZZY = False`)

## 7.6 Kelola Data

Tujuan:

- CRUD data referensi pada Supabase/PostgREST

Area kelola:

- suspicious person
- country blacklist/greylist
- PJP reference
- city/province/country reference

Semua perubahan memakai dialog konfirmasi sebelum eksekusi.

---

## 8. Mapping Rumus -> Grafik

1. **Pie Summary Top-N**
	- input: `Market Share (%)` per PJP
	- Others = 100% - jumlah top-N

2. **Grouped Bar Summary**
	- sumbu X: Month/Quarter
	- sumbu Y: jumlah atau nilai per arus

3. **Combined Bar+Line Growth (Inc/Out/Dom/Total)**
	- bar: nilai/frekuensi terskala (juta/miliar/triliun)
	- line: YoY & QtQ (atau MtM pada monthly)

4. **VS Quarter chart**
	- bandingkan 2 titik periode
	- delta% = `(B-A)/A x 100`

5. **Overall stacked growth chart**
	- bar stacked Inc/Out/Dom
	- line total YoY dan QtQ (opsional breakdown growth)

6. **Profile chart**
	- bar: nominal (unit adaptif Rp/Ribu/Juta/Miliar/Triliun)
	- line: frekuensi

7. **Market Share pie Jakarta vs National**
	- dua slice: Jakarta vs sisa nasional
	- persen jakarta = hasil market share

---

## 9. Catatan Teknis Penting

1. Data nasional pada beberapa file bersifat pengulangan per baris periodik. Fungsi average ticket punya heuristik agar tidak overcount.
2. Nilai pembagi 0 pada growth/market share ditangani aman (`None/NaN`, tidak dipaksa jadi angka palsu).
3. Untuk validitas growth, urutan waktu sangat penting (Year-Quarter/Year-Month).
4. Beberapa visual memakai unit display berbeda (miliar/triliun/jutaan), tetapi basis angka sumber tetap konsisten dari kolom agregat.

---

## 10. Cara Menjalankan Singkat

1. Aktifkan virtual env.
2. Install dependency dari `requirements.txt`.
3. Jalankan Streamlit app melalui entrypoint utama.
4. Upload file Excel di halaman Summary.
5. Navigasi ke halaman lain untuk analisis lanjutan.

---

## 11. Checklist Validasi Hasil (Praktis)

Saat verifikasi hasil analisis, cek urutan berikut:

1. Sheet input lengkap (`Trx_PJPJKT`, `Raw_JKTNasional`)
2. Kolom waktu valid (`Year`, `Quarter`, `Month`)
3. Mode multilicense sesuai kebutuhan
4. Scope filter (Quarter/Range, start-end) benar
5. Growth pembanding benar:
	- YoY banding kuartal sama tahun lalu
	- QtQ banding kuartal sebelumnya
	- MtM banding bulan sebelumnya
6. Unit tampilan dipahami (juta/miliar/triliun)
7. Untuk market share: pembanding nasional tersedia pada scope sama

---

Jika dibutuhkan, dokumentasi ini bisa dipisah lagi menjadi:

- `docs/01-data-flow.md`
- `docs/02-formulas.md`
- `docs/03-page-by-page.md`

agar maintenance lebih mudah.

