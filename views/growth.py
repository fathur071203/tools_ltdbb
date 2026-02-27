import pandas as pd
import streamlit as st

from service.preprocess import *
from service.visualize import *
from service.formatting import format_en_decimal, format_id_decimal, format_id_percent, qround_float


def _triwulan_label(year: int, quarter: int) -> str:
    roman = {1: "I", 2: "II", 3: "III", 4: "IV"}
    q = roman.get(int(quarter), str(quarter))
    return f"Triwulan {q} - {int(year)}"


def _prev_quarter(year: int, quarter: int) -> tuple[int, int]:
    q = int(quarter)
    y = int(year)
    if q <= 1:
        return y - 1, 4
    return y, q - 1


def _pct_growth(cur: float | None, prev: float | None) -> float | None:
    try:
        c = float(cur) if cur is not None else None
        p = float(prev) if prev is not None else None
    except Exception:
        return None
    if c is None or p is None or p == 0:
        return None
    return (c - p) / p * 100.0


def _fmt_id_decimal(value: float | None, decimals: int = 1) -> str:
    return format_id_decimal(value, decimals=int(decimals), none="-")


def _fmt_id_percent(value: float | None, decimals: int = 2) -> str:
    return format_id_percent(value, decimals=int(decimals), show_sign=True, none="-", space_before_percent=False)


def _pjp_metric_value(
    df_base: pd.DataFrame,
    *,
    year: int,
    quarter: int,
    pjp_name: str,
    flow: str,
    measure: str,
) -> float | None:
    """Get aggregated value for a PJP-period.

    flow: Incoming|Outgoing|Domestik|Total
    measure: Nilai|Jumlah
    """
    if df_base is None or df_base.empty:
        return None
    if not {"Nama PJP", "Year", "Quarter"}.issubset(set(df_base.columns)):
        return None

    dfc = df_base
    cur = dfc[(dfc["Year"].astype(int) == int(year)) & (dfc["Quarter"].astype(int) == int(quarter))]
    if pjp_name:
        cur = cur[cur["Nama PJP"].astype(str) == str(pjp_name)]
    if cur.empty:
        return None

    measure = str(measure)
    flow = str(flow)

    col_map = {
        ("Nilai", "Incoming"): "Sum of Fin Nilai Inc",
        ("Nilai", "Outgoing"): "Sum of Fin Nilai Out",
        ("Nilai", "Domestik"): "Sum of Fin Nilai Dom",
        ("Jumlah", "Incoming"): "Sum of Fin Jumlah Inc",
        ("Jumlah", "Outgoing"): "Sum of Fin Jumlah Out",
        ("Jumlah", "Domestik"): "Sum of Fin Jumlah Dom",
    }

    if flow == "Total":
        cols = [
            col_map.get((measure, "Incoming")),
            col_map.get((measure, "Outgoing")),
            col_map.get((measure, "Domestik")),
        ]
        cols = [c for c in cols if c and c in cur.columns]
        if not cols:
            return None
        return float(pd.to_numeric(cur[cols].sum(axis=1), errors="coerce").fillna(0).sum())

    col = col_map.get((measure, flow))
    if not col or col not in cur.columns:
        return None
    return float(pd.to_numeric(cur[col], errors="coerce").fillna(0).sum())


def _render_pjp_supporting_tw_table(
    *,
    df_base: pd.DataFrame,
    year: int,
    quarter: int,
    key_prefix: str,
) -> None:
    """Render triwulan table for selected PJPs, like: a (same q last year), b (prev q), c (current), QtQ, YoY."""

    st.markdown("**b. PJP LR pendukung utama (TW)**")
    st.caption(
        "Auto-generate: memilih PJP paling berpengaruh untuk Incoming/Domestik/Outgoing, "
        "membentuk Triwulan a/b/c, lalu menghitung QtQ (c/b) dan YoY (c/a)."
    )

    def _series_pjp_value(
        *,
        y: int,
        q: int,
        flow: str,
        measure: str,
    ) -> pd.Series:
        if df_base is None or df_base.empty:
            return pd.Series(dtype=float)
        needed_cols = {"Nama PJP", "Year", "Quarter"}
        if not needed_cols.issubset(set(df_base.columns)):
            return pd.Series(dtype=float)

        dfp = df_base[(df_base["Year"].astype(int) == int(y)) & (df_base["Quarter"].astype(int) == int(q))].copy()
        if dfp.empty:
            return pd.Series(dtype=float)

        flow = str(flow)
        measure = str(measure)

        col_map = {
            ("Nilai", "Incoming"): "Sum of Fin Nilai Inc",
            ("Nilai", "Outgoing"): "Sum of Fin Nilai Out",
            ("Nilai", "Domestik"): "Sum of Fin Nilai Dom",
            ("Jumlah", "Incoming"): "Sum of Fin Jumlah Inc",
            ("Jumlah", "Outgoing"): "Sum of Fin Jumlah Out",
            ("Jumlah", "Domestik"): "Sum of Fin Jumlah Dom",
        }

        if flow == "Total":
            cols = [
                col_map.get((measure, "Incoming")),
                col_map.get((measure, "Outgoing")),
                col_map.get((measure, "Domestik")),
            ]
            cols = [c for c in cols if c and c in dfp.columns]
            if not cols:
                return pd.Series(dtype=float)
            dfp["__val__"] = pd.to_numeric(dfp[cols].sum(axis=1), errors="coerce").fillna(0.0)
        else:
            col = col_map.get((measure, flow))
            if not col or col not in dfp.columns:
                return pd.Series(dtype=float)
            dfp["__val__"] = pd.to_numeric(dfp[col], errors="coerce").fillna(0.0)

        s = dfp.groupby("Nama PJP", observed=False)["__val__"].sum()
        s.index = s.index.astype(str)
        return s

    def _pick_driver_by_direction(*, flow: str, basis: str) -> str | None:
        """Pick a driver PJP that matches total direction.

        If total delta is positive/zero, pick the largest positive delta PJP.
        If total delta is negative, pick the most negative delta PJP.
        Falls back to absolute delta, then to largest current nominal.
        """

        basis_u = str(basis).upper()
        flow = str(flow)

        cur = _series_pjp_value(y=int(year), q=int(quarter), flow=flow, measure="Nilai")
        if basis_u == "YOY":
            prev = _series_pjp_value(y=int(year) - 1, q=int(quarter), flow=flow, measure="Nilai")
        else:
            prev_y, prev_q = _prev_quarter(int(year), int(quarter))
            prev = _series_pjp_value(y=int(prev_y), q=int(prev_q), flow=flow, measure="Nilai")

        if cur.empty and prev.empty:
            return None

        all_idx = cur.index.union(prev.index)
        cur2 = cur.reindex(all_idx).fillna(0.0)
        prev2 = prev.reindex(all_idx).fillna(0.0)
        delta = cur2 - prev2

        total_delta = float(delta.sum())

        if total_delta < 0:
            neg = delta[delta < 0]
            if not neg.empty:
                return str(neg.sort_values(ascending=True).index[0])
        else:
            pos = delta[delta > 0]
            if not pos.empty:
                return str(pos.sort_values(ascending=False).index[0])

        if not delta.empty and float(delta.abs().max()) != 0.0:
            return str(delta.abs().sort_values(ascending=False).index[0])

        if not cur2.empty and float(cur2.max()) != 0.0:
            return str(cur2.sort_values(ascending=False).index[0])

        return None


    def _fmt_tril_id(amount_rp: float | None) -> str:
        if amount_rp is None:
            return "-"
        try:
            v = float(amount_rp) / 1e12
        except Exception:
            return "-"
        return _fmt_id_decimal(v, decimals=2)


    def _fmt_tril_delta_id(amount_rp: float | None) -> str:
        if amount_rp is None:
            return "-"
        try:
            v = float(amount_rp) / 1e12
        except Exception:
            return "-"
        # always positive number in text: "sebesar RpX triliun"
        return _fmt_id_decimal(abs(v), decimals=2)


    def _render_narrative_for_flow(flow: str) -> None:
        flow = str(flow)
        prev_y, prev_q = _prev_quarter(int(year), int(quarter))

        cur_total = _pjp_metric_value(df_base, year=int(year), quarter=int(quarter), pjp_name="", flow=flow, measure="Nilai")
        prevq_total = _pjp_metric_value(df_base, year=int(prev_y), quarter=int(prev_q), pjp_name="", flow=flow, measure="Nilai")
        prevy_total = _pjp_metric_value(df_base, year=int(year) - 1, quarter=int(quarter), pjp_name="", flow=flow, measure="Nilai")

        delta_q = None if (cur_total is None or prevq_total is None) else (cur_total - prevq_total)
        delta_y = None if (cur_total is None or prevy_total is None) else (cur_total - prevy_total)
        pct_q = _pct_growth(cur_total, prevq_total)
        pct_y = _pct_growth(cur_total, prevy_total)

        trend_q = "meningkat" if (delta_q is not None and delta_q >= 0) else "menurun"
        trend_y = "meningkat" if (delta_y is not None and delta_y >= 0) else "menurun"

        # pick drivers that match direction
        driver_q = _pick_driver_by_direction(flow=flow, basis="QtQ")
        driver_y = _pick_driver_by_direction(flow=flow, basis="YoY")

        def _pjp_driver_sentence(pjp: str | None, basis: str) -> str:
            if not pjp:
                return ""
            basis_u = str(basis).upper()
            if basis_u == "YOY":
                y0, q0 = int(year) - 1, int(quarter)
            else:
                y0, q0 = _prev_quarter(int(year), int(quarter))

            v_cur = _pjp_metric_value(df_base, year=int(year), quarter=int(quarter), pjp_name=pjp, flow=flow, measure="Nilai")
            v_prev = _pjp_metric_value(df_base, year=int(y0), quarter=int(q0), pjp_name=pjp, flow=flow, measure="Nilai")
            d = None if (v_cur is None or v_prev is None) else (v_cur - v_prev)
            p = _pct_growth(v_cur, v_prev)

            if d is None:
                return ""
            verb = "peningkatan" if d >= 0 else "penurunan"
            return (
                f"Hal tersebut terutama disebabkan oleh {verb} transaksi dari **{pjp}** "
                f"sebesar Rp{_fmt_tril_delta_id(d)} triliun atau {_fmt_id_percent(p)} ({basis_u})."
            )

        flow_title = {
            "Domestik": "Transaksi Domestik",
            "Incoming": "Transaksi Incoming",
            "Outgoing": "Transaksi Outgoing",
        }.get(flow, f"Transaksi {flow}")

        st.markdown(f"**{flow_title}**")
        if cur_total is None:
            st.info("Data tidak tersedia untuk periode ini.")
            return

        # Main sentence
        st.markdown(
            " ".join(
                [
                    f"Nominal transaksi {flow.lower()} pada {_triwulan_label(int(year), int(quarter))} sebesar Rp{_fmt_tril_id(cur_total)} triliun,",
                    (
                        f"{trend_q} sebesar Rp{_fmt_tril_delta_id(delta_q)} triliun dibandingkan dengan triwulan sebelumnya "
                        f"Rp{_fmt_tril_id(prevq_total)} triliun (QtQ: {_fmt_id_percent(pct_q).replace('+', '')})"
                        if prevq_total is not None and delta_q is not None and pct_q is not None
                        else "(data pembanding triwulan sebelumnya tidak tersedia)"
                    )
                    +
                    " dan ",
                    (
                        f"{trend_y} sebesar Rp{_fmt_tril_delta_id(delta_y)} triliun dibandingkan dengan {_triwulan_label(int(year) - 1, int(quarter))} "
                        f"Rp{_fmt_tril_id(prevy_total)} triliun (YoY: {_fmt_id_percent(pct_y).replace('+', '')})."
                        if prevy_total is not None and delta_y is not None and pct_y is not None
                        else "(data pembanding tahun sebelumnya tidak tersedia)."
                    ),
                ]
            )
        )

        # Driver sentences
        s_q = _pjp_driver_sentence(driver_q, "QtQ")
        s_y = _pjp_driver_sentence(driver_y, "YoY")
        if s_q:
            st.markdown(s_q)
        if s_y and (driver_y != driver_q):
            st.markdown(s_y)

    # Render narrative paragraphs (matching report style)
    _render_narrative_for_flow("Domestik")
    st.markdown("---")
    _render_narrative_for_flow("Incoming")
    st.markdown("---")
    _render_narrative_for_flow("Outgoing")
    st.markdown("---")

    # Auto specs: direction-aware drivers for QtQ and YoY per flow
    chosen: dict[str, dict[str, str | None]] = {
        "Incoming": {
            "QtQ": _pick_driver_by_direction(flow="Incoming", basis="QtQ"),
            "YoY": _pick_driver_by_direction(flow="Incoming", basis="YoY"),
        },
        "Outgoing": {
            "QtQ": _pick_driver_by_direction(flow="Outgoing", basis="QtQ"),
            "YoY": _pick_driver_by_direction(flow="Outgoing", basis="YoY"),
        },
        "Domestik": {
            "QtQ": _pick_driver_by_direction(flow="Domestik", basis="QtQ"),
            "YoY": _pick_driver_by_direction(flow="Domestik", basis="YoY"),
        },
    }

    auto_spec_rows: list[dict] = []
    seen = set()
    for flow in ["Domestik", "Incoming", "Outgoing"]:
        for basis in ["QtQ", "YoY"]:
            pjp = chosen.get(flow, {}).get(basis)
            if not pjp:
                continue
            sig = (str(pjp), str(flow))
            if sig in seen:
                continue
            seen.add(sig)
            auto_spec_rows.append({"Nama PJP": pjp, "Arus": flow, "Ukuran": "Nilai"})

    default_spec = pd.DataFrame(auto_spec_rows)
    if default_spec.empty:
        # Fallback to previous default (keeps UI usable if data missing)
        default_spec = pd.DataFrame(
            [
                {"Nama PJP": "", "Arus": "Domestik", "Ukuran": "Nilai"},
                {"Nama PJP": "", "Arus": "Incoming", "Ukuran": "Nilai"},
                {"Nama PJP": "", "Arus": "Outgoing", "Ukuran": "Nilai"},
            ]
        )

    spec_key = f"{key_prefix}_pjp_tw_spec"
    if spec_key not in st.session_state:
        st.session_state[spec_key] = default_spec

    # Editor (optional override)
    pjp_options = []
    if df_base is not None and not df_base.empty and "Nama PJP" in df_base.columns:
        pjp_options = sorted(df_base["Nama PJP"].dropna().astype(str).unique().tolist())

    with st.expander("Konfigurasi kolom tabel (opsional)", expanded=False):
        left, right = st.columns([3, 2])
        with left:
            spec_df = st.data_editor(
                st.session_state[spec_key],
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Nama PJP": st.column_config.SelectboxColumn(
                        "Nama PJP",
                        options=pjp_options if pjp_options else None,
                        help="Pilih Nama PJP sesuai yang ada di data.",
                    ),
                    "Arus": st.column_config.SelectboxColumn(
                        "Arus",
                        options=["Domestik", "Incoming", "Outgoing", "Total"],
                    ),
                    "Ukuran": st.column_config.SelectboxColumn(
                        "Ukuran",
                        options=["Nilai", "Jumlah"],
                        help="Nilai akan ditampilkan dalam Rp Triliun; Jumlah dalam Jutaan.",
                    ),
                },
                key=f"{key_prefix}_pjp_tw_editor",
            )
        with right:
            treat_zero_as_blank = st.checkbox(
                "Tampilkan 0 sebagai '-'",
                value=True,
                key=f"{key_prefix}_pjp_tw_zero_blank",
                help="Jika nilai 0 (atau tidak ada data), akan ditampilkan '-'.",
            )
            decimals = st.slider(
                "Pembulatan",
                min_value=0,
                max_value=2,
                value=1,
                step=1,
                key=f"{key_prefix}_pjp_tw_decimals",
                help="Jumlah digit desimal untuk nilai (triliun/jutaan).",
            )

    st.session_state[spec_key] = spec_df
    if spec_df is None or spec_df.empty:
        st.info("Tambahkan minimal 1 baris konfigurasi PJP untuk menampilkan tabel.")
        return

    # Define periods (a, b, c)
    a_year, a_q = int(year) - 1, int(quarter)
    b_year, b_q = _prev_quarter(int(year), int(quarter))
    c_year, c_q = int(year), int(quarter)

    rows = [
        (f"a. {_triwulan_label(a_year, a_q)}", (a_year, a_q)),
        (f"b. {_triwulan_label(b_year, b_q)}", (b_year, b_q)),
        (f"c. {_triwulan_label(c_year, c_q)}", (c_year, c_q)),
        ("QtQ (c/b)", None),
        ("YoY (c/a)", None),
    ]

    # Compute raw values for a/b/c, then growth
    col_specs: list[dict] = spec_df.fillna("").to_dict(orient="records")
    raw_a: list[float | None] = []
    raw_b: list[float | None] = []
    raw_c: list[float | None] = []
    col_names: list[str] = []
    col_meta: list[tuple[str, str]] = []  # (measure, flow)

    for s in col_specs:
        pjp = str(s.get("Nama PJP", "")).strip()
        flow = str(s.get("Arus", "Total")).strip() or "Total"
        measure = str(s.get("Ukuran", "Nilai")).strip() or "Nilai"

        display_measure = "Nominal" if measure == "Nilai" else "Frekuensi"
        unit = "Rp Triliun" if measure == "Nilai" else "Jutaan"
        col_name = f"{pjp}\n{display_measure} {flow} ({unit})" if pjp else f"({display_measure} {flow} - {unit})"
        col_names.append(col_name)
        col_meta.append((measure, flow))

        va = _pjp_metric_value(df_base, year=a_year, quarter=a_q, pjp_name=pjp, flow=flow, measure=measure)
        vb = _pjp_metric_value(df_base, year=b_year, quarter=b_q, pjp_name=pjp, flow=flow, measure=measure)
        vc = _pjp_metric_value(df_base, year=c_year, quarter=c_q, pjp_name=pjp, flow=flow, measure=measure)

        raw_a.append(va)
        raw_b.append(vb)
        raw_c.append(vc)

    def _scale(measure: str, value: float | None) -> float | None:
        if value is None:
            return None
        if measure == "Nilai":
            return value / 1e12
        return value / 1e6

    # Build table (as strings to match report formatting)
    table = pd.DataFrame(index=[r[0] for r in rows], columns=col_names)

    for i, (measure, _flow) in enumerate(col_meta):
        a_s = _scale(measure, raw_a[i])
        b_s = _scale(measure, raw_b[i])
        c_s = _scale(measure, raw_c[i])

        if treat_zero_as_blank:
            a_s = None if (a_s is None or a_s == 0) else a_s
            b_s = None if (b_s is None or b_s == 0) else b_s
            c_s = None if (c_s is None or c_s == 0) else c_s

        table.iloc[0, i] = _fmt_id_decimal(a_s, decimals=decimals)
        table.iloc[1, i] = _fmt_id_decimal(b_s, decimals=decimals)
        table.iloc[2, i] = _fmt_id_decimal(c_s, decimals=decimals)

        qtq = _pct_growth(c_s, b_s)
        yoy = _pct_growth(c_s, a_s)
        table.iloc[3, i] = _fmt_id_percent(qtq)
        table.iloc[4, i] = _fmt_id_percent(yoy)

    st.dataframe(table, use_container_width=True)

    # Impact breakdown: show current/prevQ/prevY and deltas for the chosen specs (Nilai preferred)
    impact_rows: list[dict] = []
    prev_y, prev_q = _prev_quarter(int(year), int(quarter))
    for s in col_specs:
        pjp = str(s.get("Nama PJP", "")).strip()
        flow = str(s.get("Arus", "Total")).strip() or "Total"
        measure = str(s.get("Ukuran", "Nilai")).strip() or "Nilai"
        # Only show breakdown for Nilai by default (it matches the report table)
        v_cur = _pjp_metric_value(df_base, year=int(year), quarter=int(quarter), pjp_name=pjp, flow=flow, measure=measure)
        v_prevq = _pjp_metric_value(df_base, year=int(prev_y), quarter=int(prev_q), pjp_name=pjp, flow=flow, measure=measure)
        v_prevy = _pjp_metric_value(df_base, year=int(year) - 1, quarter=int(quarter), pjp_name=pjp, flow=flow, measure=measure)

        def _scale_for_breakdown(val: float | None) -> float | None:
            if val is None:
                return None
            return val / (1e12 if measure == "Nilai" else 1e6)

        cur_s = _scale_for_breakdown(v_cur)
        prevq_s = _scale_for_breakdown(v_prevq)
        prevy_s = _scale_for_breakdown(v_prevy)
        if treat_zero_as_blank:
            cur_s = None if (cur_s is None or cur_s == 0) else cur_s
            prevq_s = None if (prevq_s is None or prevq_s == 0) else prevq_s
            prevy_s = None if (prevy_s is None or prevy_s == 0) else prevy_s

        delta_q = None if (cur_s is None or prevq_s is None) else (cur_s - prevq_s)
        delta_y = None if (cur_s is None or prevy_s is None) else (cur_s - prevy_s)
        impact_rows.append(
            {
                "Arus": flow,
                "Nama PJP": pjp,
                "Current": cur_s,
                "Prev Quarter": prevq_s,
                "Delta QtQ": delta_q,
                "QtQ (%)": _pct_growth(cur_s, prevq_s),
                "Prev Year": prevy_s,
                "Delta YoY": delta_y,
                "YoY (%)": _pct_growth(cur_s, prevy_s),
            }
        )

    if impact_rows:
        unit_label = "Rp Triliun" if any(str(s.get("Ukuran", "")).strip() == "Nilai" for s in col_specs) else "Jutaan"
        impact_df = pd.DataFrame(impact_rows)
        st.markdown("**Komponen nilai & pengaruh (detail QtQ/YoY)**")
        st.caption(
            f"Current = Q{int(quarter)} {int(year)}, Prev Quarter = Q{int(prev_q)} {int(prev_y)}, Prev Year = Q{int(quarter)} {int(year) - 1}. "
            f"Satuan: {unit_label}."
        )

        def _fmt_num_cell(v):
            return _fmt_id_decimal(v, decimals=decimals) if v is not None else "-"

        impact_df_display = impact_df.copy()
        for c in ["Current", "Prev Quarter", "Delta QtQ", "Prev Year", "Delta YoY"]:
            impact_df_display[c] = impact_df_display[c].apply(lambda x: x if pd.notna(x) else None)
            impact_df_display[c] = impact_df_display[c].apply(_fmt_num_cell)
        for c in ["QtQ (%)", "YoY (%)"]:
            impact_df_display[c] = impact_df_display[c].apply(lambda x: x if pd.notna(x) else None)
            impact_df_display[c] = impact_df_display[c].apply(_fmt_id_percent)

        st.dataframe(
            impact_df_display,
            use_container_width=True,
            hide_index=True,
        )

    # Download
    csv = table.reset_index(names=["Periode"]).to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV (tabel TW)",
        data=csv,
        file_name=f"pjp_pendukung_utama_tw_Q{int(quarter)}_{int(year)}.csv",
        mime="text/csv",
        use_container_width=True,
        key=f"{key_prefix}_pjp_tw_download",
    )


def _get_growth_column_config(trx_var: str):
    """
    Mengembalikan column_config untuk st.dataframe agar format tampil dengan benar
    sambil tetap mempertahankan sorting numerik yang benar.
    """
    return {
        "Year": st.column_config.NumberColumn(
            "Year",
            format="%d"
        ),
        "Quarter": st.column_config.NumberColumn(
            "Quarter", 
            format="%d"
        ) if "Quarter" in ["Quarter"] else None,
        f"Total Frekuensi {trx_var}": st.column_config.NumberColumn(
            f"Total Frekuensi {trx_var}",
            format="%.0f"
        ),
        f"Total Nominal {trx_var}": st.column_config.NumberColumn(
            f"Total Nominal {trx_var}",
            format="%.0f"
        ),
        "Year-on-Year Frekuensi": st.column_config.NumberColumn(
            "Year-on-Year Frekuensi",
            format="%+.2f%%"
        ),
        "Quarter-to-Quarter Frekuensi": st.column_config.NumberColumn(
            "Quarter-to-Quarter Frekuensi",
            format="%+.2f%%"
        ),
        "Year-on-Year Nominal": st.column_config.NumberColumn(
            "Year-on-Year Nominal",
            format="%+.2f%%"
        ),
        "Quarter-to-Quarter Nominal": st.column_config.NumberColumn(
            "Quarter-to-Quarter Nominal",
            format="%+.2f%%"
        ),
        "Month-to-Month Frekuensi": st.column_config.NumberColumn(
            "Month-to-Month Frekuensi",
            format="%+.2f%%"
        ),
        "Month-to-Month Nominal": st.column_config.NumberColumn(
            "Month-to-Month Nominal",
            format="%+.2f%%"
        ),
    }


def _render_pjp_detail(df_base: pd.DataFrame, year: int, quarter: int, trx_type: str):
    """Tampilkan detail growth per PJP untuk periode (year, quarter) dan tipe transaksi."""
    col_map_jumlah = {
        "Incoming": "Sum of Fin Jumlah Inc",
        "Outgoing": "Sum of Fin Jumlah Out",
        "Domestik": "Sum of Fin Jumlah Dom",
    }
    col_map_nilai = {
        "Incoming": "Sum of Fin Nilai Inc",
        "Outgoing": "Sum of Fin Nilai Out",
        "Domestik": "Sum of Fin Nilai Dom",
    }

    # Filter current period
    current = df_base[(df_base["Year"] == year) & (df_base["Quarter"] == quarter)].copy()
    if current.empty:
        st.warning("Data tidak ditemukan untuk periode tersebut")
        return

    if trx_type == "Total":
        current["Jumlah"] = (
            current["Sum of Fin Jumlah Inc"]
            + current["Sum of Fin Jumlah Out"]
            + current["Sum of Fin Jumlah Dom"]
        )
        current["Nilai"] = (
            current["Sum of Fin Nilai Inc"]
            + current["Sum of Fin Nilai Out"]
            + current["Sum of Fin Nilai Dom"]
        )
    else:
        current["Jumlah"] = current[col_map_jumlah[trx_type]]
        current["Nilai"] = current[col_map_nilai[trx_type]]

    # Grup per PJP
    cur_group = current.groupby("Nama PJP", observed=False)[["Jumlah", "Nilai"]].sum().reset_index()

    # Prev quarter
    prev_q = quarter - 1 if quarter > 1 else 4
    prev_y = year if quarter > 1 else year - 1
    prev_q_df = df_base[(df_base["Year"] == prev_y) & (df_base["Quarter"] == prev_q)].copy()
    if not prev_q_df.empty:
        if trx_type == "Total":
            prev_q_df["Jumlah"] = (
                prev_q_df["Sum of Fin Jumlah Inc"]
                + prev_q_df["Sum of Fin Jumlah Out"]
                + prev_q_df["Sum of Fin Jumlah Dom"]
            )
            prev_q_df["Nilai"] = (
                prev_q_df["Sum of Fin Nilai Inc"]
                + prev_q_df["Sum of Fin Nilai Out"]
                + prev_q_df["Sum of Fin Nilai Dom"]
            )
        else:
            prev_q_df["Jumlah"] = prev_q_df[col_map_jumlah[trx_type]]
            prev_q_df["Nilai"] = prev_q_df[col_map_nilai[trx_type]]
        prev_q_group = prev_q_df.groupby("Nama PJP", observed=False)[["Jumlah", "Nilai"]].sum().reset_index()
    else:
        prev_q_group = pd.DataFrame(columns=["Nama PJP", "Jumlah", "Nilai"])

    # Prev year same quarter
    prev_y_df = df_base[(df_base["Year"] == year - 1) & (df_base["Quarter"] == quarter)].copy()
    if not prev_y_df.empty:
        if trx_type == "Total":
            prev_y_df["Jumlah"] = (
                prev_y_df["Sum of Fin Jumlah Inc"]
                + prev_y_df["Sum of Fin Jumlah Out"]
                + prev_y_df["Sum of Fin Jumlah Dom"]
            )
            prev_y_df["Nilai"] = (
                prev_y_df["Sum of Fin Nilai Inc"]
                + prev_y_df["Sum of Fin Nilai Out"]
                + prev_y_df["Sum of Fin Nilai Dom"]
            )
        else:
            prev_y_df["Jumlah"] = prev_y_df[col_map_jumlah[trx_type]]
            prev_y_df["Nilai"] = prev_y_df[col_map_nilai[trx_type]]
        prev_y_group = prev_y_df.groupby("Nama PJP", observed=False)[["Jumlah", "Nilai"]].sum().reset_index()
    else:
        prev_y_group = pd.DataFrame(columns=["Nama PJP", "Jumlah", "Nilai"])

    # Merge for growth
    detail = cur_group.merge(prev_q_group, on="Nama PJP", how="left", suffixes=("", "_PrevQ"))
    detail = detail.merge(prev_y_group, on="Nama PJP", how="left", suffixes=("", "_PrevY"))

    # Ensure numeric dtypes (sorting must be numeric, not lexicographic)
    for col in ["Jumlah", "Nilai", "Jumlah_PrevQ", "Nilai_PrevQ", "Jumlah_PrevY", "Nilai_PrevY"]:
        if col in detail.columns:
            detail[col] = pd.to_numeric(detail[col], errors="coerce")

    def pct_growth(cur: pd.Series, prev: pd.Series) -> pd.Series:
        """Percent growth in %.

        For dashboard readability, when the comparison value is missing or 0,
        we return 0.0 (instead of None/NaN) so the table stays sortable and
        doesn't show 'None'.
        """
        cur = pd.to_numeric(cur, errors="coerce")
        prev = pd.to_numeric(prev, errors="coerce")
        out = (cur - prev) / prev * 100

        # Keep dtype numeric and avoid 'None' in Streamlit
        out = out.fillna(0.0)
        out = out.where(prev != 0, 0.0)

        # Stabilize rounding for Streamlit NumberColumn display
        out = out.map(lambda x: qround_float(x, decimals=2, none=0.0))
        return out

    detail["Growth QtQ (%)"] = pct_growth(detail["Nilai"], detail.get("Nilai_PrevQ"))
    detail["Growth YoY (%)"] = pct_growth(detail["Nilai"], detail.get("Nilai_PrevY"))

    # Delta (absolute change) - focus on nominal
    if "Nilai_PrevQ" in detail.columns:
        detail["Delta QtQ Nilai"] = (detail["Nilai"].fillna(0) - detail["Nilai_PrevQ"].fillna(0))
    else:
        detail["Delta QtQ Nilai"] = 0.0
    if "Nilai_PrevY" in detail.columns:
        detail["Delta YoY Nilai"] = (detail["Nilai"].fillna(0) - detail["Nilai_PrevY"].fillna(0))
    else:
        detail["Delta YoY Nilai"] = 0.0

    # Display columns (hide helper prev columns)
    display_cols = [
        "Nama PJP",
        "Jumlah",
        "Nilai",
        "Delta QtQ Nilai",
        "Growth QtQ (%)",
        "Delta YoY Nilai",
        "Growth YoY (%)",
    ]
    display_cols = [c for c in display_cols if c in detail.columns]

    # Insight: total delta + biggest positive/negative contributors (Nominal)
    def _fmt_tril(amount_rp: float) -> str:
        try:
            t = float(amount_rp) / 1e12
        except Exception:
            t = 0.0
        return format_id_decimal(t, decimals=1, none="0")

    def _fmt_pct(p: float) -> str:
        try:
            fp = float(p)
        except Exception:
            fp = 0.0
        return format_id_percent(fp, decimals=2, show_sign=True, none="0,00%", space_before_percent=False)

    def _top_pos_neg(delta_col: str, pct_col: str) -> tuple[tuple[str, float, float] | None, tuple[str, float, float] | None]:
        if delta_col not in detail.columns or pct_col not in detail.columns or "Nama PJP" not in detail.columns:
            return None, None
        dfc = detail[["Nama PJP", delta_col, pct_col]].copy()
        dfc[delta_col] = pd.to_numeric(dfc[delta_col], errors="coerce").fillna(0.0)
        dfc[pct_col] = pd.to_numeric(dfc[pct_col], errors="coerce").fillna(0.0)

        pos = dfc[dfc[delta_col] > 0]
        neg = dfc[dfc[delta_col] < 0]

        top_pos = None
        top_neg = None
        if not pos.empty:
            r = pos.sort_values(delta_col, ascending=False).iloc[0]
            top_pos = (str(r["Nama PJP"]), float(r[delta_col]), float(r[pct_col]))
        if not neg.empty:
            r = neg.sort_values(delta_col, ascending=True).iloc[0]
            top_neg = (str(r["Nama PJP"]), float(r[delta_col]), float(r[pct_col]))
        return top_pos, top_neg

    def _total_delta_and_growth(cur_col: str, prev_col: str) -> tuple[float, float, float]:
        cur_total = float(pd.to_numeric(detail.get(cur_col), errors="coerce").fillna(0).sum())
        prev_total = float(pd.to_numeric(detail.get(prev_col), errors="coerce").fillna(0).sum())
        delta_total = cur_total - prev_total
        growth_total = float(pct_growth(pd.Series([cur_total]), pd.Series([prev_total])).iloc[0])
        return cur_total, prev_total, delta_total, growth_total

    cur_total, prevq_total, delta_q_total, pct_q_total = _total_delta_and_growth("Nilai", "Nilai_PrevQ")
    _, prevy_total, delta_y_total, pct_y_total = _total_delta_and_growth("Nilai", "Nilai_PrevY")

    qtq_pos, qtq_neg = _top_pos_neg("Delta QtQ Nilai", "Growth QtQ (%)")
    yoy_pos, yoy_neg = _top_pos_neg("Delta YoY Nilai", "Growth YoY (%)")

    qtq_label = f"Q{prev_q} {prev_y}"
    yoy_label = f"Q{quarter} {year - 1}"

    insight_lines: list[str] = []
    trend_q = "meningkat" if delta_q_total >= 0 else "menurun"
    trend_y = "meningkat" if delta_y_total >= 0 else "menurun"

    insight_lines.append(
        f"- Total nominal periode ini **{trend_q}** dibanding {qtq_label}: **Rp {_fmt_tril(abs(delta_q_total))} triliun** ({_fmt_pct(pct_q_total)} QtQ)."
    )
    if delta_q_total < 0 and qtq_neg is not None:
        name, delta_rp, pct = qtq_neg
        insight_lines.append(
            f"  Penurunan terutama disebabkan oleh **{name}** sebesar **Rp {_fmt_tril(abs(delta_rp))} triliun** ({_fmt_pct(pct)} QtQ)."
        )
        if qtq_pos is not None:
            name2, delta2, pct2 = qtq_pos
            insight_lines.append(
                f"  Diimbangi kenaikan dari **{name2}** sebesar **Rp {_fmt_tril(abs(delta2))} triliun** ({_fmt_pct(pct2)} QtQ)."
            )
    elif delta_q_total >= 0 and qtq_pos is not None:
        name, delta_rp, pct = qtq_pos
        insight_lines.append(
            f"  Kenaikan terutama didorong oleh **{name}** sebesar **Rp {_fmt_tril(abs(delta_rp))} triliun** ({_fmt_pct(pct)} QtQ)."
        )
        if qtq_neg is not None:
            name2, delta2, pct2 = qtq_neg
            insight_lines.append(
                f"  Namun tertahan oleh penurunan **{name2}** sebesar **Rp {_fmt_tril(abs(delta2))} triliun** ({_fmt_pct(pct2)} QtQ)."
            )

    insight_lines.append(
        f"- Total nominal periode ini **{trend_y}** dibanding {yoy_label}: **Rp {_fmt_tril(abs(delta_y_total))} triliun** ({_fmt_pct(pct_y_total)} YoY)."
    )
    if delta_y_total < 0 and yoy_neg is not None:
        name, delta_rp, pct = yoy_neg
        insight_lines.append(
            f"  Penurunan terutama disebabkan oleh **{name}** sebesar **Rp {_fmt_tril(abs(delta_rp))} triliun** ({_fmt_pct(pct)} YoY)."
        )
        if yoy_pos is not None:
            name2, delta2, pct2 = yoy_pos
            insight_lines.append(
                f"  Diimbangi kenaikan dari **{name2}** sebesar **Rp {_fmt_tril(abs(delta2))} triliun** ({_fmt_pct(pct2)} YoY)."
            )
    elif delta_y_total >= 0 and yoy_pos is not None:
        name, delta_rp, pct = yoy_pos
        insight_lines.append(
            f"  Kenaikan terutama didorong oleh **{name}** sebesar **Rp {_fmt_tril(abs(delta_rp))} triliun** ({_fmt_pct(pct)} YoY)."
        )
        if yoy_neg is not None:
            name2, delta2, pct2 = yoy_neg
            insight_lines.append(
                f"  Namun tertahan oleh penurunan **{name2}** sebesar **Rp {_fmt_tril(abs(delta2))} triliun** ({_fmt_pct(pct2)} YoY)."
            )

    if insight_lines:
        st.markdown("\n".join(insight_lines))

    st.dataframe(
        detail[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Nama PJP": st.column_config.TextColumn("Nama PJP"),
            "Jumlah": st.column_config.NumberColumn("Jumlah", format="%.0f"),
            "Nilai": st.column_config.NumberColumn("Nilai", format="%.0f"),
            "Delta QtQ Nilai": st.column_config.NumberColumn("Delta QtQ Nilai", format="%+.0f"),
            "Growth QtQ (%)": st.column_config.NumberColumn("Growth QtQ (%)", format="%+.2f%%"),
            "Delta YoY Nilai": st.column_config.NumberColumn("Delta YoY Nilai", format="%+.0f"),
            "Growth YoY (%)": st.column_config.NumberColumn("Growth YoY (%)", format="%+.2f%%"),
        },
    )


def _render_pjp_detail_month(df_base: pd.DataFrame, year: int, month: str, trx_type: str):
    """Tampilkan detail growth per PJP untuk periode (year, month) dengan MtM & YoY pada level bulan."""
    import calendar

    col_map_jumlah = {
        "Incoming": "Sum of Fin Jumlah Inc",
        "Outgoing": "Sum of Fin Jumlah Out",
        "Domestik": "Sum of Fin Jumlah Dom",
    }
    col_map_nilai = {
        "Incoming": "Sum of Fin Nilai Inc",
        "Outgoing": "Sum of Fin Nilai Out",
        "Domestik": "Sum of Fin Nilai Dom",
    }

    month_num = list(calendar.month_name).index(str(month)) if str(month) in calendar.month_name else int(month)

    current = df_base[(df_base["Year"] == year) & (df_base["Month"].astype(str) == str(month))].copy()
    if current.empty:
        st.warning("Data tidak ditemukan untuk periode tersebut")
        return

    if trx_type == "Total":
        current["Jumlah"] = (
            current["Sum of Fin Jumlah Inc"]
            + current["Sum of Fin Jumlah Out"]
            + current["Sum of Fin Jumlah Dom"]
        )
        current["Nilai"] = (
            current["Sum of Fin Nilai Inc"]
            + current["Sum of Fin Nilai Out"]
            + current["Sum of Fin Nilai Dom"]
        )
    else:
        current["Jumlah"] = current[col_map_jumlah[trx_type]]
        current["Nilai"] = current[col_map_nilai[trx_type]]

    cur_group = current.groupby("Nama PJP", observed=False)[["Jumlah", "Nilai"]].sum().reset_index()

    # Prev month
    prev_m = 12 if month_num == 1 else month_num - 1
    prev_y = year if month_num > 1 else year - 1
    prev_m_name = calendar.month_name[prev_m]
    prev_m_df = df_base[(df_base["Year"] == prev_y) & (df_base["Month"].astype(str) == str(prev_m_name))].copy()
    if prev_m_df.empty:
        prev_m_df = df_base[(df_base["Year"] == prev_y) & (df_base["Month"].astype(str) == str(prev_m))].copy()
    if not prev_m_df.empty:
        if trx_type == "Total":
            prev_m_df["Jumlah"] = prev_m_df["Sum of Fin Jumlah Inc"] + prev_m_df["Sum of Fin Jumlah Out"] + prev_m_df["Sum of Fin Jumlah Dom"]
            prev_m_df["Nilai"] = prev_m_df["Sum of Fin Nilai Inc"] + prev_m_df["Sum of Fin Nilai Out"] + prev_m_df["Sum of Fin Nilai Dom"]
        else:
            prev_m_df["Jumlah"] = prev_m_df[col_map_jumlah[trx_type]]
            prev_m_df["Nilai"] = prev_m_df[col_map_nilai[trx_type]]
        prev_m_group = prev_m_df.groupby("Nama PJP", observed=False)[["Jumlah", "Nilai"]].sum().reset_index()
    else:
        prev_m_group = pd.DataFrame(columns=["Nama PJP", "Jumlah", "Nilai"])

    # Prev year same month
    prev_y_df = df_base[(df_base["Year"] == year - 1) & (df_base["Month"].astype(str) == str(month))].copy()
    if prev_y_df.empty:
        prev_y_df = df_base[(df_base["Year"] == year - 1) & (df_base["Month"].astype(str) == str(month_num))].copy()
    if not prev_y_df.empty:
        if trx_type == "Total":
            prev_y_df["Jumlah"] = prev_y_df["Sum of Fin Jumlah Inc"] + prev_y_df["Sum of Fin Jumlah Out"] + prev_y_df["Sum of Fin Jumlah Dom"]
            prev_y_df["Nilai"] = prev_y_df["Sum of Fin Nilai Inc"] + prev_y_df["Sum of Fin Nilai Out"] + prev_y_df["Sum of Fin Nilai Dom"]
        else:
            prev_y_df["Jumlah"] = prev_y_df[col_map_jumlah[trx_type]]
            prev_y_df["Nilai"] = prev_y_df[col_map_nilai[trx_type]]
        prev_y_group = prev_y_df.groupby("Nama PJP", observed=False)[["Jumlah", "Nilai"]].sum().reset_index()
    else:
        prev_y_group = pd.DataFrame(columns=["Nama PJP", "Jumlah", "Nilai"])

    detail = cur_group.merge(prev_m_group, on="Nama PJP", how="left", suffixes=("", "_PrevM"))
    detail = detail.merge(prev_y_group, on="Nama PJP", how="left", suffixes=("", "_PrevY"))

    for col in ["Jumlah", "Nilai", "Jumlah_PrevM", "Nilai_PrevM", "Jumlah_PrevY", "Nilai_PrevY"]:
        if col in detail.columns:
            detail[col] = pd.to_numeric(detail[col], errors="coerce")

    def pct_growth(cur: pd.Series, prev: pd.Series) -> pd.Series:
        cur = pd.to_numeric(cur, errors="coerce")
        prev = pd.to_numeric(prev, errors="coerce")
        out = (cur - prev) / prev * 100
        out = out.fillna(0.0)
        out = out.where(prev != 0, 0.0)

        # Stabilize rounding for Streamlit NumberColumn display
        out = out.map(lambda x: qround_float(x, decimals=2, none=0.0))
        return out

    detail["Growth MtM (%)"] = pct_growth(detail["Nilai"], detail.get("Nilai_PrevM"))
    detail["Growth YoY (%)"] = pct_growth(detail["Nilai"], detail.get("Nilai_PrevY"))

    display_cols = ["Nama PJP", "Jumlah", "Nilai", "Growth MtM (%)", "Growth YoY (%)"]
    display_cols = [c for c in display_cols if c in detail.columns]

    st.dataframe(
        detail[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Nama PJP": st.column_config.TextColumn("Nama PJP"),
            "Jumlah": st.column_config.NumberColumn("Jumlah", format="%.0f"),
            "Nilai": st.column_config.NumberColumn("Nilai", format="%.0f"),
            "Growth MtM (%)": st.column_config.NumberColumn("Growth MtM (%)", format="%+.2f%%"),
            "Growth YoY (%)": st.column_config.NumberColumn("Growth YoY (%)", format="%+.2f%%"),
        },
    )


def _render_overall_growth_detail_table_quarterly(
    *,
    df_total_combined: pd.DataFrame,
    df_inc: pd.DataFrame,
    df_out: pd.DataFrame,
    df_dom: pd.DataFrame,
    sum_trx_type: str,
    visible_periods: list[str] | None,
    ordered_periods: list[str],
):
    """Tabel detail YoY/QtQ untuk semua periode yang sedang ditampilkan (visual-only)."""

    if sum_trx_type not in ("Jumlah", "Nilai"):
        return

    if df_total_combined is None or df_total_combined.empty:
        return

    # Tentukan periode yang benar-benar ditampilkan (urut sesuai pilihan)
    visible_set = set(visible_periods or [])
    shown_periods = [p for p in ordered_periods if p in visible_set] if visible_set else list(ordered_periods)
    if not shown_periods:
        st.info("Tidak ada periode yang dipilih untuk tabel detail.")
        return

    # Parse "YYYY Qn" menjadi list (Year, Quarter) berurutan
    parsed = []
    for p in shown_periods:
        try:
            parts = str(p).split()
            if len(parts) >= 2 and parts[1].upper().startswith("Q"):
                y = int(parts[0])
                q = int(parts[1].upper().replace("Q", ""))
                if 1 <= q <= 4:
                    parsed.append((y, q))
        except Exception:
            continue

    if not parsed:
        return

    if sum_trx_type == "Jumlah":
        value_unit = "Volume (Jutaan)"
        scale = 1e6
    else:
        value_unit = "Nilai (Rp Triliun)"
        scale = 1e12

    periods_df = pd.DataFrame(parsed, columns=["Year", "Quarter"]).drop_duplicates()

    total_val_col = f"Sum of Fin {sum_trx_type} Total"
    total_yoy_col = f"%YoY {sum_trx_type}"
    total_qoq_col = f"%QtQ {sum_trx_type}"

    inc_val_col = f"Sum of Fin {sum_trx_type} Inc"
    out_val_col = f"Sum of Fin {sum_trx_type} Out"
    dom_val_col = f"Sum of Fin {sum_trx_type} Dom"

    def _num(v):
        return pd.to_numeric(v, errors="coerce")

    def _build_block(
        df_src: pd.DataFrame,
        *,
        jenis: str,
        value_col: str,
        yoy_col: str,
        qoq_col: str,
    ) -> pd.DataFrame:
        if df_src is None or df_src.empty:
            return pd.DataFrame()
        if not {"Year", "Quarter"}.issubset(set(df_src.columns)):
            return pd.DataFrame()
        needed = {value_col, yoy_col, qoq_col}
        if not needed.issubset(set(df_src.columns)):
            return pd.DataFrame()

        dfc = df_src[["Year", "Quarter", value_col, yoy_col, qoq_col]].copy()
        dfc["Year"] = dfc["Year"].astype(int)
        dfc["Quarter"] = dfc["Quarter"].astype(int)

        # Join ke daftar periode yg sedang ditampilkan agar urut & hanya yg dipilih
        dfc = periods_df.merge(dfc, on=["Year", "Quarter"], how="left")
        dfc["Periode"] = "Q" + dfc["Quarter"].astype(int).astype(str) + " " + dfc["Year"].astype(int).astype(str)
        dfc["Jenis"] = jenis
        dfc[value_unit] = (_num(dfc[value_col]) / scale).map(lambda x: qround_float(x, decimals=2, none=0.0))
        dfc["YoY (%)"] = _num(dfc[yoy_col]).map(lambda x: qround_float(x, decimals=2, none=0.0))
        dfc["QtQ (%)"] = _num(dfc[qoq_col]).map(lambda x: qround_float(x, decimals=2, none=0.0))
        return dfc[["Periode", "Jenis", value_unit, "YoY (%)", "QtQ (%)"]]

    df_total_block = _build_block(
        df_total_combined,
        jenis="Total",
        value_col=total_val_col,
        yoy_col=total_yoy_col,
        qoq_col=total_qoq_col,
    )
    df_inc_block = _build_block(
        df_inc,
        jenis="Incoming",
        value_col=inc_val_col,
        yoy_col="%YoY",
        qoq_col="%QtQ",
    )
    df_out_block = _build_block(
        df_out,
        jenis="Outgoing",
        value_col=out_val_col,
        yoy_col="%YoY",
        qoq_col="%QtQ",
    )
    df_dom_block = _build_block(
        df_dom,
        jenis="Domestik",
        value_col=dom_val_col,
        yoy_col="%YoY",
        qoq_col="%QtQ",
    )

    # Make Total display consistent with the sum of displayed components
    if not df_total_block.empty and not df_inc_block.empty and not df_out_block.empty and not df_dom_block.empty:
        comp = (
            df_inc_block[["Periode", value_unit]]
            .rename(columns={value_unit: "__inc__"})
            .merge(df_out_block[["Periode", value_unit]].rename(columns={value_unit: "__out__"}), on="Periode", how="left")
            .merge(df_dom_block[["Periode", value_unit]].rename(columns={value_unit: "__dom__"}), on="Periode", how="left")
        )
        comp["__inc__"] = pd.to_numeric(comp["__inc__"], errors="coerce").fillna(0.0)
        comp["__out__"] = pd.to_numeric(comp["__out__"], errors="coerce").fillna(0.0)
        comp["__dom__"] = pd.to_numeric(comp["__dom__"], errors="coerce").fillna(0.0)
        comp[value_unit] = (comp["__inc__"] + comp["__out__"] + comp["__dom__"]).map(lambda x: qround_float(x, decimals=2, none=0.0))
        df_total_block = df_total_block.drop(columns=[value_unit]).merge(comp[["Periode", value_unit]], on="Periode", how="left")

    df_detail = pd.concat([df_total_block, df_inc_block, df_out_block, df_dom_block], ignore_index=True)
    if df_detail.empty:
        return

    st.caption("Detail perbandingan untuk semua periode yang sedang ditampilkan pada chart (sesuai filter 'Tampilkan Kuartal').")
    st.dataframe(
        df_detail,
        use_container_width=True,
        hide_index=True,
        column_config={
            value_unit: st.column_config.NumberColumn(value_unit, format="%.2f"),
            "YoY (%)": st.column_config.NumberColumn("YoY (%)", format="%+.2f%%"),
            "QtQ (%)": st.column_config.NumberColumn("QtQ (%)", format="%+.2f%%"),
        },
    )

# Initial Page Setup
set_page_visuals("viz")

if st.session_state['df'] is not None:
    df = st.session_state['df']
    with st.sidebar:
        with st.expander("Filter Growth", True):
            unique_years = sorted(df['Year'].unique().tolist())
            quarters = ['Q1', 'Q2', 'Q3', 'Q4']
            
            # Start Year & Quarter
            col_y1, col_q1 = st.columns(2)
            with col_y1:
                selected_start_year = st.selectbox('Start Year:', unique_years)
            with col_q1:
                selected_start_quarter = st.selectbox('Start Quarter:', quarters)
            
            # End Year & Quarter
            col_y2, col_q2 = st.columns(2)
            with col_y2:
                selected_end_year = st.selectbox('End Year:', unique_years, index=len(unique_years) - 1)
            with col_q2:
                selected_end_quarter = st.selectbox('End Quarter:', quarters, index=3)

            jenis_transaksi = ['All', 'Incoming', 'Outgoing', 'Domestik']
            selected_jenis_transaksi = st.selectbox('Select Jenis Transaksi:', jenis_transaksi)

        with st.expander("Pengaturan Tampilan Grafik (Growth)", True):
            st.slider(
                "Ukuran Font (Global)",
                min_value=9,
                max_value=22,
                value=int(st.session_state.get("growth_font_size", 12)),
                step=1,
                key="growth_font_size",
                help="Mengatur ukuran seluruh tulisan di grafik (judul, axis, legend, hoverlabel).",
            )
            st.slider(
                "Ukuran Angka Sumbu X",
                min_value=8,
                max_value=24,
                value=int(st.session_state.get("growth_axis_x_tick_font_size", max(int(st.session_state.get("growth_font_size", 12)) - 1, 9))),
                step=1,
                key="growth_axis_x_tick_font_size",
                help="Mengatur ukuran angka pada sumbu X (horizontal/periode).",
            )
            st.checkbox(
                "Bold Angka Sumbu X",
                value=bool(st.session_state.get("growth_axis_x_tick_bold", True)),
                key="growth_axis_x_tick_bold",
                help="Menebalkan angka pada sumbu X.",
            )
            st.selectbox(
                "Ketebalan Angka Sumbu X",
                options=["Normal", "Medium", "SemiBold", "Bold", "Black"],
                index=["Normal", "Medium", "SemiBold", "Bold", "Black"].index(str(st.session_state.get("growth_axis_x_tick_weight", "SemiBold"))),
                key="growth_axis_x_tick_weight",
                help="Mengatur seberapa tebal angka pada sumbu X. Ini override checkbox Bold.",
            )
            st.slider(
                "Ukuran Angka Sumbu Y",
                min_value=8,
                max_value=24,
                value=int(st.session_state.get("growth_axis_y_tick_font_size", max(int(st.session_state.get("growth_font_size", 12)) - 1, 9))),
                step=1,
                key="growth_axis_y_tick_font_size",
                help="Mengatur ukuran angka pada sumbu Y (kiri & kanan/nilai & growth).",
            )
            st.checkbox(
                "Bold Angka Sumbu Y",
                value=bool(st.session_state.get("growth_axis_y_tick_bold", True)),
                key="growth_axis_y_tick_bold",
                help="Menebalkan angka pada sumbu Y (termasuk sumbu kanan jika ada).",
            )
            st.selectbox(
                "Ketebalan Angka Sumbu Y",
                options=["Normal", "Medium", "SemiBold", "Bold", "Black"],
                index=["Normal", "Medium", "SemiBold", "Bold", "Black"].index(str(st.session_state.get("growth_axis_y_tick_weight", "SemiBold"))),
                key="growth_axis_y_tick_weight",
                help="Mengatur seberapa tebal angka pada sumbu Y. Ini override checkbox Bold.",
            )
            st.slider(
                "Ukuran Legend (Legenda Grafik)",
                min_value=9,
                max_value=24,
                value=int(st.session_state.get("growth_legend_font_size", st.session_state.get("growth_font_size", 12))),
                step=1,
                key="growth_legend_font_size",
                help="Mengatur ukuran tulisan pada legend/legenda grafik.",
            )
            st.slider(
                "Ukuran Font Label (%)",
                min_value=9,
                max_value=26,
                value=int(st.session_state.get("growth_label_font_size", 12)),
                step=1,
                key="growth_label_font_size",
                help="Mengatur ukuran tulisan label persentase (YoY/QtQ) di titik terakhir.",
            )
            st.slider(
                "Tinggi Grafik (px)",
                min_value=380,
                max_value=980,
                value=int(st.session_state.get("growth_chart_height", 560)),
                step=20,
                key="growth_chart_height",
                help="Atur tinggi grafik supaya tidak gepeng / terlalu tinggi.",
            )
            st.slider(
                "Lebar Grafik (px)",
                min_value=0,
                max_value=2200,
                value=int(st.session_state.get("growth_chart_width", 0)),
                step=50,
                key="growth_chart_width",
                help="Atur lebar grafik. 0 = mengikuti lebar container (auto).",
            )
        st.info("Use the filters to adjust the year-quarter range and transaction type.")

        _growth_font_size = int(st.session_state.get("growth_font_size", 12))
        _growth_axis_x_tick_font_size = int(st.session_state.get("growth_axis_x_tick_font_size", max(_growth_font_size - 1, 9)))
        _growth_axis_y_tick_font_size = int(st.session_state.get("growth_axis_y_tick_font_size", max(_growth_font_size - 1, 9)))
        _growth_axis_x_tick_bold = bool(st.session_state.get("growth_axis_x_tick_bold", True))
        _growth_axis_y_tick_bold = bool(st.session_state.get("growth_axis_y_tick_bold", True))
        _growth_axis_x_tick_weight = str(st.session_state.get("growth_axis_x_tick_weight", "SemiBold"))
        _growth_axis_y_tick_weight = str(st.session_state.get("growth_axis_y_tick_weight", "SemiBold"))
        _growth_legend_font_size = int(st.session_state.get("growth_legend_font_size", _growth_font_size))
        _growth_label_font_size = int(st.session_state.get("growth_label_font_size", 12))
        _growth_chart_height = int(st.session_state.get("growth_chart_height", 560))
        _growth_chart_width = int(st.session_state.get("growth_chart_width", 0))

    with (st.spinner('Loading and filtering data...')):
        df_preprocessed_time = preprocess_data(df, True)

        df_sum_time = sum_data_time(df_preprocessed_time, False)
        df_sum_time_month = sum_data_time(df_preprocessed_time, True)

        df_tuple = preprocess_data_growth(df_sum_time, False)
        df_tuple_month = preprocess_data_growth(df_sum_time_month, True)

        df_jumlah_inc, df_jumlah_out, df_jumlah_dom, df_nom_inc, df_nom_out, df_nom_dom = df_tuple

        (df_jumlah_inc_month, df_jumlah_out_month, df_jumlah_dom_month,
         df_nom_inc_month, df_nom_out_month, df_nom_dom_month) = df_tuple_month

        df_jumlah_total = process_combined_df(df_jumlah_inc, df_jumlah_out,
                                              df_jumlah_dom, False)
        df_nom_total = process_combined_df(df_nom_inc, df_nom_out,
                                           df_nom_dom, False)

        df_jumlah_total_month = process_combined_df(df_jumlah_inc_month, df_jumlah_out_month,
                                                    df_jumlah_dom_month, True)
        df_nom_total_month = process_combined_df(df_nom_inc_month, df_nom_out_month,
                                                 df_nom_dom_month, True)

        df_total_combined = process_growth_combined(df_jumlah_total, df_nom_total, df_preprocessed_time['Year'].min(),
                                                    False)
        df_total_month_combined = process_growth_combined(df_jumlah_total_month, df_nom_total_month,
                                                          df_preprocessed_time['Year'].min(), True)

        # Filter by year and quarter range (continuous)
        df_total_combined = filter_start_end_year(df_total_combined, selected_start_year, selected_end_year)
        df_total_combined = filter_by_quarter(df_total_combined, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_total_month_combined = filter_start_end_year(df_total_month_combined, selected_start_year, selected_end_year, True)
        df_total_month_combined = filter_by_quarter(df_total_month_combined, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)

        df_jumlah_inc_filtered = filter_start_end_year(df_jumlah_inc, selected_start_year, selected_end_year)
        df_jumlah_inc_filtered = filter_by_quarter(df_jumlah_inc_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_jumlah_out_filtered = filter_start_end_year(df_jumlah_out, selected_start_year, selected_end_year)
        df_jumlah_out_filtered = filter_by_quarter(df_jumlah_out_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_jumlah_dom_filtered = filter_start_end_year(df_jumlah_dom, selected_start_year, selected_end_year)
        df_jumlah_dom_filtered = filter_by_quarter(df_jumlah_dom_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)

        df_nom_inc_filtered = filter_start_end_year(df_nom_inc, selected_start_year, selected_end_year)
        df_nom_inc_filtered = filter_by_quarter(df_nom_inc_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_nom_out_filtered = filter_start_end_year(df_nom_out, selected_start_year, selected_end_year)
        df_nom_out_filtered = filter_by_quarter(df_nom_out_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_nom_dom_filtered = filter_start_end_year(df_nom_dom, selected_start_year, selected_end_year)
        df_nom_dom_filtered = filter_by_quarter(df_nom_dom_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)

        df_jumlah_inc_month_filtered = filter_start_end_year(df_jumlah_inc_month, selected_start_year, selected_end_year, True)
        df_jumlah_inc_month_filtered = filter_by_quarter(df_jumlah_inc_month_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_jumlah_out_month_filtered = filter_start_end_year(df_jumlah_out_month, selected_start_year, selected_end_year, True)
        df_jumlah_out_month_filtered = filter_by_quarter(df_jumlah_out_month_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_jumlah_dom_month_filtered = filter_start_end_year(df_jumlah_dom_month, selected_start_year, selected_end_year, True)
        df_jumlah_dom_month_filtered = filter_by_quarter(df_jumlah_dom_month_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)

        df_nom_inc_month_filtered = filter_start_end_year(df_nom_inc_month, selected_start_year, selected_end_year, True)
        df_nom_inc_month_filtered = filter_by_quarter(df_nom_inc_month_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_nom_out_month_filtered = filter_start_end_year(df_nom_out_month, selected_start_year, selected_end_year, True)
        df_nom_out_month_filtered = filter_by_quarter(df_nom_out_month_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)
        
        df_nom_dom_month_filtered = filter_start_end_year(df_nom_dom_month, selected_start_year, selected_end_year, True)
        df_nom_dom_month_filtered = filter_by_quarter(df_nom_dom_month_filtered, selected_start_year, selected_start_quarter, selected_end_year, selected_end_quarter)

        df_inc_combined = merge_df_growth(df_jumlah_inc_filtered, df_nom_inc_filtered)
        df_out_combined = merge_df_growth(df_jumlah_out_filtered, df_nom_out_filtered)
        df_dom_combined = merge_df_growth(df_jumlah_dom_filtered, df_nom_dom_filtered)

        df_inc_combined_month = merge_df_growth(df_jumlah_inc_month_filtered, df_nom_inc_month_filtered, True)
        df_out_combined_month = merge_df_growth(df_jumlah_out_month_filtered, df_nom_out_month_filtered, True)
        df_dom_combined_month = merge_df_growth(df_jumlah_dom_month_filtered, df_nom_dom_month_filtered, True)

        st.subheader("📈 Growth in Transactions")
        
        # Initialize default view mode
        if 'view_mode' not in st.session_state:
            st.session_state['view_mode'] = 'quarterly'
        
        # Toggle buttons dengan styling modern
        col_space1, col_toggle1, col_toggle2, col_space2 = st.columns([2, 1.5, 1.5, 2])
        
        # CSS styling untuk toggle buttons
        toggle_css = """
        <style>
            .toggle-container {
                display: flex;
                gap: 10px;
                justify-content: center;
                margin-bottom: 20px;
            }
            
            .toggle-btn {
                padding: 10px 20px;
                border-radius: 8px;
                border: 2px solid #e0e0e0;
                background-color: #f8f9fa;
                color: #333;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 15px;
                min-width: 140px;
            }
            
            .toggle-btn:hover {
                border-color: #3b82f6;
                background-color: #eff6ff;
                color: #1e40af;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(59, 130, 246, 0.15);
            }
            
            .toggle-btn.active {
                background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
                color: white;
                border-color: #1e40af;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            }
            
            .toggle-btn.active:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
            }
        </style>
        """
        st.markdown(toggle_css, unsafe_allow_html=True)
        
        # Render modern toggle slider
        col_space1, col_toggle, col_space2 = st.columns([1.5, 3, 1.5])
        
        with col_toggle:
            # Custom CSS untuk segmented control
            segmented_css = """
            <style>
                .segmented-control {
                    display: flex;
                    background: linear-gradient(to bottom, #f5f5f5, #efefef);
                    border-radius: 50px;
                    padding: 3px;
                    width: fit-content;
                    margin: 20px auto;
                    box-shadow: 
                        inset 0 2px 4px rgba(255,255,255,0.5),
                        inset 0 -2px 4px rgba(0,0,0,0.05),
                        0 4px 12px rgba(0,0,0,0.08);
                    gap: 4px;
                }
                
                .segmented-control button {
                    flex: 1;
                    padding: 12px 24px;
                    border: none;
                    background: transparent;
                    color: #666;
                    font-weight: 500;
                    font-size: 15px;
                    cursor: pointer;
                    border-radius: 48px;
                    transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
                    min-width: 130px;
                    white-space: nowrap;
                }
                
                .segmented-control button:hover {
                    background: rgba(59, 130, 246, 0.08);
                    color: #3b82f6;
                }
                
                .segmented-control button.active {
                    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                    color: white;
                    font-weight: 600;
                    box-shadow: 
                        0 4px 12px rgba(59, 130, 246, 0.35),
                        inset 0 1px 2px rgba(255,255,255,0.2);
                }
            </style>
            """
            st.markdown(segmented_css, unsafe_allow_html=True)
        
        # Create button group
        col_q, col_m, col_y = st.columns([1, 1, 1], gap="small")
        
        with col_q:
            is_quarterly = st.session_state['view_mode'] == 'quarterly'
            btn_style = "primary" if is_quarterly else "secondary"
            if st.button("📊 Quarterly", key="toggle_quarterly", use_container_width=True, 
                        type=btn_style):
                st.session_state['view_mode'] = 'quarterly'
                st.rerun()
        
        with col_m:
            is_monthly = st.session_state['view_mode'] == 'monthly'
            btn_style = "primary" if is_monthly else "secondary"
            if st.button("📅 Monthly", key="toggle_monthly", use_container_width=True,
                        type=btn_style):
                st.session_state['view_mode'] = 'monthly'
                st.rerun()

        with col_y:
            is_yearly = st.session_state['view_mode'] == 'yearly'
            btn_style = "primary" if is_yearly else "secondary"
            if st.button("🗓️ Yearly", key="toggle_yearly", use_container_width=True,
                        type=btn_style):
                st.session_state['view_mode'] = 'yearly'
                st.rerun()
        
        st.divider()
        
        # QUARTERLY SECTION
        if st.session_state['view_mode'] == 'quarterly':
            st.subheader("📊 Data Transaksi Kuartalan")
            
            # KPI Cards - Tampilkan total dari semua data
            st.markdown("<h3 style='margin-top: 20px; margin-bottom: 15px;'>📈 Ringkasan Transaksi</h3>", unsafe_allow_html=True)
            
            # Calculate totals
            total_inc_freq = df_inc_combined['Sum of Fin Jumlah Inc'].sum()
            total_inc_value = df_inc_combined['Sum of Fin Nilai Inc'].sum()
            total_out_freq = df_out_combined['Sum of Fin Jumlah Out'].sum()
            total_out_value = df_out_combined['Sum of Fin Nilai Out'].sum()
            total_dom_freq = df_dom_combined['Sum of Fin Jumlah Dom'].sum()
            total_dom_value = df_dom_combined['Sum of Fin Nilai Dom'].sum()
            total_all_freq = total_inc_freq + total_out_freq + total_dom_freq
            total_all_value = total_inc_value + total_out_value + total_dom_value

            inc_t = qround_float(total_inc_value / 1e12, decimals=2, none=0.0) or 0.0
            out_t = qround_float(total_out_value / 1e12, decimals=2, none=0.0) or 0.0
            dom_t = qround_float(total_dom_value / 1e12, decimals=2, none=0.0) or 0.0
            tot_t = qround_float(inc_t + out_t + dom_t, decimals=2, none=0.0) or 0.0
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #F5B0CB;">
                    <div class="kpi-title">📥 INCOMING</div>
                    <div class="kpi-value-main" style="color: #F5B0CB;">{total_inc_freq:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #F5B0CB; margin-top: 12px;">Rp {format_en_decimal(inc_t, decimals=2, none='0.00')} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #F5CBA7;">
                    <div class="kpi-title">📤 OUTGOING</div>
                    <div class="kpi-value-main" style="color: #F5CBA7;">{total_out_freq:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #F5CBA7; margin-top: 12px;">Rp {format_en_decimal(out_t, decimals=2, none='0.00')} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #5DADE2;">
                    <div class="kpi-title">🏠 DOMESTIK</div>
                    <div class="kpi-value-main" style="color: #5DADE2;">{total_dom_freq:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #5DADE2; margin-top: 12px;">Rp {format_en_decimal(dom_t, decimals=2, none='0.00')} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #6366f1;">
                    <div class="kpi-title">💰 TOTAL</div>
                    <div class="kpi-value-main" style="color: #6366f1;">{total_all_freq:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #6366f1; margin-top: 12px;">Rp {format_en_decimal(tot_t, decimals=2, none='0.00')} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
            
            # Grafik Gabungan (Stacked Bar + Line)
            st.markdown("<h3 style='margin-bottom: 15px;'>📊 Grafik Gabungan - Nilai Transaksi</h3>", unsafe_allow_html=True)
            make_stacked_bar_line_chart_combined(
                df_inc_combined,
                df_out_combined,
                df_dom_combined,
                is_month=False,
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                axis_x_tick_bold=_growth_axis_x_tick_bold,
                axis_y_tick_bold=_growth_axis_y_tick_bold,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )

            # Perbandingan Periode (Quarter) - VS
            st.markdown("<h3 style='margin-top: 25px; margin-bottom: 10px;'>🆚 Perbandingan Periode (Kuartal)</h3>", unsafe_allow_html=True)
            st.markdown(
                "<p style='color:#6b7280; margin-top:-6px; margin-bottom:12px;'>Pilih 2 periode (tahun & kuartal) untuk dibandingkan. Grafik hanya menampilkan 2 batang yang relevan.</p>",
                unsafe_allow_html=True,
            )

            # Sinkronkan default Periode A/B dengan filter sidebar (Start/End)
            _start_q_int = int(str(selected_start_quarter).replace("Q", ""))
            _end_q_int = int(str(selected_end_quarter).replace("Q", ""))
            _vs_filter_sig = (int(selected_start_year), _start_q_int, int(selected_end_year), _end_q_int)
            if st.session_state.get("_vs_filter_sig") != _vs_filter_sig:
                st.session_state["_vs_filter_sig"] = _vs_filter_sig
                st.session_state["vs_year_a"] = int(selected_start_year)
                st.session_state["vs_q_a"] = int(_start_q_int)
                st.session_state["vs_year_b"] = int(selected_end_year)
                st.session_state["vs_q_b"] = int(_end_q_int)

            cmp_years = sorted(df_total_combined['Year'].unique().tolist()) if not df_total_combined.empty else sorted(df_preprocessed_time['Year'].unique().tolist())
            cmp_quarters = [1, 2, 3, 4]

            c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 1.2])
            with c1:
                vs_year_a = st.selectbox("Tahun A", cmp_years, key="vs_year_a")
            with c2:
                vs_q_a = st.selectbox("Kuartal A", cmp_quarters, format_func=lambda q: f"Q{q}", key="vs_q_a")
            with c3:
                vs_year_b = st.selectbox("Tahun B", cmp_years, key="vs_year_b")
            with c4:
                vs_q_b = st.selectbox("Kuartal B", cmp_quarters, format_func=lambda q: f"Q{q}", key="vs_q_b")

            c5, c6 = st.columns([1.2, 1.6])
            with c5:
                vs_metric = st.selectbox("Metrik", ["Nominal", "Frekuensi"], key="vs_metric")
            with c6:
                vs_trx = st.selectbox("Jenis Transaksi", ["Incoming", "Outgoing", "Domestik", "Total"], key="vs_trx")

            sum_trx_type = "Nilai" if vs_metric == "Nominal" else "Jumlah"

            if vs_trx == "Incoming":
                df_vs_src = df_nom_inc_filtered if sum_trx_type == "Nilai" else df_jumlah_inc_filtered
                trx_code = "Inc"
                is_combined = False
            elif vs_trx == "Outgoing":
                df_vs_src = df_nom_out_filtered if sum_trx_type == "Nilai" else df_jumlah_out_filtered
                trx_code = "Out"
                is_combined = False
            elif vs_trx == "Domestik":
                df_vs_src = df_nom_dom_filtered if sum_trx_type == "Nilai" else df_jumlah_dom_filtered
                trx_code = "Dom"
                is_combined = False
            else:
                df_vs_src = df_total_combined
                trx_code = "Total"
                is_combined = True

            if trx_code == "Total":
                df_vs_inc = df_nom_inc_filtered if sum_trx_type == "Nilai" else df_jumlah_inc_filtered
                df_vs_out = df_nom_out_filtered if sum_trx_type == "Nilai" else df_jumlah_out_filtered
                df_vs_dom = df_nom_dom_filtered if sum_trx_type == "Nilai" else df_jumlah_dom_filtered

                make_quarter_vs_quarter_chart_total_breakdown(
                    df_inc=df_vs_inc,
                    df_out=df_vs_out,
                    df_dom=df_vs_dom,
                    year_a=int(vs_year_a),
                    quarter_a=int(vs_q_a),
                    year_b=int(vs_year_b),
                    quarter_b=int(vs_q_b),
                    sum_trx_type=sum_trx_type,
                    font_size=_growth_font_size,
                    label_font_size=_growth_label_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    axis_x_tick_bold=_growth_axis_x_tick_bold,
                    axis_y_tick_bold=_growth_axis_y_tick_bold,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
            else:
                make_quarter_vs_quarter_chart(
                    df=df_vs_src,
                    year_a=int(vs_year_a),
                    quarter_a=int(vs_q_a),
                    year_b=int(vs_year_b),
                    quarter_b=int(vs_q_b),
                    sum_trx_type=sum_trx_type,
                    trx_type=trx_code,
                    is_combined=is_combined,
                    font_size=_growth_font_size,
                    label_font_size=_growth_label_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    axis_x_tick_bold=_growth_axis_x_tick_bold,
                    axis_y_tick_bold=_growth_axis_y_tick_bold,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )

            # Tabel VS Market Share (Jakarta vs Nasional)
            df_national_raw = st.session_state.get('df_national')
            if df_national_raw is None:
                st.info("Upload data nasional (Raw_JKTNasional) di Summary dulu untuk menampilkan tabel market share vs nasional.")
            else:
                try:
                    df_national_q = add_quarter_column(df_national_raw.copy())
                    df_national_grouped = preprocess_data_national(df_national_q, True, True)

                    jkt_a = df_sum_time[(df_sum_time['Year'] == int(vs_year_a)) & (df_sum_time['Quarter'] == int(vs_q_a))].copy()
                    nat_a = df_national_grouped[(df_national_grouped['Year'] == int(vs_year_a)) & (df_national_grouped['Quarter'] == int(vs_q_a))].copy()

                    jkt_b = df_sum_time[(df_sum_time['Year'] == int(vs_year_b)) & (df_sum_time['Quarter'] == int(vs_q_b))].copy()
                    nat_b = df_national_grouped[(df_national_grouped['Year'] == int(vs_year_b)) & (df_national_grouped['Quarter'] == int(vs_q_b))].copy()

                    if jkt_a.empty or nat_a.empty or jkt_b.empty or nat_b.empty:
                        st.warning("Data market share tidak lengkap untuk salah satu periode (A/B).")
                    else:
                        def _build_ms_row(df_ms: pd.DataFrame, label: str) -> dict:
                            # df_ms: output compile_data_market_share
                            return {
                                "Periode": label,
                                "Jakarta Nom (T)": df_ms["Nominal (dalam triliun)"].iloc[0],
                                "Nasional Nom (T)": df_ms["Nominal (dalam triliun)"].iloc[1],
                                "Market Share Nom (%)": df_ms["Nominal (dalam triliun)"].iloc[2],
                                "Jakarta Frek (Juta)": df_ms["Frekuensi (dalam jutaan)"].iloc[0],
                                "Nasional Frek (Juta)": df_ms["Frekuensi (dalam jutaan)"].iloc[1],
                                "Market Share Frek (%)": df_ms["Frekuensi (dalam jutaan)"].iloc[2],
                            }

                        if trx_code == "Total":
                            ms_a_inc = compile_data_market_share(jkt_a, nat_a, "Inc")
                            ms_a_out = compile_data_market_share(jkt_a, nat_a, "Out")
                            ms_a_dom = compile_data_market_share(jkt_a, nat_a, "Dom")
                            ms_a = compile_data_market_share(jkt_a, nat_a, "Total", ms_a_inc, ms_a_out, ms_a_dom)

                            ms_b_inc = compile_data_market_share(jkt_b, nat_b, "Inc")
                            ms_b_out = compile_data_market_share(jkt_b, nat_b, "Out")
                            ms_b_dom = compile_data_market_share(jkt_b, nat_b, "Dom")
                            ms_b = compile_data_market_share(jkt_b, nat_b, "Total", ms_b_inc, ms_b_out, ms_b_dom)
                        else:
                            ms_a = compile_data_market_share(jkt_a, nat_a, trx_code)
                            ms_b = compile_data_market_share(jkt_b, nat_b, trx_code)

                        st.markdown("<h4 style='margin-top: 10px; margin-bottom: 10px;'>📋 Tabel VS - Market Share Jakarta vs Nasional</h4>", unsafe_allow_html=True)
                        df_ms_vs = pd.DataFrame([
                            _build_ms_row(ms_a, f"Q{int(vs_q_a)} {int(vs_year_a)}"),
                            _build_ms_row(ms_b, f"Q{int(vs_q_b)} {int(vs_year_b)}"),
                        ])
                        st.dataframe(df_ms_vs, use_container_width=True, hide_index=True)
                        st.caption("Market Share = (Jakarta / Nasional) × 100. Nominal dalam triliun, Frekuensi dalam jutaan.")
                except Exception as e:
                    st.warning(f"Gagal memproses market share vs nasional: {e}")
            
            st.divider()
            
            if selected_jenis_transaksi == 'Incoming' or selected_jenis_transaksi == 'All':
                st.markdown("<h3 style='background-color: #f0f7ff; border-left: 5px solid #3b82f6; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px;'>📥 INCOMING - Data Transaksi</h3>", unsafe_allow_html=True)
                
                # Display table with proper numeric sorting
                df_inc_combined_display = rename_format_growth_df(df_inc_combined.copy(), "Inc")
                st.dataframe(
                    df_inc_combined_display, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config=_get_growth_column_config("Incoming")
                )
                
                # Detail selection with dropdown
                col_detail, col_empty = st.columns([3, 5])
                with col_detail:
                    period_options = [f"Q{int(row['Quarter'])} {int(row['Year'])}" for _, row in df_inc_combined.iterrows()]
                    selected_period = st.selectbox("Pilih periode untuk detail", period_options, key="sel_inc_period", label_visibility="collapsed")
                    if selected_period:
                        for idx, row in df_inc_combined.iterrows():
                            if f"Q{int(row['Quarter'])} {int(row['Year'])}" == selected_period:
                                year_val = int(row['Year'])
                                quarter_val = int(row['Quarter'])
                                
                                with st.container(border=True):
                                    st.markdown(f"**📊 Detail per PJP - {selected_period} (Incoming)**")
                                    _render_pjp_detail(df_preprocessed_time, year_val, quarter_val, "Incoming")
                                break
                
                make_combined_bar_line_chart(
                    df_jumlah_inc_filtered,
                    "Jumlah",
                    "Inc",
                    font_size=_growth_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    axis_x_tick_bold=_growth_axis_x_tick_bold,
                    axis_y_tick_bold=_growth_axis_y_tick_bold,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
                make_combined_bar_line_chart(
                    df_nom_inc_filtered,
                    "Nilai",
                    "Inc",
                    font_size=_growth_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    axis_x_tick_bold=_growth_axis_x_tick_bold,
                    axis_y_tick_bold=_growth_axis_y_tick_bold,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
                st.divider()

            if selected_jenis_transaksi == 'Outgoing' or selected_jenis_transaksi == 'All':
                st.markdown("<h3 style='background-color: #fef2f2; border-left: 5px solid #ef4444; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px;'>📤 OUTGOING - Data Transaksi</h3>", unsafe_allow_html=True)
                
                # Display table with proper numeric sorting
                df_out_combined_display = rename_format_growth_df(df_out_combined.copy(), "Out")
                st.dataframe(
                    df_out_combined_display, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config=_get_growth_column_config("Outgoing")
                )
                
                # Detail selection with dropdown
                col_detail, col_empty = st.columns([3, 5])
                with col_detail:
                    period_options = [f"Q{int(row['Quarter'])} {int(row['Year'])}" for _, row in df_out_combined.iterrows()]
                    selected_period = st.selectbox("Pilih periode untuk detail", period_options, key="sel_out_period", label_visibility="collapsed")
                    if selected_period:
                        for idx, row in df_out_combined.iterrows():
                            if f"Q{int(row['Quarter'])} {int(row['Year'])}" == selected_period:
                                year_val = int(row['Year'])
                                quarter_val = int(row['Quarter'])
                                
                                with st.container(border=True):
                                    st.markdown(f"**📊 Detail per PJP - {selected_period} (Outgoing)**")
                                    _render_pjp_detail(df_preprocessed_time, year_val, quarter_val, "Outgoing")
                                break
                
                make_combined_bar_line_chart(
                    df_jumlah_out_filtered,
                    "Jumlah",
                    "Out",
                    font_size=_growth_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    axis_x_tick_bold=_growth_axis_x_tick_bold,
                    axis_y_tick_bold=_growth_axis_y_tick_bold,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
                make_combined_bar_line_chart(
                    df_nom_out_filtered,
                    "Nilai",
                    "Out",
                    font_size=_growth_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    axis_x_tick_bold=_growth_axis_x_tick_bold,
                    axis_y_tick_bold=_growth_axis_y_tick_bold,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
                st.divider()
                
            if selected_jenis_transaksi == 'Domestik' or selected_jenis_transaksi == 'All':
                st.markdown("<h3 style='background-color: #f0fdf4; border-left: 5px solid #16a34a; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px;'>🏠 DOMESTIK - Data Transaksi</h3>", unsafe_allow_html=True)
                
                # Display table with proper numeric sorting
                df_dom_combined_display = rename_format_growth_df(df_dom_combined.copy(), "Dom")
                st.dataframe(
                    df_dom_combined_display, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config=_get_growth_column_config("Domestik")
                )
                
                # Detail selection with dropdown
                col_detail, col_empty = st.columns([3, 5])
                with col_detail:
                    period_options = [f"Q{int(row['Quarter'])} {int(row['Year'])}" for _, row in df_dom_combined.iterrows()]
                    selected_period = st.selectbox("Pilih periode untuk detail", period_options, key="sel_dom_period", label_visibility="collapsed")
                    if selected_period:
                        for idx, row in df_dom_combined.iterrows():
                            if f"Q{int(row['Quarter'])} {int(row['Year'])}" == selected_period:
                                year_val = int(row['Year'])
                                quarter_val = int(row['Quarter'])
                                
                                with st.container(border=True):
                                    st.markdown(f"**📊 Detail per PJP - {selected_period} (Domestik)**")
                                    _render_pjp_detail(df_preprocessed_time, year_val, quarter_val, "Domestik")
                                break
                
                make_combined_bar_line_chart(
                    df_jumlah_dom_filtered,
                    "Jumlah",
                    "Dom",
                    font_size=_growth_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    axis_x_tick_bold=_growth_axis_x_tick_bold,
                    axis_y_tick_bold=_growth_axis_y_tick_bold,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
                make_combined_bar_line_chart(
                    df_nom_dom_filtered,
                    "Nilai",
                    "Dom",
                    font_size=_growth_font_size,
                    legend_font_size=_growth_legend_font_size,
                    axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                    axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                    axis_x_tick_bold=_growth_axis_x_tick_bold,
                    axis_y_tick_bold=_growth_axis_y_tick_bold,
                    chart_height=_growth_chart_height,
                    chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
                )
                st.divider()

            st.markdown("<h3 style='background-color: #fef3c7; border-left: 5px solid #f59e0b; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px; margin-top: 30px;'>💰 TOTAL KESELURUHAN - Data Transaksi (Kuartalan)</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color: #92400e; font-weight: 500; margin-bottom: 15px;'>Gabungan Data Transaksi Incoming + Outgoing + Domestik (Frekuensi & Nominal)</p>", unsafe_allow_html=True)
            
            df_total_combined_display = df_total_combined.copy()
            df_total_combined_display = rename_format_growth_df(df_total_combined_display, "Total")
            st.dataframe(
                df_total_combined_display, 
                use_container_width=True, 
                hide_index=True,
                column_config=_get_growth_column_config("Total")
            )
            
            # Detail selection with dropdown
            col_detail, col_empty = st.columns([3, 5])
            with col_detail:
                period_options = [f"Q{int(row['Quarter'])} {int(row['Year'])}" for _, row in df_total_combined.iterrows()]
                selected_period = st.selectbox("Pilih periode untuk detail", period_options, key="sel_total_period", label_visibility="collapsed")
                if selected_period:
                    for idx, row in df_total_combined.iterrows():
                        if f"Q{int(row['Quarter'])} {int(row['Year'])}" == selected_period:
                            year_val = int(row['Year'])
                            quarter_val = int(row['Quarter'])
                            
                            with st.container(border=True):
                                st.markdown(f"**📊 Detail per PJP - {selected_period} (Total)**")
                                _render_pjp_detail(df_preprocessed_time, year_val, quarter_val, "Total")
                                st.divider()
                                _render_pjp_supporting_tw_table(
                                    df_base=df_preprocessed_time,
                                    year=year_val,
                                    quarter=quarter_val,
                                    key_prefix=f"growth_tw_{year_val}Q{quarter_val}",
                                )
                            break

            st.markdown("<hr style='border-top: 2px dashed #f59e0b; margin: 20px 0;'>", unsafe_allow_html=True)
            st.markdown("### 📊 Visualisasi Keseluruhan Data Transaksi (Frekuensi & Nominal Tergabung)")

            st.caption(
                "Grafik berikut menampilkan stacked bar (Incoming/Outgoing/Domestik) pada sumbu kiri dan garis Growth (YoY & QtQ) pada sumbu kanan. "
                "Gunakan legend untuk menyembunyikan/menampilkan garis tertentu; label % akan ikut hilang saat garis di-hide."
            )

            # Visual-only filter: tampilkan/sematikan kuartal tertentu (growth tidak dihitung ulang)
            overall_period_options = (
                df_total_combined.assign(
                    _period=lambda d: d["Year"].astype(int).astype(str) + " Q" + d["Quarter"].astype(int).astype(str)
                )
                .sort_values(["Year", "Quarter"])
                ["_period"]
                .dropna()
                .astype(str)
                .tolist()
            )
            overall_period_sig = "|".join(overall_period_options)
            if st.session_state.get("overall_visible_period_sig") != overall_period_sig:
                st.session_state["overall_visible_period_sig"] = overall_period_sig
                st.session_state["overall_visible_periods"] = overall_period_options

            st.multiselect(
                "Tampilkan Kuartal",
                options=overall_period_options,
                key="overall_visible_periods",
                help="Hanya menyaring tampilan chart. Nilai YoY/QtQ tetap nilai asli dari perhitungan data.",
            )

            st.markdown("#### 📦 Volume / Frekuensi")
            st.caption("Sumbu kiri: Volume (Jutaan). Sumbu kanan: Growth YoY & QtQ (%).")

            make_overall_total_stacked_growth_chart(
                df_total=df_total_combined,
                df_inc=df_jumlah_inc_filtered,
                df_out=df_jumlah_out_filtered,
                df_dom=df_jumlah_dom_filtered,
                sum_trx_type="Jumlah",
                is_month=False,
                show_breakdown_growth=True,
                visible_periods=st.session_state.get("overall_visible_periods"),
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                axis_x_tick_bold=_growth_axis_x_tick_bold,
                axis_y_tick_bold=_growth_axis_y_tick_bold,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )
            _render_overall_growth_detail_table_quarterly(
                df_total_combined=df_total_combined,
                df_inc=df_jumlah_inc_filtered,
                df_out=df_jumlah_out_filtered,
                df_dom=df_jumlah_dom_filtered,
                sum_trx_type="Jumlah",
                visible_periods=st.session_state.get("overall_visible_periods"),
                ordered_periods=overall_period_options,
            )

            st.markdown("#### 💰 Nominal")
            st.caption("Sumbu kiri: Nilai (Rp Triliun). Sumbu kanan: Growth YoY & QtQ (%).")
            make_overall_total_stacked_growth_chart(
                df_total=df_total_combined,
                df_inc=df_nom_inc_filtered,
                df_out=df_nom_out_filtered,
                df_dom=df_nom_dom_filtered,
                sum_trx_type="Nilai",
                is_month=False,
                show_breakdown_growth=True,
                visible_periods=st.session_state.get("overall_visible_periods"),
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                axis_x_tick_bold=_growth_axis_x_tick_bold,
                axis_y_tick_bold=_growth_axis_y_tick_bold,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )
            _render_overall_growth_detail_table_quarterly(
                df_total_combined=df_total_combined,
                df_inc=df_nom_inc_filtered,
                df_out=df_nom_out_filtered,
                df_dom=df_nom_dom_filtered,
                sum_trx_type="Nilai",
                visible_periods=st.session_state.get("overall_visible_periods"),
                ordered_periods=overall_period_options,
            )

        # MONTHLY SECTION
        if st.session_state['view_mode'] == 'monthly':
            st.subheader("📅 Data Transaksi Bulanan")
            
            # KPI Cards - Monthly
            st.markdown("<h3 style='margin-top: 20px; margin-bottom: 15px;'>📈 Ringkasan Transaksi</h3>", unsafe_allow_html=True)
            
            # Calculate totals
            total_inc_freq_m = df_inc_combined_month['Sum of Fin Jumlah Inc'].sum()
            total_inc_value_m = df_inc_combined_month['Sum of Fin Nilai Inc'].sum()
            total_out_freq_m = df_out_combined_month['Sum of Fin Jumlah Out'].sum()
            total_out_value_m = df_out_combined_month['Sum of Fin Nilai Out'].sum()
            total_dom_freq_m = df_dom_combined_month['Sum of Fin Jumlah Dom'].sum()
            total_dom_value_m = df_dom_combined_month['Sum of Fin Nilai Dom'].sum()
            total_all_freq_m = total_inc_freq_m + total_out_freq_m + total_dom_freq_m
            total_all_value_m = total_inc_value_m + total_out_value_m + total_dom_value_m

            inc_t_m = qround_float(total_inc_value_m / 1e12, decimals=2, none=0.0) or 0.0
            out_t_m = qround_float(total_out_value_m / 1e12, decimals=2, none=0.0) or 0.0
            dom_t_m = qround_float(total_dom_value_m / 1e12, decimals=2, none=0.0) or 0.0
            tot_t_m = qround_float(inc_t_m + out_t_m + dom_t_m, decimals=2, none=0.0) or 0.0
            
            col1_kpi, col2_kpi, col3_kpi, col4_kpi = st.columns(4)
            
            with col1_kpi:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #F5B0CB;">
                    <div class="kpi-title">📥 INCOMING</div>
                    <div class="kpi-value-main" style="color: #F5B0CB;">{total_inc_freq_m:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #F5B0CB; margin-top: 12px;">Rp {format_en_decimal(inc_t_m, decimals=2, none='0.00')} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2_kpi:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #F5CBA7;">
                    <div class="kpi-title">📤 OUTGOING</div>
                    <div class="kpi-value-main" style="color: #F5CBA7;">{total_out_freq_m:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #F5CBA7; margin-top: 12px;">Rp {format_en_decimal(out_t_m, decimals=2, none='0.00')} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3_kpi:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #5DADE2;">
                    <div class="kpi-title">🏠 DOMESTIK</div>
                    <div class="kpi-value-main" style="color: #5DADE2;">{total_dom_freq_m:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #5DADE2; margin-top: 12px;">Rp {format_en_decimal(dom_t_m, decimals=2, none='0.00')} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4_kpi:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color: #6366f1;">
                    <div class="kpi-title">💰 TOTAL</div>
                    <div class="kpi-value-main" style="color: #6366f1;">{total_all_freq_m:,.0f}</div>
                    <div class="kpi-value-sub">Frekuensi</div>
                    <div class="kpi-value-main" style="color: #6366f1; margin-top: 12px;">Rp {format_en_decimal(tot_t_m, decimals=2, none='0.00')} T</div>
                    <div class="kpi-value-sub">Nilai</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
            
            # Grafik Gabungan (Stacked Bar + Line) - Monthly
            st.markdown("<h3 style='margin-bottom: 15px;'>📊 Grafik Gabungan - Nilai Transaksi</h3>", unsafe_allow_html=True)
            make_stacked_bar_line_chart_combined(
                df_inc_combined_month,
                df_out_combined_month,
                df_dom_combined_month,
                is_month=True,
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )
            
            st.divider()
            
            col1, col2, col3 = st.columns(3)
            
            if selected_jenis_transaksi == 'Incoming' or selected_jenis_transaksi == 'All':
                with col1:
                    st.markdown("<h4 style='background-color: #f0f7ff; border-left: 5px solid #3b82f6; padding: 10px 12px; border-radius: 5px; margin-bottom: 15px;'>📥 INCOMING (Bulanan)</h4>", unsafe_allow_html=True)
                    
                    df_inc_combined_month_display = rename_format_growth_monthly_df(df_inc_combined_month.copy(), "Inc")
                    st.dataframe(
                        df_inc_combined_month_display, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config=_get_growth_column_config("Incoming")
                    )
                    
                    # Detail selection with dropdown
                    period_options_m = [f"{row['Month']} {int(row['Year'])}" for _, row in df_inc_combined_month.iterrows()]
                    selected_period_m = st.selectbox("Detail:", period_options_m, key="sel_inc_m_period", label_visibility="collapsed")
                    if selected_period_m:
                        for idx, row in df_inc_combined_month.iterrows():
                            if f"{row['Month']} {int(row['Year'])}" == selected_period_m:
                                year_val = int(row['Year'])
                                month_val = row['Month']
                                
                                with st.container(border=True):
                                    st.markdown(f"**📊 Detail per PJP - {selected_period_m} (Incoming)**")
                                    _render_pjp_detail_month(df_preprocessed_time, year_val, str(month_val), "Incoming")
                                break
            
            if selected_jenis_transaksi == 'Outgoing' or selected_jenis_transaksi == 'All':
                with col2:
                    st.markdown("<h4 style='background-color: #fef2f2; border-left: 5px solid #ef4444; padding: 10px 12px; border-radius: 5px; margin-bottom: 15px;'>📤 OUTGOING (Bulanan)</h4>", unsafe_allow_html=True)
                    
                    df_out_combined_month_display = rename_format_growth_monthly_df(df_out_combined_month.copy(), "Out")
                    st.dataframe(
                        df_out_combined_month_display, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config=_get_growth_column_config("Outgoing")
                    )
                    
                    # Detail selection with dropdown
                    period_options_m = [f"{row['Month']} {int(row['Year'])}" for _, row in df_out_combined_month.iterrows()]
                    selected_period_m = st.selectbox("Detail:", period_options_m, key="sel_out_m_period", label_visibility="collapsed")
                    if selected_period_m:
                        for idx, row in df_out_combined_month.iterrows():
                            if f"{row['Month']} {int(row['Year'])}" == selected_period_m:
                                year_val = int(row['Year'])
                                month_val = row['Month']
                                
                                with st.container(border=True):
                                    st.markdown(f"**📊 Detail per PJP - {selected_period_m} (Outgoing)**")
                                    _render_pjp_detail_month(df_preprocessed_time, year_val, str(month_val), "Outgoing")
                                break
            
            if selected_jenis_transaksi == 'Domestik' or selected_jenis_transaksi == 'All':
                with col3:
                    st.markdown("<h4 style='background-color: #f0fdf4; border-left: 5px solid #16a34a; padding: 10px 12px; border-radius: 5px; margin-bottom: 15px;'>🏠 DOMESTIK (Bulanan)</h4>", unsafe_allow_html=True)
                    
                    df_dom_combined_month_display = rename_format_growth_monthly_df(df_dom_combined_month.copy(), "Dom")
                    st.dataframe(
                        df_dom_combined_month_display, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config=_get_growth_column_config("Domestik")
                    )
                    
                    # Detail selection with dropdown
                    period_options_m = [f"{row['Month']} {int(row['Year'])}" for _, row in df_dom_combined_month.iterrows()]
                    selected_period_m = st.selectbox("Detail:", period_options_m, key="sel_dom_m_period", label_visibility="collapsed")
                    if selected_period_m:
                        for idx, row in df_dom_combined_month.iterrows():
                            if f"{row['Month']} {int(row['Year'])}" == selected_period_m:
                                year_val = int(row['Year'])
                                month_val = row['Month']
                                
                                with st.container(border=True):
                                    st.markdown(f"**📊 Detail per PJP - {selected_period_m} (Domestik)**")
                                    _render_pjp_detail_month(df_preprocessed_time, year_val, str(month_val), "Domestik")
                                break
            
            st.divider()
            
            make_combined_bar_line_chart(
                df_jumlah_inc_month_filtered,
                "Jumlah",
                "Inc",
                True,
                font_size=_growth_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )
            make_combined_bar_line_chart(
                df_nom_inc_month_filtered,
                "Nilai",
                "Inc",
                True,
                font_size=_growth_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )

            make_combined_bar_line_chart(
                df_jumlah_out_month_filtered,
                "Jumlah",
                "Out",
                True,
                font_size=_growth_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )
            make_combined_bar_line_chart(
                df_nom_out_month_filtered,
                "Nilai",
                "Out",
                True,
                font_size=_growth_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )

            make_combined_bar_line_chart(
                df_jumlah_dom_month_filtered,
                "Jumlah",
                "Dom",
                True,
                font_size=_growth_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )
            make_combined_bar_line_chart(
                df_nom_dom_month_filtered,
                "Nilai",
                "Dom",
                True,
                font_size=_growth_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )

            st.markdown("<h3 style='background-color: #fef3c7; border-left: 5px solid #f59e0b; padding: 12px 15px; border-radius: 5px; margin-bottom: 20px; margin-top: 30px;'>💰 TOTAL KESELURUHAN - Data Transaksi (Bulanan)</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color: #92400e; font-weight: 500; margin-bottom: 15px;'>Gabungan Data Transaksi Incoming + Outgoing + Domestik per Bulan (Frekuensi & Nominal)</p>", unsafe_allow_html=True)
            df_total_month_combined_display = df_total_month_combined.copy()
            df_total_month_combined_display = rename_format_growth_monthly_df(df_total_month_combined_display, "Total")
            st.dataframe(
                df_total_month_combined_display, 
                use_container_width=True, 
                hide_index=True,
                column_config=_get_growth_column_config("Total")
            )
            
            # Detail selection with dropdown for monthly
            col_detail_m, col_empty_m = st.columns([3, 5])
            with col_detail_m:
                period_options_m = [f"{row['Month']} {int(row['Year'])}" for _, row in df_total_month_combined.iterrows()]
                selected_period_m = st.selectbox("Detail:", period_options_m, key="sel_total_m_period", label_visibility="collapsed")
                if selected_period_m:
                    for idx, row in df_total_month_combined.iterrows():
                        if f"{row['Month']} {int(row['Year'])}" == selected_period_m:
                            year_val = int(row['Year'])
                            month_val = row['Month']
                            
                            with st.container(border=True):
                                st.markdown(f"**📊 Detail per PJP - {selected_period_m} (Total)**")
                                _render_pjp_detail_month(df_preprocessed_time, year_val, str(month_val), "Total")
                            break

            st.markdown("<hr style='border-top: 2px dashed #f59e0b; margin: 20px 0;'>", unsafe_allow_html=True)
            st.markdown("### 📅 Visualisasi Keseluruhan Data Transaksi (Frekuensi & Nominal Tergabung)")
            make_overall_total_stacked_growth_chart(
                df_total=df_total_month_combined,
                df_inc=df_jumlah_inc_month_filtered,
                df_out=df_jumlah_out_month_filtered,
                df_dom=df_jumlah_dom_month_filtered,
                sum_trx_type="Jumlah",
                is_month=True,
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                axis_x_tick_bold=_growth_axis_x_tick_bold,
                axis_y_tick_bold=_growth_axis_y_tick_bold,
                chart_height=_growth_chart_height,
            )
            make_overall_total_stacked_growth_chart(
                df_total=df_total_month_combined,
                df_inc=df_nom_inc_month_filtered,
                df_out=df_nom_out_month_filtered,
                df_dom=df_nom_dom_month_filtered,
                sum_trx_type="Nilai",
                is_month=True,
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                axis_x_tick_bold=_growth_axis_x_tick_bold,
                axis_y_tick_bold=_growth_axis_y_tick_bold,
                chart_height=_growth_chart_height,
            )

        # YEARLY SECTION
        if st.session_state['view_mode'] == 'yearly':
            st.subheader("🗓️ Data Transaksi Tahunan")
            st.caption("Catatan: tanda '*' berarti data tahun tersebut tidak lengkap (terpotong karena filter Start/End Quarter).")

            # KPI Cards - Yearly (per Tahun)
            if df_total_combined is None or df_total_combined.empty:
                st.info("Tidak ada data pada rentang tahun/kuartal yang dipilih.")
            else:
                def _safe_year_sum(df_src: pd.DataFrame | None, value_col: str) -> pd.Series:
                    if df_src is None or df_src.empty:
                        return pd.Series(dtype="float64")
                    if "Year" not in df_src.columns or value_col not in df_src.columns:
                        return pd.Series(dtype="float64")
                    dfc = df_src[["Year", value_col]].copy()
                    dfc["Year"] = pd.to_numeric(dfc["Year"], errors="coerce")
                    dfc[value_col] = pd.to_numeric(dfc[value_col], errors="coerce")
                    dfc = dfc.dropna(subset=["Year"]).copy()
                    if dfc.empty:
                        return pd.Series(dtype="float64")
                    dfc["Year"] = dfc["Year"].astype(int)
                    return dfc.groupby("Year", observed=False)[value_col].sum()

                years = (
                    df_total_combined["Year"].dropna().astype(int).sort_values().unique().tolist()
                    if "Year" in df_total_combined.columns
                    else []
                )

                q_counts = (
                    df_total_combined.groupby("Year", observed=False)["Quarter"].nunique()
                    if {"Year", "Quarter"}.issubset(set(df_total_combined.columns))
                    else pd.Series(dtype="int64")
                )
                is_partial_map = {int(y): (int(q_counts.get(int(y), 0)) < 4) for y in years}

                # Annual totals (Nominal)
                inc_nom_y = _safe_year_sum(df_nom_inc_filtered, "Sum of Fin Nilai Inc")
                out_nom_y = _safe_year_sum(df_nom_out_filtered, "Sum of Fin Nilai Out")
                dom_nom_y = _safe_year_sum(df_nom_dom_filtered, "Sum of Fin Nilai Dom")

                # Annual totals (Frekuensi)
                inc_freq_y = _safe_year_sum(df_jumlah_inc_filtered, "Sum of Fin Jumlah Inc")
                out_freq_y = _safe_year_sum(df_jumlah_out_filtered, "Sum of Fin Jumlah Out")
                dom_freq_y = _safe_year_sum(df_jumlah_dom_filtered, "Sum of Fin Jumlah Dom")

                yearly = pd.DataFrame({"Year": years})
                yearly["Incoming_Nominal"] = yearly["Year"].map(inc_nom_y).fillna(0.0)
                yearly["Outgoing_Nominal"] = yearly["Year"].map(out_nom_y).fillna(0.0)
                yearly["Domestik_Nominal"] = yearly["Year"].map(dom_nom_y).fillna(0.0)
                yearly["Total_Nominal"] = yearly["Incoming_Nominal"] + yearly["Outgoing_Nominal"] + yearly["Domestik_Nominal"]

                yearly["Incoming_Frekuensi"] = yearly["Year"].map(inc_freq_y).fillna(0.0)
                yearly["Outgoing_Frekuensi"] = yearly["Year"].map(out_freq_y).fillna(0.0)
                yearly["Domestik_Frekuensi"] = yearly["Year"].map(dom_freq_y).fillna(0.0)
                yearly["Total_Frekuensi"] = yearly["Incoming_Frekuensi"] + yearly["Outgoing_Frekuensi"] + yearly["Domestik_Frekuensi"]

                yearly["YoY_Total_Nominal"] = yearly["Total_Nominal"].pct_change() * 100
                yearly["YoY_Total_Frekuensi"] = yearly["Total_Frekuensi"].pct_change() * 100

                def _fmt_yoy(v: float | None) -> str:
                    if v is None or pd.isna(v):
                        return "-"
                    return (
                        format_id_percent(v, decimals=2, show_sign=True, none="-", space_before_percent=False)
                        .replace(",00%", "%")
                    )

                st.markdown("<h3 style='margin-top: 20px; margin-bottom: 15px;'>📈 KPI Tahunan</h3>", unsafe_allow_html=True)

                year_labels = [f"{int(y)}{'*' if is_partial_map.get(int(y), False) else ''}" for y in years]
                label_to_year = {lbl: int(lbl.replace("*", "")) for lbl in year_labels}
                default_label = year_labels[-1] if year_labels else None
                selected_year_label = st.selectbox(
                    "Pilih Tahun (untuk KPI)",
                    options=year_labels,
                    index=(len(year_labels) - 1) if year_labels else 0,
                    key="yearly_kpi_year",
                )
                selected_year = label_to_year.get(selected_year_label, years[-1] if years else None)

                row = yearly[yearly["Year"] == int(selected_year)].iloc[0] if selected_year is not None else None

                if row is not None:
                    inc_freq = float(row["Incoming_Frekuensi"]) if not pd.isna(row["Incoming_Frekuensi"]) else 0.0
                    out_freq = float(row["Outgoing_Frekuensi"]) if not pd.isna(row["Outgoing_Frekuensi"]) else 0.0
                    dom_freq = float(row["Domestik_Frekuensi"]) if not pd.isna(row["Domestik_Frekuensi"]) else 0.0
                    tot_freq = float(row["Total_Frekuensi"]) if not pd.isna(row["Total_Frekuensi"]) else 0.0

                    inc_nom = float(row["Incoming_Nominal"]) if not pd.isna(row["Incoming_Nominal"]) else 0.0
                    out_nom = float(row["Outgoing_Nominal"]) if not pd.isna(row["Outgoing_Nominal"]) else 0.0
                    dom_nom = float(row["Domestik_Nominal"]) if not pd.isna(row["Domestik_Nominal"]) else 0.0
                    tot_nom = float(row["Total_Nominal"]) if not pd.isna(row["Total_Nominal"]) else 0.0

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.markdown(f"""
                        <div class="kpi-card" style="border-left-color: #F5B0CB;">
                            <div class="kpi-title">📥 INCOMING ({selected_year_label})</div>
                            <div class="kpi-value-main" style="color: #F5B0CB;">{inc_freq:,.0f}</div>
                            <div class="kpi-value-sub">Frekuensi</div>
                            <div class="kpi-value-main" style="color: #F5B0CB; margin-top: 12px;">Rp {format_en_decimal(inc_nom/1e12, decimals=2, none='0.00')} T</div>
                            <div class="kpi-value-sub">Nilai</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        st.markdown(f"""
                        <div class="kpi-card" style="border-left-color: #F5CBA7;">
                            <div class="kpi-title">📤 OUTGOING ({selected_year_label})</div>
                            <div class="kpi-value-main" style="color: #F5CBA7;">{out_freq:,.0f}</div>
                            <div class="kpi-value-sub">Frekuensi</div>
                            <div class="kpi-value-main" style="color: #F5CBA7; margin-top: 12px;">Rp {format_en_decimal(out_nom/1e12, decimals=2, none='0.00')} T</div>
                            <div class="kpi-value-sub">Nilai</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with col3:
                        st.markdown(f"""
                        <div class="kpi-card" style="border-left-color: #5DADE2;">
                            <div class="kpi-title">🏠 DOMESTIK ({selected_year_label})</div>
                            <div class="kpi-value-main" style="color: #5DADE2;">{dom_freq:,.0f}</div>
                            <div class="kpi-value-sub">Frekuensi</div>
                            <div class="kpi-value-main" style="color: #5DADE2; margin-top: 12px;">Rp {format_en_decimal(dom_nom/1e12, decimals=2, none='0.00')} T</div>
                            <div class="kpi-value-sub">Nilai</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with col4:
                        st.markdown(f"""
                        <div class="kpi-card" style="border-left-color: #6366f1;">
                            <div class="kpi-title">💰 TOTAL ({selected_year_label})</div>
                            <div class="kpi-value-main" style="color: #6366f1;">{tot_freq:,.0f}</div>
                            <div class="kpi-value-sub">Frekuensi</div>
                            <div class="kpi-value-main" style="color: #6366f1; margin-top: 12px;">Rp {format_en_decimal(tot_nom/1e12, decimals=2, none='0.00')} T</div>
                            <div class="kpi-value-sub">Nilai</div>
                        </div>
                        """, unsafe_allow_html=True)

                    # YoY info for selected year (Total)
                    yoy_nom = yearly.loc[yearly["Year"] == int(selected_year), "YoY_Total_Nominal"].iloc[0]
                    yoy_freq = yearly.loc[yearly["Year"] == int(selected_year), "YoY_Total_Frekuensi"].iloc[0]
                    st.caption(f"YoY Total Nominal: {_fmt_yoy(yoy_nom)} | YoY Total Frekuensi: {_fmt_yoy(yoy_freq)}")

                with st.expander("📋 Ringkasan Tahunan (Tabel)", expanded=False):
                    table = yearly.copy()
                    table["Incoming (Rp T)"] = table["Incoming_Nominal"] / 1e12
                    table["Outgoing (Rp T)"] = table["Outgoing_Nominal"] / 1e12
                    table["Domestik (Rp T)"] = table["Domestik_Nominal"] / 1e12
                    table["Total (Rp T)"] = table["Total_Nominal"] / 1e12
                    table["YoY Total Nominal (%)"] = table["YoY_Total_Nominal"]
                    table["YoY Total Frekuensi (%)"] = table["YoY_Total_Frekuensi"]
                    table["Data Lengkap?"] = table["Year"].map(lambda y: "Lengkap" if not is_partial_map.get(int(y), False) else "Parsial*")

                    for c in [
                        "Incoming (Rp T)",
                        "Outgoing (Rp T)",
                        "Domestik (Rp T)",
                        "Total (Rp T)",
                        "YoY Total Nominal (%)",
                        "YoY Total Frekuensi (%)",
                    ]:
                        if c in table.columns:
                            table[c] = pd.to_numeric(table[c], errors="coerce").map(lambda x: qround_float(x, decimals=2, none=0.0))

                    if {"Incoming (Rp T)", "Outgoing (Rp T)", "Domestik (Rp T)", "Total (Rp T)"}.issubset(set(table.columns)):
                        table["Total (Rp T)"] = (
                            pd.to_numeric(table["Incoming (Rp T)"], errors="coerce").fillna(0.0)
                            + pd.to_numeric(table["Outgoing (Rp T)"], errors="coerce").fillna(0.0)
                            + pd.to_numeric(table["Domestik (Rp T)"], errors="coerce").fillna(0.0)
                        ).map(lambda x: qround_float(x, decimals=2, none=0.0))

                    st.dataframe(
                        table[[
                            "Year",
                            "Incoming (Rp T)",
                            "Outgoing (Rp T)",
                            "Domestik (Rp T)",
                            "Total (Rp T)",
                            "YoY Total Nominal (%)",
                            "YoY Total Frekuensi (%)",
                            "Data Lengkap?",
                        ]],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Year": st.column_config.NumberColumn("Year", format="%d"),
                            "Incoming (Rp T)": st.column_config.NumberColumn("Incoming (Rp T)", format="%.2f"),
                            "Outgoing (Rp T)": st.column_config.NumberColumn("Outgoing (Rp T)", format="%.2f"),
                            "Domestik (Rp T)": st.column_config.NumberColumn("Domestik (Rp T)", format="%.2f"),
                            "Total (Rp T)": st.column_config.NumberColumn("Total (Rp T)", format="%.2f"),
                            "YoY Total Nominal (%)": st.column_config.NumberColumn("YoY Total Nominal (%)", format="%+.2f%%"),
                            "YoY Total Frekuensi (%)": st.column_config.NumberColumn("YoY Total Frekuensi (%)", format="%+.2f%%"),
                        },
                    )

            st.markdown(
                "<h3 style='margin-bottom: 15px;'>📊 Grafik Tahunan — Nilai Transaksi (Rp Triliun) + YoY (%)</h3>",
                unsafe_allow_html=True,
            )
            make_yearly_stacked_bar_yoy_chart(
                df_inc=df_nom_inc_filtered,
                df_out=df_nom_out_filtered,
                df_dom=df_nom_dom_filtered,
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                axis_x_tick_bold=_growth_axis_x_tick_bold,
                axis_y_tick_bold=_growth_axis_y_tick_bold,
                axis_x_tick_weight=_growth_axis_x_tick_weight,
                axis_y_tick_weight=_growth_axis_y_tick_weight,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )

            st.markdown(
                "<h3 style='margin-top: 20px; margin-bottom: 15px;'>📊 Grafik Tahunan (Khusus 2025 = Jan–Sep) — Nilai Transaksi (Rp Triliun) + YoY (%)</h3>",
                unsafe_allow_html=True,
            )
            st.caption(
                "Sumbu nilai dalam Rp Triliun (Rp T). Bar 2025 memakai akumulasi Jan–Sep, tahun lainnya Jan–Des. "
                "Untuk YoY 2025: bandingkan Jan–Sep 2025 vs Jan–Sep 2024; YoY 2024 tetap full-year vs 2023."
            )
            make_yearly_stacked_bar_yoy_chart_ytd(
                df_inc=df_nom_inc_month_filtered,
                df_out=df_nom_out_month_filtered,
                df_dom=df_nom_dom_month_filtered,
                end_month=9,
                cap_years={2025},
                default_end_month=12,
                yoy_cap_years={2025},
                font_size=_growth_font_size,
                label_font_size=_growth_label_font_size,
                legend_font_size=_growth_legend_font_size,
                axis_x_tick_font_size=_growth_axis_x_tick_font_size,
                axis_y_tick_font_size=_growth_axis_y_tick_font_size,
                axis_x_tick_bold=_growth_axis_x_tick_bold,
                axis_y_tick_bold=_growth_axis_y_tick_bold,
                axis_x_tick_weight=_growth_axis_x_tick_weight,
                axis_y_tick_weight=_growth_axis_y_tick_weight,
                chart_height=_growth_chart_height,
                chart_width=_growth_chart_width if _growth_chart_width > 0 else None,
            )

else:
    st.warning("Please Upload the Main Excel File first in the Summary Section.")

