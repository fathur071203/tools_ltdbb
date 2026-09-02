"""Deteksi anomali data LTDBB.

Dua lapis pemeriksaan sengaja dipisah karena tindak lanjutnya berbeda:

1. Kualitas data - dugaan ANGKANYA yang salah (Incoming/Outgoing tertukar,
   nominal tertukar dengan frekuensi, salah satuan, baris ganda, periode
   bolong). Tindak lanjut: konfirmasi/perbaiki laporan.
2. Early warning - dugaan PERILAKUNYA yang berubah (lonjakan, pergeseran
   level, reaktivasi PJP dormant, fragmentasi transaksi). Tindak lanjut:
   pendalaman pengawasan.

Keduanya dikaitkan: lonjakan yang periodenya juga kena temuan kualitas data
ditandai "diduga isu data", supaya analis tidak mengejar lonjakan yang
sebenarnya hanya salah input.

Modul ini tidak meng-import Streamlit supaya bisa dipakai/diuji di luar UI.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from service.formatting import format_id_decimal, format_id_percent, parse_number


TRX_LABEL = {"Inc": "Incoming", "Out": "Outgoing", "Dom": "Domestik"}
VALUE_COL = {k: f"Nilai {k}" for k in TRX_LABEL}
FREQ_COL = {k: f"Jumlah {k}" for k in TRX_LABEL}

# Nama kolom di panel -> nama kolom di sheet Trx_PJPJKT.
SOURCE_COLS = {
    f"{prefix} {k}": f"Fin {prefix} {k}"
    for k in TRX_LABEL
    for prefix in ("Jumlah", "Nilai")
}
PANEL_NUMERIC_COLS = list(SOURCE_COLS.keys())

SEVERITY_ORDER = ["Kritis", "Tinggi", "Sedang", "Rendah"]
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITY_ORDER)}

_BULAN_SINGKAT = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
    7: "Jul", 8: "Agu", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des",
}

DQ_COLUMNS = [
    "Periode", "Label Periode", "Tahun", "Bulan", "Kode", "Nama PJP",
    "Jenis Temuan", "Kolom", "Nilai Dilaporkan", "Dugaan Nilai Benar",
    "Nominal Terdampak", "Skor Keyakinan", "Severitas", "Penjelasan",
    "Rekomendasi",
]

EW_COLUMNS = [
    "Periode", "Label Periode", "Tahun", "Bulan", "Kode", "Nama PJP",
    "Metrik", "Jenis", "Satuan", "Nilai", "Baseline", "Rasio (x)",
    "MtM (%)", "YoY (%)", "Z-Robust", "Level Shift (%)", "Pangsa (%)",
    "Delta Pangsa (pp)", "Arah", "Sinyal", "Skor Risiko", "Severitas",
    "Dugaan Penyebab", "Narasi", "Rekomendasi",
]


@dataclass(frozen=True)
class AnomalyConfig:
    """Ambang deteksi. Semua bisa ditimpa dari UI."""

    # --- materialitas: di bawah ini tidak ditindaklanjuti walau menyimpang ---
    min_nominal: float = 1_000_000_000.0
    min_frekuensi: float = 10.0

    # --- baseline historis per PJP (leave-one-out, robust) ---
    baseline_halfwidth: int = 6
    baseline_halfwidth_wide: int = 24
    min_baseline_obs: int = 4

    # --- dugaan Incoming <-> Outgoing tertukar ---
    swap_share_gap: float = 0.35
    swap_improve_ratio: float = 0.35
    swap_total_tol: float = 0.35

    # --- dugaan nominal <-> frekuensi tertukar ---
    ats_abs_floor: float = 10_000.0
    ats_log_gap: float = 2.0
    ats_swap_tol: float = 0.6
    ats_drift_gap: float = 1.5

    # --- dugaan salah satuan (x1.000 / x1.000.000) ---
    scale_tol: float = 0.4
    scale_pair_tol: float = 0.3
    scale_base_mad: float = 0.25

    # --- nilai stagnan & periode bolong ---
    stale_min_repeat: int = 3
    sudden_zero_history: int = 3

    # --- early warning ---
    ew_window: int = 12
    ew_min_obs: int = 6
    ew_z_threshold: float = 3.0
    ew_level_shift: float = 0.6
    ew_yoy_threshold: float = 1.0
    ew_dormant_months: int = 3
    ew_share_jump_pp: float = 2.0
    ew_min_score: float = 35.0
    ew_seasonal_shrink: float = 3.0
    ew_mad_floor: float = 0.35


PRESETS: dict[str, dict] = {
    "Konservatif": dict(
        min_nominal=5_000_000_000.0,
        swap_share_gap=0.45,
        swap_improve_ratio=0.30,
        ats_log_gap=2.5,
        scale_tol=0.30,
        ew_z_threshold=3.5,
        ew_level_shift=0.8,
        ew_yoy_threshold=1.5,
        ew_min_score=50.0,
    ),
    "Seimbang": dict(),
    "Sensitif": dict(
        min_nominal=200_000_000.0,
        swap_share_gap=0.25,
        swap_improve_ratio=0.45,
        ats_log_gap=1.5,
        scale_tol=0.5,
        ew_z_threshold=2.5,
        ew_level_shift=0.4,
        ew_yoy_threshold=0.6,
        ew_min_score=25.0,
    ),
}


def make_config(preset: str = "Seimbang", **overrides) -> AnomalyConfig:
    base = AnomalyConfig()
    base = replace(base, **PRESETS.get(preset, {}))
    clean = {k: v for k, v in overrides.items() if v is not None}
    return replace(base, **clean) if clean else base


# ---------------------------------------------------------------------------
# Helper umum
# ---------------------------------------------------------------------------

_MONTH_NAMES = {
    "january": 1, "jan": 1, "januari": 1,
    "february": 2, "feb": 2, "februari": 2, "pebruari": 2,
    "march": 3, "mar": 3, "maret": 3,
    "april": 4, "apr": 4,
    "may": 5, "mei": 5,
    "june": 6, "jun": 6, "juni": 6,
    "july": 7, "jul": 7, "juli": 7,
    "august": 8, "aug": 8, "agustus": 8, "agu": 8, "ags": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "oktober": 10, "okt": 10,
    "november": 11, "nov": 11, "nopember": 11,
    "december": 12, "dec": 12, "desember": 12, "des": 12,
}


def _month_to_int(value) -> float:
    """Terima angka maupun nama bulan (Inggris/Indonesia); NaN kalau gagal."""
    if value is None:
        return np.nan
    try:
        if pd.isna(value):
            return np.nan
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        m = int(float(value))
        return m if 1 <= m <= 12 else np.nan

    s = str(value).strip().lower().replace(".", "")
    if not s:
        return np.nan
    try:
        m = int(float(s))
        return m if 1 <= m <= 12 else np.nan
    except ValueError:
        pass
    return _MONTH_NAMES.get(s, np.nan)


def periode_label(year, month) -> str:
    try:
        y = int(year)
        m = int(month)
    except (TypeError, ValueError):
        return "-"
    return f"{_BULAN_SINGKAT.get(m, m)} {y}"


def _mad(arr: np.ndarray) -> float:
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.nan
    return float(np.median(np.abs(finite - np.median(finite))))


def _loo_stats_1d(values: np.ndarray, halfwidth: int, min_obs: int):
    """Median & MAD tetangga tiap titik, TANPA menyertakan titik itu sendiri.

    Titik yang sedang diuji harus dikeluarkan dari baselinenya sendiri; kalau
    ikut dihitung, satu nilai ekstrem akan menarik baseline ke arahnya dan
    justru menyamarkan anomali yang mau dicari.
    """
    n = values.size
    med = np.full(n, np.nan)
    mad = np.full(n, np.nan)
    cnt = np.zeros(n, dtype=np.int64)
    if n == 0:
        return med, mad, cnt

    for i in range(n):
        lo = max(0, i - halfwidth)
        hi = min(n, i + halfwidth + 1)
        neigh = np.concatenate((values[lo:i], values[i + 1:hi]))
        neigh = neigh[np.isfinite(neigh)]
        cnt[i] = neigh.size
        if neigh.size >= min_obs:
            m = float(np.median(neigh))
            med[i] = m
            mad[i] = float(np.median(np.abs(neigh - m)))
    return med, mad, cnt


def loo_stats(values: pd.Series, groups: pd.Series, halfwidth: int, min_obs: int) -> pd.DataFrame:
    """Jalankan :func:`_loo_stats_1d` per PJP. Input harus sudah terurut waktu."""
    v = pd.to_numeric(values, errors="coerce").astype(float)
    med = np.full(len(v), np.nan)
    mad = np.full(len(v), np.nan)
    cnt = np.zeros(len(v), dtype=np.int64)
    arr = v.to_numpy()

    for _, pos in v.groupby(groups, sort=False).indices.items():
        pos = np.asarray(pos)
        m, d, c = _loo_stats_1d(arr[pos], halfwidth, min_obs)
        med[pos] = m
        mad[pos] = d
        cnt[pos] = c

    return pd.DataFrame({"median": med, "mad": mad, "count": cnt}, index=v.index)


def _best_baseline(current: pd.Series, narrow: pd.Series, wide: pd.Series) -> pd.Series:
    """Pilih baseline yang paling 'memaafkan' titik saat ini.

    Baseline sempit menangkap perubahan musiman/level, baseline lebar menangkap
    kebiasaan jangka panjang. Mengambil yang terdekat dengan nilai sekarang
    berarti temuan hanya muncul kalau nilai itu menyimpang dari KEDUANYA.
    """
    n_ok = narrow.notna()
    w_ok = wide.notna()
    dn = (current - narrow).abs()
    dw = (current - wide).abs()
    use_wide = w_ok & (~n_ok | (dw < dn))
    return narrow.where(~use_wide.fillna(False), wide)


def _fmt_rp(value) -> str:
    """Rupiah ringkas dengan pemisah Indonesia."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "-"
    if not np.isfinite(v):
        return "-"
    sign = "-" if v < 0 else ""
    v = abs(v)
    for div, unit in ((1e12, "T"), (1e9, "M"), (1e6, "Jt"), (1e3, "Rb")):
        if v >= div:
            return f"{sign}Rp {format_id_decimal(v / div, decimals=2)} {unit}"
    return f"{sign}Rp {format_id_decimal(v, decimals=0)}"


def _fmt_int(value) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "-"
    if not np.isfinite(v):
        return "-"
    return format_id_decimal(v, decimals=0)


def _fmt_pct(value, decimals: int = 1, show_sign: bool = False) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "-"
    if not np.isfinite(v):
        return "-"
    return format_id_percent(v, decimals=decimals, show_sign=show_sign)


def _severity_from_score(score: float, kritis: float = 80.0, tinggi: float = 60.0,
                         sedang: float = 40.0) -> str:
    if score >= kritis:
        return "Kritis"
    if score >= tinggi:
        return "Tinggi"
    if score >= sedang:
        return "Sedang"
    return "Rendah"


# ---------------------------------------------------------------------------
# Panel bulanan
# ---------------------------------------------------------------------------

def build_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Rapikan sheet Trx_PJPJKT jadi satu baris per PJP per bulan.

    Baris ganda dijumlahkan (dan jumlah baris asalnya dicatat di ``Baris
    Sumber`` supaya bisa dilaporkan sebagai temuan tersendiri).
    """
    empty = pd.DataFrame(columns=[
        "Kode", "Nama PJP", "Year", "MonthNum", "Quarter", "Periode", "Label Periode", "t",
        *PANEL_NUMERIC_COLS, "Nilai Total", "Jumlah Total", "Baris Sumber", "Kolom Kosong",
    ])
    if df is None or len(df) == 0:
        return empty

    work = df.copy()

    for target, source in SOURCE_COLS.items():
        if source in work.columns:
            col = work[source]
            if not pd.api.types.is_numeric_dtype(col):
                col = col.map(parse_number)
            work[target] = pd.to_numeric(col, errors="coerce")
        else:
            work[target] = np.nan

    work["Year"] = pd.to_numeric(work.get("Year"), errors="coerce")
    if "Month" in work.columns:
        work["MonthNum"] = work["Month"].map(_month_to_int)
    elif "Quarter" in work.columns:
        # Tanpa kolom bulan, pakai bulan penutup triwulan sebagai penanda periode.
        work["MonthNum"] = pd.to_numeric(work["Quarter"], errors="coerce") * 3
    else:
        return empty

    work = work[work["Year"].notna() & work["MonthNum"].notna()].copy()
    if work.empty:
        return empty
    work["Year"] = work["Year"].astype(int)
    work["MonthNum"] = work["MonthNum"].astype(int)
    work = work[work["MonthNum"].between(1, 12)]
    if work.empty:
        return empty

    if "Nama PJP" in work.columns:
        work["Nama PJP"] = work["Nama PJP"].astype(str).str.strip()
    else:
        work["Nama PJP"] = "(tanpa nama)"

    if "Kode" in work.columns:
        kode_num = pd.to_numeric(work["Kode"], errors="coerce")
        work["Kode"] = np.where(
            kode_num.notna(),
            kode_num.fillna(0).astype("int64").astype(str),
            work["Kode"].astype(str).str.strip(),
        )
    else:
        work["Kode"] = work["Nama PJP"]

    work["Kolom Kosong"] = work[PANEL_NUMERIC_COLS].isna().sum(axis=1)

    agg_map = {c: "sum" for c in PANEL_NUMERIC_COLS}
    agg_map["Kolom Kosong"] = "sum"
    agg_map["Nama PJP"] = "first"

    keys = ["Kode", "Year", "MonthNum"]
    panel = work.groupby(keys, as_index=False).agg(agg_map)
    sizes = work.groupby(keys, as_index=False).size().rename(columns={"size": "Baris Sumber"})
    panel = panel.merge(sizes, on=keys, how="left")

    panel["Quarter"] = ((panel["MonthNum"] - 1) // 3 + 1).astype(int)
    panel["Periode"] = pd.to_datetime(
        dict(year=panel["Year"], month=panel["MonthNum"], day=1), errors="coerce"
    )
    panel["Label Periode"] = [
        periode_label(y, m) for y, m in zip(panel["Year"], panel["MonthNum"])
    ]
    panel["t"] = panel["Year"] * 12 + panel["MonthNum"]
    panel["Nilai Total"] = panel[[VALUE_COL[k] for k in TRX_LABEL]].fillna(0).sum(axis=1)
    panel["Jumlah Total"] = panel[[FREQ_COL[k] for k in TRX_LABEL]].fillna(0).sum(axis=1)

    return panel.sort_values(["Kode", "t"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Lapis 1: kualitas data
# ---------------------------------------------------------------------------

def _finding(row, jenis: str, kolom: str, nilai, dugaan, terdampak,
             keyakinan: float, severitas: str, penjelasan: str, rekomendasi: str) -> dict:
    return {
        "Periode": row["Periode"],
        "Label Periode": row["Label Periode"],
        "Tahun": int(row["Year"]),
        "Bulan": int(row["MonthNum"]),
        "Kode": row["Kode"],
        "Nama PJP": row["Nama PJP"],
        "Jenis Temuan": jenis,
        "Kolom": kolom,
        "Nilai Dilaporkan": float(nilai) if nilai is not None and np.isfinite(nilai) else np.nan,
        "Dugaan Nilai Benar": float(dugaan) if dugaan is not None and np.isfinite(dugaan) else np.nan,
        "Nominal Terdampak": float(terdampak) if terdampak is not None and np.isfinite(terdampak) else np.nan,
        "Skor Keyakinan": round(float(min(100.0, max(0.0, keyakinan))), 1),
        "Severitas": severitas,
        "Penjelasan": penjelasan,
        "Rekomendasi": rekomendasi,
    }


def _pair_swap_evidence(panel: pd.DataFrame, cfg: AnomalyConfig,
                        a_col: str, b_col: str, floor: float) -> dict:
    """Bukti bahwa dua kolom berpasangan diduga tertukar pada satu periode.

    Ide dasarnya: komposisi A terhadap A+B untuk satu PJP relatif stabil.
    Kalau komposisi bulan ini jauh dari baseline TAPI komposisi cerminnya
    (1 - porsi) justru pas di baseline, nilainya kemungkinan tertukar. Total
    A+B yang tetap utuh memperkuat dugaan itu: tukar posisi tidak mengubah
    total, sedangkan lonjakan riil hampir selalu ikut mengubah total.
    """
    key = panel["Kode"]
    a = panel[a_col].astype(float)
    b = panel[b_col].astype(float)
    tot = a.fillna(0) + b.fillna(0)
    material = tot >= floor
    share = a / tot.where(tot > 0)

    src = share.where(material)
    narrow = loo_stats(src, key, cfg.baseline_halfwidth, cfg.min_baseline_obs)
    wide = loo_stats(src, key, cfg.baseline_halfwidth_wide, cfg.min_baseline_obs)
    base = _best_baseline(share, narrow["median"], wide["median"])

    log_tot = np.log10(tot.where(tot > 0))
    t_narrow = loo_stats(log_tot.where(material), key, cfg.baseline_halfwidth, cfg.min_baseline_obs)
    t_wide = loo_stats(log_tot.where(material), key, cfg.baseline_halfwidth_wide, cfg.min_baseline_obs)
    base_tot = _best_baseline(log_tot, t_narrow["median"], t_wide["median"])

    err_now = (share - base).abs()
    err_swap = ((1.0 - share) - base).abs()

    hit = (
        share.notna() & base.notna() & material
        & (err_now >= cfg.swap_share_gap)
        & (err_swap <= err_now * cfg.swap_improve_ratio)
    ).fillna(False)

    total_ok = ((log_tot - base_tot).abs() <= np.log10(1.0 + cfg.swap_total_tol)).fillna(False)

    return {
        "a": a, "b": b, "total": tot, "share": share, "base": base,
        "err_now": err_now, "err_swap": err_swap, "hit": hit, "total_ok": total_ok,
    }


def _check_swap_inc_out(panel: pd.DataFrame, cfg: AnomalyConfig) -> list[dict]:
    if panel.empty:
        return []

    ev_v = _pair_swap_evidence(panel, cfg, "Nilai Inc", "Nilai Out", cfg.min_nominal)
    ev_f = _pair_swap_evidence(panel, cfg, "Jumlah Inc", "Jumlah Out", cfg.min_frekuensi)

    both = ev_v["hit"] & ev_f["hit"]
    only_v = ev_v["hit"] & ~ev_f["hit"]
    only_f = ev_f["hit"] & ~ev_v["hit"]

    findings: list[dict] = []

    def emit(mask, ev, kolom, jenis, satuan, blok: bool, other=None):
        for idx in panel.index[mask]:
            row = panel.loc[idx]
            share = float(ev["share"].loc[idx])
            base = float(ev["base"].loc[idx])
            err_now = float(ev["err_now"].loc[idx])
            err_swap = float(ev["err_swap"].loc[idx])
            total_ok = bool(ev["total_ok"].loc[idx])

            rasio = err_swap / err_now if err_now > 0 else 0.0
            conf = 40.0 + 25.0 * max(0.0, 1.0 - rasio / max(cfg.swap_improve_ratio, 1e-9))
            if total_ok:
                conf += 15.0
            if blok:
                conf += 20.0

            fmt = _fmt_rp if satuan == "nominal" else _fmt_int
            a_val = float(ev["a"].loc[idx])
            b_val = float(ev["b"].loc[idx])

            penjelasan = (
                f"Porsi Incoming terhadap Incoming+Outgoing pada periode ini "
                f"{_fmt_pct(share * 100)}, sedangkan kebiasaan historis PJP ini "
                f"{_fmt_pct(base * 100)}. Kalau kedua nilai ditukar, porsinya jadi "
                f"{_fmt_pct((1 - share) * 100)} - kembali sejalan baseline. "
                f"Dilaporkan: Inc {fmt(a_val)} vs Out {fmt(b_val)}."
            )
            if total_ok:
                penjelasan += (
                    " Total Incoming+Outgoing tetap setara historis; ini ciri nilai "
                    "yang bertukar posisi, bukan lonjakan riil."
                )
            else:
                penjelasan += (
                    " Total Incoming+Outgoing ikut bergeser dari historis, jadi "
                    "kemungkinan perubahan riil belum bisa dikesampingkan."
                )
            if blok:
                penjelasan += " Pola terbalik yang sama muncul pada kolom nominal DAN frekuensi sekaligus."
            elif other is not None:
                penjelasan += (
                    f" Kolom {other} pada periode yang sama TIDAK ikut terbalik, "
                    "jadi periksa apakah hanya satu kolom yang salah tempat."
                )

            findings.append(_finding(
                row,
                jenis=jenis,
                kolom=kolom,
                nilai=a_val,
                dugaan=b_val,
                terdampak=abs(a_val - b_val) if satuan == "nominal" else float(row["Nilai Total"]),
                keyakinan=conf,
                severitas=_severity_from_score(conf),
                penjelasan=penjelasan,
                rekomendasi=(
                    "Cek sel Excel periode ini: kemungkinan kolom Incoming dan Outgoing "
                    "tertukar saat input. Konfirmasi ke PJP sebelum angka dipakai di publikasi."
                ),
            ))

    emit(both, ev_v, "Nilai Inc <-> Nilai Out", "Incoming/Outgoing tertukar (nominal + frekuensi)", "nominal", True)
    emit(only_v, ev_v, "Nilai Inc <-> Nilai Out", "Incoming/Outgoing tertukar (nominal)", "nominal", False, other="frekuensi")
    emit(only_f, ev_f, "Jumlah Inc <-> Jumlah Out", "Incoming/Outgoing tertukar (frekuensi)", "frekuensi", False, other="nominal")

    return findings


def _check_swap_nominal_volume(panel: pd.DataFrame, cfg: AnomalyConfig) -> list[dict]:
    """Nominal dan frekuensi tertukar pada jenis transaksi yang sama.

    Penanda utamanya rata-rata nilai per transaksi (ATS). Menukar nominal
    dengan frekuensi membalik ATS jadi kebalikannya (1/ATS), jadi kalau
    log ATS periode ini jauh dari baseline tapi negatifnya justru pas, dugaan
    tertukar sangat kuat. Kasus paling telanjang: nominal lebih kecil daripada
    frekuensi, artinya ATS di bawah Rp 1 per transaksi.
    """
    if panel.empty:
        return []

    key = panel["Kode"]
    findings: list[dict] = []

    for k, label in TRX_LABEL.items():
        v = panel[VALUE_COL[k]].astype(float)
        f = panel[FREQ_COL[k]].astype(float)
        both = (v > 0) & (f > 0)

        ats = (v / f.where(f > 0)).where(both)
        log_ats = np.log10(ats.where(ats > 0))

        narrow = loo_stats(log_ats, key, cfg.baseline_halfwidth, cfg.min_baseline_obs)
        wide = loo_stats(log_ats, key, cfg.baseline_halfwidth_wide, cfg.min_baseline_obs)
        base = _best_baseline(log_ats, narrow["median"], wide["median"])

        err_now = (log_ats - base).abs()
        err_swap = (-log_ats - base).abs()

        inverted = both & (v < f)
        below_floor = both & (ats < cfg.ats_abs_floor) & ~inverted
        statistical = (
            both & base.notna()
            & (err_now >= cfg.ats_log_gap)
            & (err_swap <= cfg.ats_swap_tol)
            & ~inverted & ~below_floor
        ).fillna(False)

        # Sisa: ATS melenceng jauh tapi ditukar pun tidak membaik -> bukan
        # tertukar, tapi tetap perlu dicek (kemungkinan salah satu kolom salah).
        drifted = (
            both & base.notna()
            & (err_now >= cfg.ats_drift_gap)
            & ~inverted & ~below_floor & ~statistical
            & ((v >= cfg.min_nominal) | (f >= cfg.min_frekuensi))
        ).fillna(False)

        for mask, jenis, conf_base, sev, is_drift in (
            (inverted, f"Nominal/frekuensi tertukar ({label})", 95.0, "Kritis", False),
            (below_floor, f"Nominal/frekuensi tertukar ({label})", 82.0, "Kritis", False),
            (statistical, f"Nominal/frekuensi tertukar ({label})", 68.0, "Tinggi", False),
            (drifted, f"Nilai per transaksi menyimpang ({label})", 55.0, "Sedang", True),
        ):
            for idx in panel.index[mask]:
                row = panel.loc[idx]
                v_val = float(v.loc[idx])
                f_val = float(f.loc[idx])
                ats_val = v_val / f_val if f_val else np.nan
                base_val = base.loc[idx]
                base_ats = 10 ** float(base_val) if pd.notna(base_val) else np.nan

                conf = conf_base
                if pd.notna(base_val) and not is_drift:
                    conf += min(10.0, 4.0 * float(err_now.loc[idx]))

                if is_drift:
                    penjelasan = (
                        f"Nilai per transaksi {label} periode ini {_fmt_rp(ats_val)} "
                        f"({_fmt_int(f_val)} transaksi senilai {_fmt_rp(v_val)}), "
                        f"sedangkan baseline PJP ini sekitar {_fmt_rp(base_ats)} per transaksi "
                        f"- selisih sekitar {format_id_decimal(10 ** float(err_now.loc[idx]), decimals=0)} kali. "
                        "Menukar kolom nominal dan frekuensi tidak memperbaiki angkanya, "
                        "jadi dugaannya salah satu kolom saja yang keliru."
                    )
                    rekomendasi = (
                        "Cek ulang nominal dan frekuensi periode ini secara terpisah; "
                        "bandingkan dengan laporan bulan sebelum dan sesudahnya."
                    )
                    dugaan = np.nan
                else:
                    penjelasan = (
                        f"Nilai per transaksi {label} periode ini hanya {_fmt_rp(ats_val)} "
                        f"(nominal {_fmt_rp(v_val)} dibagi frekuensi {_fmt_int(f_val)}). "
                    )
                    if pd.notna(base_val):
                        penjelasan += f"Baseline PJP ini sekitar {_fmt_rp(base_ats)} per transaksi. "
                    penjelasan += (
                        f"Kalau kedua kolom ditukar, nominalnya menjadi {_fmt_rp(f_val)} "
                        f"dengan {_fmt_int(v_val)} transaksi, dan nilai per transaksinya "
                        "kembali masuk akal."
                    )
                    if v_val < f_val:
                        penjelasan += (
                            " Nominal yang dilaporkan bahkan lebih kecil daripada jumlah "
                            "transaksinya, yang berarti kurang dari Rp 1 per transaksi."
                        )
                    rekomendasi = (
                        f"Tukar isi kolom Fin Nilai {k} dengan Fin Jumlah {k} untuk periode ini "
                        "setelah dikonfirmasi ke PJP."
                    )
                    dugaan = f_val

                findings.append(_finding(
                    row,
                    jenis=jenis,
                    kolom=f"Nilai {k} <-> Jumlah {k}",
                    nilai=v_val,
                    dugaan=dugaan,
                    terdampak=max(v_val, f_val),
                    keyakinan=conf,
                    severitas=sev,
                    penjelasan=penjelasan,
                    rekomendasi=rekomendasi,
                ))

    return findings


def _check_scale_shift(panel: pd.DataFrame, cfg: AnomalyConfig) -> list[dict]:
    """Dugaan salah satuan: angka ter-input x1.000 atau /1.000 (juga x1 juta).

    Pembedanya dari lonjakan riil ada dua: (a) seri PJP itu sangat stabil di
    sekitar baseline, dan (b) kolom pasangannya tidak ikut bergerak. Nominal
    naik 1.000 kali sementara frekuensi diam di tempat jauh lebih mungkin
    salah satuan daripada pertumbuhan bisnis.
    """
    if panel.empty:
        return []

    key = panel["Kode"]
    findings: list[dict] = []
    pairs = [(VALUE_COL[k], FREQ_COL[k], k, "nominal") for k in TRX_LABEL]
    pairs += [(FREQ_COL[k], VALUE_COL[k], k, "frekuensi") for k in TRX_LABEL]

    for col, pair_col, k, satuan in pairs:
        v = panel[col].astype(float)
        p = panel[pair_col].astype(float)
        floor = cfg.min_nominal if satuan == "nominal" else cfg.min_frekuensi

        lv = np.log10(v.where(v > 0))
        lp = np.log10(p.where(p > 0))

        narrow = loo_stats(lv, key, cfg.baseline_halfwidth, cfg.min_baseline_obs)
        wide = loo_stats(lv, key, cfg.baseline_halfwidth_wide, cfg.min_baseline_obs)
        base = _best_baseline(lv, narrow["median"], wide["median"])
        base_mad = narrow["mad"].fillna(wide["mad"])

        p_narrow = loo_stats(lp, key, cfg.baseline_halfwidth, cfg.min_baseline_obs)
        p_wide = loo_stats(lp, key, cfg.baseline_halfwidth_wide, cfg.min_baseline_obs)
        p_base = _best_baseline(lp, p_narrow["median"], p_wide["median"])

        diff = lv - base
        pair_diff = (lp - p_base).abs()
        stable = (base_mad <= cfg.scale_base_mad).fillna(False)
        pair_stable = (pair_diff <= cfg.scale_pair_tol).fillna(False)
        material = ((v >= floor) | (10 ** base >= floor)).fillna(False)

        for exponent in (3.0, 6.0):
            for direction in (1.0, -1.0):
                target = exponent * direction
                mask = (
                    diff.notna() & stable & material
                    & ((diff - target).abs() <= cfg.scale_tol)
                ).fillna(False)

                for idx in panel.index[mask]:
                    row = panel.loc[idx]
                    v_val = float(v.loc[idx])
                    base_val = 10 ** float(base.loc[idx])
                    faktor = 10 ** target

                    conf = 50.0
                    if bool(pair_stable.loc[idx]):
                        conf += 22.0
                    if float(base_mad.loc[idx]) <= cfg.scale_base_mad / 2:
                        conf += 13.0
                    conf += max(0.0, 10.0 - 20.0 * abs(float(diff.loc[idx]) - target))

                    arah = "lebih besar" if direction > 0 else "lebih kecil"
                    fmt = _fmt_rp if satuan == "nominal" else _fmt_int
                    penjelasan = (
                        f"{col} periode ini {fmt(v_val)}, sekitar "
                        f"{format_id_decimal(10 ** abs(target), decimals=0)} kali {arah} "
                        f"dibanding baseline historis PJP ini ({fmt(base_val)}), "
                        f"padahal seri bulanannya sangat stabil."
                    )
                    if bool(pair_stable.loc[idx]):
                        penjelasan += (
                            f" Kolom pasangannya ({pair_col}) tidak ikut bergerak, "
                            "sehingga polanya lebih mirip salah satuan (mis. angka "
                            "dilaporkan dalam ribuan) daripada perubahan transaksi."
                        )
                    else:
                        penjelasan += (
                            f" Kolom pasangannya ({pair_col}) ikut bergerak, jadi "
                            "perubahan riil masih mungkin - perlu konfirmasi."
                        )

                    findings.append(_finding(
                        row,
                        jenis=f"Dugaan salah satuan ({TRX_LABEL[k]})",
                        kolom=col,
                        nilai=v_val,
                        dugaan=v_val / faktor,
                        terdampak=abs(v_val - v_val / faktor) if satuan == "nominal" else float(row["Nilai Total"]),
                        keyakinan=conf,
                        severitas=_severity_from_score(conf),
                        penjelasan=penjelasan,
                        rekomendasi=(
                            f"Periksa satuan pelaporan {col} periode ini; dugaan nilai "
                            f"seharusnya {fmt(v_val / faktor)}."
                        ),
                    ))

    return findings


def _check_orphan_and_invalid(panel: pd.DataFrame, cfg: AnomalyConfig) -> list[dict]:
    """Nilai tanpa pasangan, angka negatif, frekuensi pecahan, sel kosong."""
    if panel.empty:
        return []

    findings: list[dict] = []

    for k, label in TRX_LABEL.items():
        v = panel[VALUE_COL[k]].astype(float)
        f = panel[FREQ_COL[k]].astype(float)

        nominal_tanpa_frek = ((v > 0) & (f.fillna(0) <= 0)).fillna(False)
        frek_tanpa_nominal = ((f > 0) & (v.fillna(0) <= 0)).fillna(False)

        for idx in panel.index[nominal_tanpa_frek]:
            row = panel.loc[idx]
            findings.append(_finding(
                row, f"Nominal tanpa frekuensi ({label})", f"Jumlah {k}",
                nilai=0.0, dugaan=np.nan, terdampak=float(v.loc[idx]),
                keyakinan=85.0, severitas="Tinggi",
                penjelasan=(
                    f"Ada nominal {label} sebesar {_fmt_rp(v.loc[idx])} tetapi frekuensinya "
                    "0. Secara definisi tidak mungkin ada nilai transaksi tanpa transaksi."
                ),
                rekomendasi=f"Lengkapi Fin Jumlah {k} periode ini atau nolkan nominalnya bila salah input.",
            ))

        for idx in panel.index[frek_tanpa_nominal]:
            row = panel.loc[idx]
            findings.append(_finding(
                row, f"Frekuensi tanpa nominal ({label})", f"Nilai {k}",
                nilai=0.0, dugaan=np.nan, terdampak=0.0,
                keyakinan=85.0, severitas="Tinggi",
                penjelasan=(
                    f"Tercatat {_fmt_int(f.loc[idx])} transaksi {label} tetapi nominalnya 0. "
                    "Nominal kemungkinan belum terisi."
                ),
                rekomendasi=f"Lengkapi Fin Nilai {k} periode ini.",
            ))

    for col in PANEL_NUMERIC_COLS:
        s = panel[col].astype(float)
        negatif = (s < 0).fillna(False)
        for idx in panel.index[negatif]:
            row = panel.loc[idx]
            findings.append(_finding(
                row, "Nilai negatif", col,
                nilai=float(s.loc[idx]), dugaan=abs(float(s.loc[idx])),
                terdampak=abs(float(s.loc[idx])),
                keyakinan=100.0, severitas="Kritis",
                penjelasan=(
                    f"{col} bernilai negatif ({format_id_decimal(s.loc[idx], decimals=0)}). "
                    "Nominal maupun frekuensi transaksi tidak boleh negatif."
                ),
                rekomendasi="Telusuri koreksi/pembalikan yang mungkin salah tanda pada sumber data.",
            ))

    for k, label in TRX_LABEL.items():
        f = panel[FREQ_COL[k]].astype(float)
        pecahan = (f.notna() & (f % 1 != 0)).fillna(False)
        for idx in panel.index[pecahan]:
            row = panel.loc[idx]
            findings.append(_finding(
                row, f"Frekuensi bukan bilangan bulat ({label})", f"Jumlah {k}",
                nilai=float(f.loc[idx]), dugaan=float(round(f.loc[idx])),
                terdampak=float(row["Nilai Total"]),
                keyakinan=70.0, severitas="Sedang",
                penjelasan=(
                    f"Frekuensi {label} tercatat {format_id_decimal(f.loc[idx], decimals=4)}. "
                    "Jumlah transaksi seharusnya bilangan bulat; angka pecahan biasanya "
                    "sisa formula atau pembagian di spreadsheet."
                ),
                rekomendasi=f"Cek formula pada kolom Fin Jumlah {k} periode ini.",
            ))

    kosong = (panel["Kolom Kosong"].fillna(0) > 0)
    for idx in panel.index[kosong]:
        row = panel.loc[idx]
        findings.append(_finding(
            row, "Sel nilai final kosong", "Fin Jumlah/Nilai",
            nilai=np.nan, dugaan=np.nan, terdampak=float(row["Nilai Total"]),
            keyakinan=60.0, severitas="Sedang",
            penjelasan=(
                f"Ada {int(row['Kolom Kosong'])} sel kolom final (Fin ...) yang kosong "
                "atau tidak terbaca sebagai angka pada periode ini. Sel kosong dihitung "
                "sebagai nol di seluruh agregasi, sehingga bisa menurunkan total tanpa terlihat."
            ),
            rekomendasi="Isi sel yang kosong atau pastikan formatnya angka, bukan teks.",
        ))

    return findings


def _check_duplicates(panel: pd.DataFrame, cfg: AnomalyConfig) -> list[dict]:
    if panel.empty or "Baris Sumber" not in panel.columns:
        return []

    findings: list[dict] = []
    ganda = (panel["Baris Sumber"].fillna(1) > 1)
    for idx in panel.index[ganda]:
        row = panel.loc[idx]
        n = int(row["Baris Sumber"])
        findings.append(_finding(
            row, "Baris ganda pada periode yang sama", "Kode + Year + Month",
            nilai=float(n), dugaan=1.0, terdampak=float(row["Nilai Total"]),
            keyakinan=75.0, severitas="Tinggi",
            penjelasan=(
                f"Ada {n} baris untuk PJP dan periode yang sama di sheet sumber. "
                "Nilainya dijumlahkan pada panel ini, tetapi kalau baris-baris itu "
                "sebenarnya duplikat (bukan pecahan produk), totalnya jadi dihitung ganda."
            ),
            rekomendasi="Pastikan baris tersebut memang rincian berbeda, bukan salinan; hapus bila duplikat.",
        ))
    return findings


def _check_stale_values(panel: pd.DataFrame, cfg: AnomalyConfig) -> list[dict]:
    """Nominal identik persis beberapa bulan berturut-turut (dugaan salin-tempel)."""
    if panel.empty:
        return []

    findings: list[dict] = []
    for k, label in TRX_LABEL.items():
        col = VALUE_COL[k]
        for kode, sub in panel.groupby("Kode", sort=False):
            values = sub[col].astype(float).to_numpy()
            idxs = sub.index.to_numpy()
            n = len(values)
            i = 0
            while i < n:
                j = i
                while (
                    j + 1 < n
                    and np.isfinite(values[j + 1])
                    and np.isfinite(values[i])
                    and values[j + 1] == values[i]
                ):
                    j += 1
                run = j - i + 1
                if run >= cfg.stale_min_repeat and np.isfinite(values[i]) and values[i] >= cfg.min_nominal:
                    row = panel.loc[idxs[i]]
                    akhir = panel.loc[idxs[j]]
                    findings.append(_finding(
                        row, f"Nilai stagnan berulang ({label})", col,
                        nilai=float(values[i]), dugaan=np.nan,
                        terdampak=float(values[i]) * run,
                        keyakinan=50.0 + min(30.0, 8.0 * (run - cfg.stale_min_repeat + 1)),
                        severitas="Sedang" if run < 5 else "Tinggi",
                        penjelasan=(
                            f"Nominal {label} bernilai persis sama ({_fmt_rp(values[i])}) "
                            f"selama {run} bulan berturut-turut, "
                            f"{row['Label Periode']} s.d. {akhir['Label Periode']}. "
                            "Nilai transaksi yang identik sampai satuan rupiah selama "
                            "beberapa periode hampir selalu salin-tempel atau laporan "
                            "yang belum diperbarui."
                        ),
                        rekomendasi="Konfirmasi ke PJP apakah angka periode-periode tersebut sudah diperbarui.",
                    ))
                i = j + 1
    return findings


def _check_period_gaps(panel: pd.DataFrame, cfg: AnomalyConfig) -> list[dict]:
    """Bulan yang hilang dan pelaporan nihil mendadak di tengah masa aktif."""
    if panel.empty:
        return []

    findings: list[dict] = []
    for kode, sub in panel.groupby("Kode", sort=False):
        sub = sub.sort_values("t")
        aktif = sub[sub["Nilai Total"].fillna(0) > 0]
        if aktif.empty:
            continue
        t_min, t_max = int(aktif["t"].min()), int(aktif["t"].max())
        ada = set(sub.loc[sub["t"].between(t_min, t_max), "t"].astype(int))
        hilang = sorted(set(range(t_min, t_max + 1)) - ada)

        nama = str(sub["Nama PJP"].iloc[0])
        for start, length in _consecutive_runs(hilang):
            end = start + length - 1
            y0, m0 = _t_to_year_month(start)
            y1, m1 = _t_to_year_month(end)
            pseudo = {
                "Periode": pd.Timestamp(year=y0, month=m0, day=1),
                "Label Periode": periode_label(y0, m0),
                "Year": y0, "MonthNum": m0, "Kode": kode, "Nama PJP": nama,
            }
            rentang = (
                periode_label(y0, m0) if length == 1
                else f"{periode_label(y0, m0)} s.d. {periode_label(y1, m1)}"
            )
            findings.append(_finding(
                pseudo, "Periode tidak dilaporkan", "Baris data",
                nilai=np.nan, dugaan=np.nan, terdampak=np.nan,
                keyakinan=70.0, severitas="Tinggi" if length >= 2 else "Sedang",
                penjelasan=(
                    f"Tidak ada baris data untuk {rentang} ({length} bulan), padahal PJP ini "
                    "aktif sebelum dan sesudah periode tersebut. Bulan yang hilang membuat "
                    "pertumbuhan YoY/MtM periode berikutnya ikut menyesatkan."
                ),
                rekomendasi="Lengkapi baris periode yang hilang atau pastikan memang tidak ada kewajiban lapor.",
            ))

        # Nihil mendadak: baris ada tetapi semua nilainya nol di tengah masa aktif.
        nilai = sub.set_index("t")["Nilai Total"].fillna(0)
        for t in sorted(ada):
            if t <= t_min or t >= t_max:
                continue
            if nilai.get(t, 0) > 0:
                continue
            sebelum = [nilai.get(t - i, 0) for i in range(1, cfg.sudden_zero_history + 1)]
            sesudah = nilai.get(t + 1, 0)
            if all(x >= cfg.min_nominal for x in sebelum) and sesudah >= cfg.min_nominal:
                row = sub[sub["t"] == t].iloc[0]
                findings.append(_finding(
                    row, "Pelaporan nihil mendadak", "Seluruh kolom Fin",
                    nilai=0.0, dugaan=float(np.median(sebelum)),
                    terdampak=float(np.median(sebelum)),
                    keyakinan=68.0, severitas="Tinggi",
                    penjelasan=(
                        f"Seluruh nilai transaksi periode ini nol, padahal "
                        f"{cfg.sudden_zero_history} bulan sebelumnya dan bulan sesudahnya "
                        f"tetap material (median sekitar {_fmt_rp(np.median(sebelum))}). "
                        "Pola nol-di-tengah seperti ini lebih sering berarti data belum masuk "
                        "daripada PJP benar-benar berhenti beroperasi satu bulan."
                    ),
                    rekomendasi="Konfirmasi ke PJP apakah memang nihil atau laporannya belum terkirim.",
                ))

    return findings


def _consecutive_runs(values: list[int]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    for v in values:
        if runs and v == runs[-1][0] + runs[-1][1]:
            runs[-1] = (runs[-1][0], runs[-1][1] + 1)
        else:
            runs.append((v, 1))
    return runs


def _t_to_year_month(t: int) -> tuple[int, int]:
    year = (int(t) - 1) // 12
    month = int(t) - year * 12
    return year, month


def detect_data_quality(panel: pd.DataFrame, cfg: AnomalyConfig | None = None) -> pd.DataFrame:
    """Jalankan seluruh pemeriksaan kualitas data, kembalikan tabel temuan."""
    cfg = cfg or AnomalyConfig()
    if panel is None or panel.empty:
        return pd.DataFrame(columns=DQ_COLUMNS)

    findings: list[dict] = []
    findings += _check_swap_inc_out(panel, cfg)
    findings += _check_swap_nominal_volume(panel, cfg)
    findings += _check_scale_shift(panel, cfg)
    findings += _check_orphan_and_invalid(panel, cfg)
    findings += _check_duplicates(panel, cfg)
    findings += _check_stale_values(panel, cfg)
    findings += _check_period_gaps(panel, cfg)

    if not findings:
        return pd.DataFrame(columns=DQ_COLUMNS)

    out = pd.DataFrame(findings)
    out["_rank"] = out["Severitas"].map(SEVERITY_RANK).fillna(len(SEVERITY_ORDER))
    out = out.sort_values(
        ["_rank", "Skor Keyakinan", "Periode"], ascending=[True, False, False]
    ).drop(columns=["_rank"]).reset_index(drop=True)
    return out[DQ_COLUMNS]


# ---------------------------------------------------------------------------
# Lapis 2: early warning transaksi
# ---------------------------------------------------------------------------

EW_METRICS = [
    ("Incoming", "Nominal", "Nilai Inc"),
    ("Incoming", "Frekuensi", "Jumlah Inc"),
    ("Outgoing", "Nominal", "Nilai Out"),
    ("Outgoing", "Frekuensi", "Jumlah Out"),
    ("Domestik", "Nominal", "Nilai Dom"),
    ("Domestik", "Frekuensi", "Jumlah Dom"),
    ("Total", "Nominal", "Nilai Total"),
    ("Total", "Frekuensi", "Jumlah Total"),
]


def _complete_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Isi bulan yang hilang dengan nol, hanya di dalam rentang aktif tiap PJP.

    Deret waktu harus rapat supaya ``shift(1)``/``shift(12)`` benar-benar
    berarti "bulan lalu" dan "tahun lalu". Rentang dibatasi per PJP supaya PJP
    yang baru berdiri tidak dibuatkan puluhan bulan nol di depan yang kemudian
    salah dibaca sebagai reaktivasi dormant.
    """
    if panel.empty:
        return panel

    frames = []
    value_cols = PANEL_NUMERIC_COLS + ["Nilai Total", "Jumlah Total"]
    for kode, sub in panel.groupby("Kode", sort=False):
        t0, t1 = int(sub["t"].min()), int(sub["t"].max())
        full = pd.DataFrame({"t": np.arange(t0, t1 + 1, dtype=int)})
        full["Kode"] = kode
        merged = full.merge(sub.drop(columns=["Kode"]), on="t", how="left")
        merged["Nama PJP"] = merged["Nama PJP"].ffill().bfill()
        merged["Terisi"] = merged["Periode"].notna()
        ym = [_t_to_year_month(t) for t in merged["t"]]
        merged["Year"] = [y for y, _ in ym]
        merged["MonthNum"] = [m for _, m in ym]
        merged["Periode"] = pd.to_datetime(
            dict(year=merged["Year"], month=merged["MonthNum"], day=1), errors="coerce"
        )
        merged["Label Periode"] = [periode_label(y, m) for y, m in ym]
        for c in value_cols:
            merged[c] = merged[c].astype(float).fillna(0.0)
        frames.append(merged)

    return pd.concat(frames, ignore_index=True).sort_values(["Kode", "t"]).reset_index(drop=True)


def _build_long(panel: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for jenis, satuan, col in EW_METRICS:
        sub = panel[["Kode", "Nama PJP", "Year", "MonthNum", "Periode", "Label Periode", "t", "Terisi"]].copy()
        sub["Jenis"] = jenis
        sub["Satuan"] = satuan
        sub["Metrik"] = f"{satuan} {jenis}"
        sub["Nilai"] = panel[col].astype(float)
        frames.append(sub)
    return pd.concat(frames, ignore_index=True)


def _robust_signals(long: pd.DataFrame, group_cols: list[str], cfg: AnomalyConfig) -> pd.DataFrame:
    """Baseline musiman + z-score robust + deteksi pergeseran level.

    Memakai median/MAD, bukan rata-rata/standar deviasi: satu lonjakan besar
    tidak boleh ikut membesarkan ambangnya sendiri. Nilai ditransformasi
    ``log1p`` supaya "naik 5 kali lipat" berbobot sama untuk PJP besar maupun
    kecil.
    """
    out = long.sort_values(group_cols + ["t"]).reset_index(drop=True)
    out["_g"] = out[group_cols].astype(str).agg("|".join, axis=1)

    val = out["Nilai"].astype(float).clip(lower=0)
    out["y"] = np.log1p(val)

    grp = out.groupby("_g", sort=False)["y"]
    center = grp.transform(lambda s: s.rolling(12, min_periods=6, center=True).median())
    resid = out["y"] - center

    # Indeks musiman: rata-rata PJP sendiri di-shrink ke pola bulanan seluruh
    # metrik, supaya PJP dengan riwayat pendek tidak dapat faktor musiman yang
    # dibentuk oleh satu-dua tahun saja.
    met_key = out["Metrik"].astype(str) + "|" + out["MonthNum"].astype(str)
    pjp_key = out["_g"] + "|" + out["MonthNum"].astype(str)
    seas_met = resid.groupby(met_key).transform("median")
    seas_pjp = resid.groupby(pjp_key).transform("median")
    n_pjp = resid.groupby(pjp_key).transform("count").astype(float)
    w = n_pjp / (n_pjp + cfg.ew_seasonal_shrink)
    seas = (w * seas_pjp.fillna(0.0) + (1 - w) * seas_met.fillna(0.0)).fillna(0.0)
    out["y_adj"] = out["y"] - seas

    g2 = out.groupby("_g", sort=False)["y_adj"]
    base = g2.transform(
        lambda s: s.shift(1).rolling(cfg.ew_window, min_periods=cfg.ew_min_obs).median()
    )
    mad = g2.transform(
        lambda s: s.shift(1).rolling(cfg.ew_window, min_periods=cfg.ew_min_obs).apply(_mad, raw=True)
    )
    scale = (1.4826 * mad).clip(lower=cfg.ew_mad_floor)
    out["Baseline"] = np.expm1(base + seas)
    out["Z-Robust"] = (out["y_adj"] - base) / scale

    gv = out.groupby("_g", sort=False)["Nilai"]
    prev1 = gv.shift(1)
    prev12 = gv.shift(12)
    out["MtM (%)"] = np.where(prev1 > 0, (out["Nilai"] / prev1 - 1) * 100, np.nan)
    out["YoY (%)"] = np.where(prev12 > 0, (out["Nilai"] / prev12 - 1) * 100, np.nan)
    out["Nilai Setahun Lalu"] = prev12

    recent = g2.transform(lambda s: s.rolling(3, min_periods=2).median())
    prior = g2.transform(lambda s: s.shift(3).rolling(cfg.ew_window, min_periods=cfg.ew_min_obs).median())
    recent_v = np.expm1(recent)
    prior_v = np.expm1(prior)
    out["Level Shift (%)"] = np.where(prior_v > 0, (recent_v / prior_v - 1) * 100, np.nan)
    out["Level Sebelumnya"] = prior_v

    out["Rasio (x)"] = np.where(out["Baseline"] > 0, out["Nilai"] / out["Baseline"], np.nan)
    return out


def _prev_zero_run(values: pd.Series, groups: pd.Series) -> pd.Series:
    """Berapa bulan nol beruntun tepat sebelum tiap titik."""
    v = values.to_numpy(dtype=float)
    out = np.zeros(len(v), dtype=int)
    for _, pos in values.groupby(groups, sort=False).indices.items():
        run = 0
        for i in np.asarray(pos):
            out[i] = run
            run = run + 1 if (not np.isfinite(v[i]) or v[i] <= 0) else 0
    return pd.Series(out, index=values.index)


def build_ew_signals(panel: pd.DataFrame, cfg: AnomalyConfig | None = None) -> pd.DataFrame:
    """Seluruh deret sinyal early warning, SEBELUM disaring jadi daftar alert.

    Dipisah dari :func:`detect_early_warning` supaya halaman bisa memakai
    frame yang sama untuk grafik drill-down (nilai vs baseline per bulan)
    tanpa menghitung ulang.
    """
    cfg = cfg or AnomalyConfig()
    if panel is None or panel.empty:
        return pd.DataFrame()

    filled = _complete_panel(panel)
    long = _build_long(filled)
    sig = _robust_signals(long, ["Metrik", "Kode"], cfg)

    # Pembanding pasar: agregat seluruh PJP DKI untuk metrik yang sama.
    market = (
        long.groupby(["Metrik", "Jenis", "Satuan", "t", "MonthNum", "Periode", "Label Periode", "Year"],
                     as_index=False)["Nilai"].sum()
    )
    market["Kode"] = "__PASAR__"
    market["Nama PJP"] = "Agregat DKI"
    market["Terisi"] = True
    market_sig = _robust_signals(market, ["Metrik"], cfg)[
        ["Metrik", "t", "Nilai", "Z-Robust", "MtM (%)", "YoY (%)"]
    ].rename(columns={
        "Nilai": "Pasar Nilai", "Z-Robust": "Pasar Z",
        "MtM (%)": "Pasar MtM (%)", "YoY (%)": "Pasar YoY (%)",
    })
    sig = sig.merge(market_sig, on=["Metrik", "t"], how="left")

    sig["Pangsa (%)"] = np.where(
        sig["Pasar Nilai"] > 0, sig["Nilai"] / sig["Pasar Nilai"] * 100, np.nan
    )
    g_share = sig.sort_values(["_g", "t"]).groupby("_g", sort=False)["Pangsa (%)"]
    share_base = g_share.transform(
        lambda s: s.shift(1).rolling(cfg.ew_window, min_periods=cfg.ew_min_obs).median()
    )
    sig["Delta Pangsa (pp)"] = sig["Pangsa (%)"] - share_base

    sig["Nol Beruntun"] = _prev_zero_run(sig["Nilai"], sig["_g"])
    sig["Umur Data"] = sig.groupby("_g", sort=False).cumcount()

    # z metrik pasangan (nominal <-> frekuensi) pada jenis & periode yang sama.
    pasangan = sig[["Kode", "t", "Jenis", "Satuan", "Z-Robust"]].copy()
    pasangan["Satuan"] = pasangan["Satuan"].map({"Nominal": "Frekuensi", "Frekuensi": "Nominal"})
    pasangan = pasangan.rename(columns={"Z-Robust": "Z Pasangan"})
    sig = sig.merge(pasangan, on=["Kode", "t", "Jenis", "Satuan"], how="left")
    return sig


def detect_early_warning(panel: pd.DataFrame, cfg: AnomalyConfig | None = None,
                         dq: pd.DataFrame | None = None,
                         signals: pd.DataFrame | None = None) -> pd.DataFrame:
    """Peringatan dini lonjakan/penurunan transaksi yang substantif."""
    cfg = cfg or AnomalyConfig()
    sig = build_ew_signals(panel, cfg) if signals is None else signals.copy()
    if sig is None or sig.empty:
        return pd.DataFrame(columns=EW_COLUMNS)

    floor = np.where(sig["Satuan"].eq("Nominal"), cfg.min_nominal, cfg.min_frekuensi)
    material = (
        np.maximum(sig["Nilai"].fillna(0), sig["Baseline"].fillna(0)) >= floor
    )

    absz = sig["Z-Robust"].abs()
    level = sig["Level Shift (%)"]
    yoy = sig["YoY (%)"]

    # Setiap pemicu digerbangi materialitas PEMBANDINGNYA, bukan cuma nilai
    # sekarang. Tanpa itu, baseline/pembanding yang nyaris nol membuat rasio
    # meledak (naik 300.000% dari Rp 8 juta) dan alert jadi tidak terpakai.
    rasio = sig["Rasio (x)"]
    base_material = (sig["Baseline"].fillna(0) >= floor)
    trig_spike = (
        (absz >= cfg.ew_z_threshold) & base_material
        & ((rasio >= 2.0) | (rasio <= 0.5))
    ).fillna(False)
    trig_level = (
        (level.abs() >= cfg.ew_level_shift * 100)
        & (sig["Level Sebelumnya"].fillna(0) >= floor)
    ).fillna(False)
    trig_yoy = (
        (yoy.abs() >= cfg.ew_yoy_threshold * 100)
        & (sig["Nilai Setahun Lalu"].fillna(0) >= floor)
    ).fillna(False)
    trig_dormant = (
        (sig["Nol Beruntun"] >= cfg.ew_dormant_months)
        & (sig["Nilai"].fillna(0) >= floor)
    ).fillna(False)
    trig_share = (
        (sig["Delta Pangsa (pp)"] >= cfg.ew_share_jump_pp)
        & (sig["Nilai"].fillna(0) >= floor)
    ).fillna(False)
    trig_baru = (
        (sig["Umur Data"] <= 1) & (sig["Nilai"].fillna(0) >= floor)
    ).fillna(False)
    idiosinkratik = (
        trig_spike & (sig["Pasar Z"].abs() < 1.5).fillna(True)
    )
    divergensi = (
        (absz >= cfg.ew_z_threshold) & (sig["Z Pasangan"].abs() <= 1.0)
    ).fillna(False)

    kandidat = material & (
        trig_spike | trig_level | trig_dormant | trig_baru | (trig_yoy & (absz >= 2.0))
        | (trig_share & (absz >= 2.0))
    )
    sig = sig[kandidat.fillna(False)].copy()
    if sig.empty:
        return pd.DataFrame(columns=EW_COLUMNS)

    sub = lambda s: s.reindex(sig.index)
    absz = sub(absz)
    level = sub(level)
    yoy = sub(yoy)
    trig_spike = sub(trig_spike)
    trig_level = sub(trig_level)
    trig_yoy = sub(trig_yoy)
    trig_dormant = sub(trig_dormant)
    trig_share = sub(trig_share)
    trig_baru = sub(trig_baru)
    idiosinkratik = sub(idiosinkratik)
    divergensi = sub(divergensi)

    score = pd.Series(0.0, index=sig.index)
    score += np.where(
        trig_spike, np.minimum(32.0, 12.0 + 6.0 * (absz - cfg.ew_z_threshold).fillna(0)), 0.0
    )
    score += np.where(trig_level, 18.0, 0.0)
    score += np.where(trig_yoy, 10.0, 0.0)
    score += np.where(idiosinkratik, 14.0, 0.0)
    score += np.where(divergensi, 12.0, 0.0)
    score += np.where(trig_dormant, 14.0, 0.0)
    score += np.where(trig_baru, 8.0, 0.0)
    score += np.where(trig_share, 10.0, 0.0)

    pangsa = sig["Pangsa (%)"].fillna(0).clip(lower=0, upper=100) / 100.0
    score += 12.0 * np.sqrt(pangsa)
    score = score.clip(upper=100.0)

    sig["Skor Risiko"] = score.round(1)
    sig["Severitas"] = [
        _severity_from_score(s, kritis=75.0, tinggi=55.0, sedang=cfg.ew_min_score) for s in score
    ]
    sig["Arah"] = np.where(
        sig["Z-Robust"].fillna(0) >= 0,
        np.where(trig_dormant, "Reaktivasi", "Lonjakan"),
        "Penurunan",
    )

    # Kaitkan dengan temuan kualitas data pada PJP+periode yang sama.
    penyebab = pd.Series("Perubahan substantif", index=sig.index)
    if dq is not None and not dq.empty:
        kuat = dq[dq["Severitas"].isin(["Kritis", "Tinggi"])]
        if not kuat.empty:
            flag = set(zip(kuat["Kode"].astype(str), pd.to_datetime(kuat["Periode"])))
            hit = [
                (str(k), pd.Timestamp(p)) in flag
                for k, p in zip(sig["Kode"].astype(str), sig["Periode"])
            ]
            penyebab = pd.Series(
                np.where(hit, "Diduga isu kualitas data", "Perubahan substantif"),
                index=sig.index,
            )
    sig["Dugaan Penyebab"] = penyebab

    sinyal = []
    narasi = []
    rekomendasi = []
    for idx in sig.index:
        row = sig.loc[idx]
        tags = []
        kalimat = []
        satuan = row["Satuan"]
        fmt = _fmt_rp if satuan == "Nominal" else _fmt_int
        arah_kata = "naik" if row["Z-Robust"] >= 0 else "turun"

        if trig_spike.loc[idx]:
            tags.append("Lonjakan statistik" if row["Z-Robust"] >= 0 else "Penurunan statistik")
            kalimat.append(
                f"{row['Metrik']} periode ini {fmt(row['Nilai'])}, "
                f"{format_id_decimal(row['Rasio (x)'], decimals=2)} kali baseline musimannya "
                f"({fmt(row['Baseline'])}); simpangan robust {format_id_decimal(row['Z-Robust'], decimals=1)} sigma."
            )
        if trig_level.loc[idx]:
            tags.append("Pergeseran level")
            kalimat.append(
                f"Level tiga bulan terakhir {arah_kata} {_fmt_pct(abs(row['Level Shift (%)']))} "
                "dibanding setahun sebelumnya, jadi ini bukan lonjakan sesaat melainkan "
                "perubahan yang bertahan."
            )
        if trig_yoy.loc[idx] and pd.notna(row["YoY (%)"]):
            tags.append("YoY ekstrem")
            kalimat.append(f"Pertumbuhan tahunan {_fmt_pct(row['YoY (%)'], show_sign=True)}.")
        if idiosinkratik.loc[idx]:
            tags.append("Menyimpang dari pasar")
            kalimat.append(
                "Agregat DKI pada periode yang sama bergerak normal, sehingga perubahan ini "
                "khas PJP tersebut dan bukan efek pasar."
            )
        if divergensi.loc[idx]:
            tags.append("Divergensi nilai vs frekuensi")
            if satuan == "Nominal":
                kalimat.append(
                    "Nominal melonjak tanpa kenaikan frekuensi yang sepadan - nilai rata-rata "
                    "per transaksi membesar tajam, pola yang lazim pada transaksi bernilai besar."
                )
            else:
                kalimat.append(
                    "Frekuensi melonjak tanpa kenaikan nominal yang sepadan - transaksi terpecah "
                    "jadi lebih banyak nominal kecil, pola yang perlu dicek terhadap indikasi structuring."
                )
        if trig_dormant.loc[idx]:
            tags.append("Reaktivasi dormant")
            kalimat.append(
                f"PJP ini nihil {int(row['Nol Beruntun'])} bulan berturut-turut lalu langsung "
                f"melapor {fmt(row['Nilai'])}."
            )
        if trig_baru.loc[idx]:
            tags.append("Pelaporan perdana material")
            kalimat.append("Ini periode pelaporan pertama yang material untuk metrik tersebut.")
        if trig_share.loc[idx] and pd.notna(row["Delta Pangsa (pp)"]):
            tags.append("Pangsa melonjak")
            kalimat.append(
                f"Pangsa terhadap total DKI naik {format_id_decimal(row['Delta Pangsa (pp)'], decimals=2)} "
                f"poin persen menjadi {_fmt_pct(row['Pangsa (%)'], decimals=2)}."
            )

        if row["Dugaan Penyebab"] == "Diduga isu kualitas data":
            kalimat.append(
                "Periode ini juga kena temuan kualitas data berat, jadi verifikasi angkanya "
                "dulu sebelum ditindaklanjuti sebagai lonjakan riil."
            )
            rek = "Verifikasi data periode ini di tab Kualitas Data lebih dulu, baru dalami perilakunya."
        elif row["Severitas"] == "Kritis":
            rek = "Prioritaskan pendalaman: minta rincian transaksi periode ini dan bandingkan dengan profil usaha PJP."
        elif row["Severitas"] == "Tinggi":
            rek = "Masukkan ke daftar pantau; konfirmasi pemicu lonjakan ke PJP."
        else:
            rek = "Cukup dipantau pada siklus pengawasan berikutnya."

        sinyal.append(", ".join(tags) if tags else "-")
        narasi.append(" ".join(kalimat))
        rekomendasi.append(rek)

    sig["Sinyal"] = sinyal
    sig["Narasi"] = narasi
    sig["Rekomendasi"] = rekomendasi
    sig["Tahun"] = sig["Year"].astype(int)
    sig["Bulan"] = sig["MonthNum"].astype(int)

    sig = sig[sig["Skor Risiko"] >= cfg.ew_min_score].copy()
    if sig.empty:
        return pd.DataFrame(columns=EW_COLUMNS)

    # Satu kejadian bisa memicu beberapa metrik sekaligus (Nominal Inc, Nominal
    # Total, Frekuensi Inc, ...). Yang dibutuhkan analis satu baris per PJP per
    # periode per jenis transaksi, diwakili metrik dengan skor tertinggi.
    sig = sig.sort_values("Skor Risiko", ascending=False)
    ada_rincian = set(
        zip(sig.loc[sig["Jenis"].ne("Total"), "Kode"],
            sig.loc[sig["Jenis"].ne("Total"), "Periode"])
    )
    redundan = sig["Jenis"].eq("Total") & np.array(
        [(k, p) in ada_rincian for k, p in zip(sig["Kode"], sig["Periode"])], dtype=bool
    )
    sig = sig[~redundan]
    sig = sig.drop_duplicates(subset=["Kode", "Periode", "Jenis"], keep="first")

    sig["_rank"] = sig["Severitas"].map(SEVERITY_RANK).fillna(len(SEVERITY_ORDER))
    sig = sig.sort_values(
        ["_rank", "Skor Risiko", "Periode"], ascending=[True, False, False]
    ).reset_index(drop=True)

    for col in EW_COLUMNS:
        if col not in sig.columns:
            sig[col] = np.nan
    return sig[EW_COLUMNS]


# ---------------------------------------------------------------------------
# Ringkasan untuk kartu KPI
# ---------------------------------------------------------------------------

def summarize(findings: pd.DataFrame, severity_col: str = "Severitas") -> dict:
    if findings is None or findings.empty:
        return {"total": 0, **{s: 0 for s in SEVERITY_ORDER}, "pjp": 0, "periode": 0}

    counts = findings[severity_col].value_counts()
    return {
        "total": int(len(findings)),
        **{s: int(counts.get(s, 0)) for s in SEVERITY_ORDER},
        "pjp": int(findings["Nama PJP"].nunique()),
        "periode": int(findings["Periode"].nunique()),
    }


def series_for(panel: pd.DataFrame, kode: str, column: str) -> pd.DataFrame:
    """Deret bulanan satu PJP untuk grafik drill-down."""
    if panel is None or panel.empty:
        return pd.DataFrame(columns=["Periode", "Label Periode", "Nilai"])
    sub = panel[panel["Kode"].astype(str) == str(kode)].sort_values("t")
    if sub.empty or column not in sub.columns:
        return pd.DataFrame(columns=["Periode", "Label Periode", "Nilai"])
    return pd.DataFrame({
        "Periode": sub["Periode"].to_numpy(),
        "Label Periode": sub["Label Periode"].to_numpy(),
        "Nilai": sub[column].astype(float).to_numpy(),
    })
