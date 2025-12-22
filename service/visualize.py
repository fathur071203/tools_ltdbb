import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import calendar


def make_stacked_bar_line_chart_combined(
    df_inc,
    df_out,
    df_dom,
    is_month: bool = False,
    *,
    font_size: int | None = None,
    label_font_size: int | None = None,
    legend_font_size: int | None = None,
    axis_x_tick_font_size: int | None = None,
    axis_y_tick_font_size: int | None = None,
    chart_height: int | None = None,
    chart_width: int | None = None,
):
    """
    Membuat grafik gabungan dengan stacked bar (Inc, Out, Dom) dan line growth (YoY)
    """
    # Merge dataframes
    if is_month:
        df_merged = df_inc[['Year', 'Month', 'Sum of Fin Nilai Inc']].copy()
        df_merged = df_merged.merge(df_out[['Year', 'Month', 'Sum of Fin Nilai Out']], on=['Year', 'Month'], how='outer')
        df_merged = df_merged.merge(df_dom[['Year', 'Month', 'Sum of Fin Nilai Dom', '%MtM Nom']], on=['Year', 'Month'], how='outer')
        df_merged['Year-Month'] = df_merged['Year'].astype(str) + '-' + df_merged['Month'].astype(str)
        df_merged = df_merged.sort_values(['Year', 'Month'])
        x_col = 'Year-Month'
        period_label = "Bulan"
        growth_col = '%MtM Nom'
        growth_label = 'Growth MtM (%)'
    else:
        df_merged = df_inc[['Year', 'Quarter', 'Sum of Fin Nilai Inc']].copy()
        df_merged = df_merged.merge(df_out[['Year', 'Quarter', 'Sum of Fin Nilai Out']], on=['Year', 'Quarter'], how='outer')
        df_merged = df_merged.merge(df_dom[['Year', 'Quarter', 'Sum of Fin Nilai Dom', '%YoY Nom']], on=['Year', 'Quarter'], how='outer')
        df_merged['Year-Quarter'] = df_merged['Year'].astype(str) + ' Q' + df_merged['Quarter'].astype(str)
        df_merged = df_merged.sort_values(['Year', 'Quarter'])
        x_col = 'Year-Quarter'
        period_label = "Kuartal"
        growth_col = '%YoY Nom'
        growth_label = 'Growth YoY (%)'
    
    # Filter rows with valid growth data
    df_merged = df_merged[df_merged[growth_col].notnull()]
    
    # Scale to Miliar
    scale_factor = 1e9
    
    fs = int(font_size) if font_size is not None else 12
    x_tick_fs = int(axis_x_tick_font_size) if axis_x_tick_font_size is not None else max(fs - 1, 9)
    y_tick_fs = int(axis_y_tick_font_size) if axis_y_tick_font_size is not None else max(fs - 1, 9)
    axis_title_fs = fs + 2
    title_fs = fs + 10
    hover_fs = fs
    label_fs = int(label_font_size) if label_font_size is not None else y_tick_fs
    legend_fs = int(legend_font_size) if legend_font_size is not None else fs

    fig = go.Figure()
    
    # Stacked bars - Incoming (Pink)
    fig.add_trace(go.Bar(
        x=df_merged[x_col],
        y=df_merged['Sum of Fin Nilai Inc'] / scale_factor,
        name='Incoming',
        marker=dict(color='#F5B0CB', line=dict(width=0)),
        hovertemplate='%{x}<br>Incoming: Rp %{y:,.2f} Miliar<extra></extra>',
        yaxis='y1'
    ))
    
    # Stacked bars - Outgoing (Peach/Orange)
    fig.add_trace(go.Bar(
        x=df_merged[x_col],
        y=df_merged['Sum of Fin Nilai Out'] / scale_factor,
        name='Outgoing',
        marker=dict(color='#F5CBA7', line=dict(width=0)),
        hovertemplate='%{x}<br>Outgoing: Rp %{y:,.2f} Miliar<extra></extra>',
        yaxis='y1'
    ))
    
    # Stacked bars - Domestik (Blue)
    fig.add_trace(go.Bar(
        x=df_merged[x_col],
        y=df_merged['Sum of Fin Nilai Dom'] / scale_factor,
        name='Domestik',
        marker=dict(color='#5DADE2', line=dict(width=0)),
        hovertemplate='%{x}<br>Domestik: Rp %{y:,.2f} Miliar<extra></extra>',
        yaxis='y1'
    ))
    
    # Line - Growth (Dark Green) with data labels
    fig.add_trace(go.Scatter(
        x=df_merged[x_col],
        y=df_merged[growth_col],
        name=growth_label,
        yaxis='y2',
        mode='lines+markers+text',
        line=dict(color='#1E8449', width=3),
        marker=dict(size=8, color='#1E8449', line=dict(color='white', width=2)),
        text=[f"{val:.1f}%" for val in df_merged[growth_col]],
        textposition='top center',
        textfont=dict(
            size=label_fs,
            color='#1E8449',
            family='Inter, Arial, sans-serif',
            weight='bold'
        ),
        hovertemplate='%{x}<br>' + growth_label + ': %{y:.2f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=f"Perkembangan Nilai Transaksi Gabungan (Per {period_label})",
            font=dict(size=title_fs, family='Inter, Arial, sans-serif', color='#1f2937', weight=700)
        ),
        barmode='stack',
        xaxis=dict(
            title=dict(text="Periode", font=dict(size=axis_title_fs, family='Inter, Arial, sans-serif'), standoff=15),
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor='#d1d5db',
            tickangle=-45,
            tickfont=dict(size=x_tick_fs, family='Inter, Arial, sans-serif')
        ),
        yaxis=dict(
            title=dict(text="Nilai (Rp Miliar)", font=dict(size=axis_title_fs, family='Inter, Arial, sans-serif'), standoff=15),
            tickformat=",.0f",
            showgrid=True,
            gridwidth=1,
            gridcolor='#e5e7eb',
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='#d1d5db',
            tickfont=dict(size=y_tick_fs, family='Inter, Arial, sans-serif')
        ),
        yaxis2=dict(
            title=dict(text='Growth (%)', font=dict(size=axis_title_fs, family='Inter, Arial, sans-serif'), standoff=15),
            overlaying='y',
            side='right',
            tickformat=".1f",
            showgrid=False,
            tickfont=dict(size=y_tick_fs, family='Inter, Arial, sans-serif')
        ),
        template="plotly_white",
        paper_bgcolor='white',
        plot_bgcolor='#f9fafb',
        font=dict(family='Inter, Arial, sans-serif', size=fs),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='#e5e7eb',
            borderwidth=1,
            font=dict(size=legend_fs, family='Inter, Arial, sans-serif')
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=hover_fs,
            font_family="Inter, Arial, sans-serif"
        )
    )

    if chart_height is not None:
        fig.update_layout(height=int(chart_height))

    if chart_width is not None and int(chart_width) > 0:
        fig.update_layout(width=int(chart_width))
        st.plotly_chart(fig, use_container_width=False)
    else:
        st.plotly_chart(fig, use_container_width=True)


def make_yearly_stacked_bar_yoy_chart(
    df_inc: pd.DataFrame,
    df_out: pd.DataFrame,
    df_dom: pd.DataFrame,
    *,
    font_size: int | None = None,
    legend_font_size: int | None = None,
    axis_x_tick_font_size: int | None = None,
    axis_y_tick_font_size: int | None = None,
    chart_height: int | None = None,
    chart_width: int | None = None,
):
    """Grafik Tahunan: stacked bar (Nilai) + garis YoY (%) dengan label boxed (mirip contoh)."""

    # Aggregate per year (respect partial year if filter by quarter makes incomplete years)
    def _agg_year(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["Year", value_col, "_nq"])
        d = df.copy()
        if "Quarter" in d.columns:
            g = d.groupby("Year", observed=False).agg({value_col: "sum", "Quarter": pd.Series.nunique}).reset_index()
            g = g.rename(columns={"Quarter": "_nq"})
        else:
            g = d.groupby("Year", observed=False).agg({value_col: "sum"}).reset_index()
            g["_nq"] = 4
        return g

    inc_col = "Sum of Fin Nilai Inc"
    out_col = "Sum of Fin Nilai Out"
    dom_col = "Sum of Fin Nilai Dom"

    inc_y = _agg_year(df_inc, inc_col)
    out_y = _agg_year(df_out, out_col)
    dom_y = _agg_year(df_dom, dom_col)

    df_y = inc_y.merge(out_y[["Year", out_col, "_nq"]], on="Year", how="outer", suffixes=("", "_out"))
    df_y = df_y.merge(dom_y[["Year", dom_col, "_nq"]], on="Year", how="outer", suffixes=("", "_dom"))

    if df_y.empty:
        st.info("Data tidak cukup untuk membuat grafik tahunan.")
        return

    # consolidate nq (max across sources)
    def _max3(a, b, c):
        vals = [v for v in [a, b, c] if pd.notna(v)]
        return int(max(vals)) if vals else 4

    df_y["_nq_out"] = df_y.get("_nq_out")
    df_y["_nq_dom"] = df_y.get("_nq_dom")
    df_y["_nq"] = df_y.apply(lambda r: _max3(r.get("_nq"), r.get("_nq_out"), r.get("_nq_dom")), axis=1)

    df_y["YearInt"] = pd.to_numeric(df_y.get("Year"), errors="coerce")
    df_y = df_y.dropna(subset=["YearInt"]).copy()
    df_y["YearInt"] = df_y["YearInt"].astype(int)

    df_y[inc_col] = pd.to_numeric(df_y.get(inc_col), errors="coerce").fillna(0.0)
    df_y[out_col] = pd.to_numeric(df_y.get(out_col), errors="coerce").fillna(0.0)
    df_y[dom_col] = pd.to_numeric(df_y.get(dom_col), errors="coerce").fillna(0.0)
    df_y = df_y.sort_values("YearInt")

    df_y["_partial"] = df_y["_nq"].astype(int) < 4
    df_y["YearLabel"] = df_y["YearInt"].astype(int).astype(str) + df_y["_partial"].apply(lambda v: "*" if bool(v) else "")

    df_y["Total"] = df_y[inc_col] + df_y[out_col] + df_y[dom_col]
    df_y["YoY"] = df_y["Total"].pct_change() * 100

    # mark yoy label with * if current or previous year is partial
    prev_partial = df_y["_partial"].shift(1).fillna(False)
    df_y["_yoy_partial"] = (df_y["_partial"] | prev_partial).astype(bool)

    # Scale to Rp Miliar
    scale_factor = 1e9

    fs = int(font_size) if font_size is not None else 12
    x_tick_fs = int(axis_x_tick_font_size) if axis_x_tick_font_size is not None else max(fs - 1, 9)
    y_tick_fs = int(axis_y_tick_font_size) if axis_y_tick_font_size is not None else max(fs - 1, 9)
    axis_title_fs = fs + 2
    title_fs = fs + 10
    hover_fs = fs
    legend_fs = int(legend_font_size) if legend_font_size is not None else fs

    fig = go.Figure()

    x_years = df_y["YearInt"].astype(int).tolist()
    x_text = df_y["YearLabel"].astype(str).tolist()

    fig.add_trace(
        go.Bar(
            x=x_years,
            y=df_y[inc_col] / scale_factor,
            name="Incoming",
            marker=dict(color="#F5B0CB", line=dict(width=0)),
            hovertemplate="%{x}<br>Incoming: Rp %{y:,.2f} Miliar<extra></extra>",
            yaxis="y1",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_years,
            y=df_y[out_col] / scale_factor,
            name="Outgoing",
            marker=dict(color="#F5CBA7", line=dict(width=0)),
            hovertemplate="%{x}<br>Outgoing: Rp %{y:,.2f} Miliar<extra></extra>",
            yaxis="y1",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_years,
            y=df_y[dom_col] / scale_factor,
            name="Domestik",
            marker=dict(color="#5DADE2", line=dict(width=0)),
            hovertemplate="%{x}<br>Domestik: Rp %{y:,.2f} Miliar<extra></extra>",
            yaxis="y1",
        )
    )

    yoy_color = "#60A5FA"  # keep consistent with existing palette family
    fig.add_trace(
        go.Scatter(
            x=x_years,
            y=df_y["YoY"],
            name="YoY",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color=yoy_color, width=4),
            marker=dict(size=10, color=yoy_color, line=dict(color="white", width=2)),
            hovertemplate="%{x}<br>YoY: %{y:.2f}%<extra></extra>",
        )
    )

    # Boxed labels (annotations) for YoY
    yoy_vals = pd.to_numeric(df_y["YoY"], errors="coerce")
    valid = yoy_vals.dropna().astype(float)
    if not valid.empty:
        vmin = float(valid.min())
        vmax = float(valid.max())
        span = vmax - vmin
        gap = max(5.0, span * 0.10)
        placed: list[float] = []

        def _place(y: float) -> float:
            pos = float(y)
            direction = 1.0
            tries = 0
            while any(abs(pos - p) < gap for p in placed) and tries < 12:
                pos += direction * gap
                direction *= -1
                tries += 1
            placed.append(pos)
            return pos

        for x, y, is_partial in zip(x_years, yoy_vals.tolist(), df_y["_yoy_partial"].tolist()):
            if y is None or (isinstance(y, float) and pd.isna(y)):
                continue
            y_float = float(y)
            y_used = _place(y_float)
            suffix = "*" if bool(is_partial) else ""
            fig.add_annotation(
                x=x,
                y=y_used,
                xref="x",
                yref="y2",
                text=f"{y_float:.2f}%{suffix}",
                showarrow=False,
                xanchor="center",
                yanchor="bottom",
                font=dict(size=max(9, fs), family="Inter, Arial, sans-serif", color="#111827"),
                bgcolor="rgba(245, 158, 11, 0.95)",
                bordercolor="rgba(245, 158, 11, 1.0)",
                borderwidth=0,
                borderpad=4,
            )

        # expand y2 range to include annotations
        all_y = placed + valid.tolist()
        ymin = float(min(all_y))
        ymax = float(max(all_y))
        pad = max(5.0, (ymax - ymin) * 0.15)
        y2_range = [ymin - pad, ymax + pad]
    else:
        y2_range = None

    fig.update_layout(
        title=dict(
            text="Perkembangan Nilai Transaksi Tahunan (Stacked) & YoY (%)",
            font=dict(size=title_fs, family="Inter, Arial, sans-serif", color="#1f2937", weight=700),
        ),
        barmode="stack",
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="#f9fafb",
        font=dict(family="Inter, Arial, sans-serif", size=fs),
        xaxis=dict(
            title=dict(text="Tahun", font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            tickfont=dict(size=x_tick_fs, family="Inter, Arial, sans-serif"),
            type="linear",
            tickmode="array",
            tickvals=x_years,
            ticktext=x_text,
            range=[min(x_years) - 0.6, max(x_years) + 0.6] if x_years else None,
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor="#d1d5db",
        ),
        yaxis=dict(
            title=dict(text="Rp Miliar", font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            tickformat=",.0f",
            tickfont=dict(size=y_tick_fs, family="Inter, Arial, sans-serif"),
            showgrid=True,
            gridcolor="#e5e7eb",
        ),
        yaxis2=dict(
            title=dict(text="YoY (%)", font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            overlaying="y",
            side="right",
            tickformat=".0f",
            tickfont=dict(size=y_tick_fs, family="Inter, Arial, sans-serif"),
            showgrid=False,
            range=y2_range,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#e5e7eb",
            borderwidth=1,
            font=dict(size=legend_fs, family="Inter, Arial, sans-serif"),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=hover_fs, font_family="Inter, Arial, sans-serif"),
        margin=dict(l=60, r=80, t=80, b=80),
    )

    if chart_height is not None:
        fig.update_layout(height=int(chart_height))

    if chart_width is not None and int(chart_width) > 0:
        fig.update_layout(width=int(chart_width))
        st.plotly_chart(fig, use_container_width=False)
    else:
        st.plotly_chart(fig, use_container_width=True)


def make_yearly_stacked_bar_yoy_chart_ytd(
    df_inc: pd.DataFrame,
    df_out: pd.DataFrame,
    df_dom: pd.DataFrame,
    *,
    end_month: int = 9,
    cap_years: set[int] | None = None,
    default_end_month: int = 12,
    font_size: int | None = None,
    legend_font_size: int | None = None,
    axis_x_tick_font_size: int | None = None,
    axis_y_tick_font_size: int | None = None,
    chart_height: int | None = None,
    chart_width: int | None = None,
):
    """Grafik Tahunan (YTD): stacked bar (Nilai) + garis YoY (%).

    - Jika cap_years None: semua tahun memakai Jan..end_month.
    - Jika cap_years diberikan: hanya tahun dalam cap_years yang memakai Jan..end_month,
      sementara tahun lain memakai Jan..default_end_month.
    """

    end_month_int = int(end_month)
    if end_month_int < 1 or end_month_int > 12:
        st.warning("end_month harus 1..12")
        return

    default_end_month_int = int(default_end_month)
    if default_end_month_int < 1 or default_end_month_int > 12:
        st.warning("default_end_month harus 1..12")
        return

    cap_years_set = set(cap_years) if cap_years else None

    def _limit_for_year(year_int: int) -> int:
        if cap_years_set is None:
            return end_month_int
        return end_month_int if int(year_int) in cap_years_set else default_end_month_int

    def _month_to_int(v) -> int | None:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        s = str(v).strip()
        if not s:
            return None
        try:
            mi = int(float(s))
            return mi if 1 <= mi <= 12 else None
        except Exception:
            pass
        # handle month name (English)
        try:
            mi = list(calendar.month_name).index(s)
            return mi if 1 <= mi <= 12 else None
        except Exception:
            return None

    def _agg_year_ytd(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["Year", value_col, "_nm"])
        d = df.copy()
        if "Year" not in d.columns or "Month" not in d.columns:
            return pd.DataFrame(columns=["Year", value_col, "_nm"])

        d["YearInt"] = pd.to_numeric(d["Year"], errors="coerce")
        d["MonthInt"] = d["Month"].apply(_month_to_int)
        d = d.dropna(subset=["YearInt", "MonthInt"]).copy()
        if d.empty:
            return pd.DataFrame(columns=["Year", value_col, "_nm"])

        d["YearInt"] = d["YearInt"].astype(int)
        d["MonthInt"] = d["MonthInt"].astype(int)
        d[value_col] = pd.to_numeric(d.get(value_col), errors="coerce")

        d["_limit"] = d["YearInt"].apply(_limit_for_year)
        d = d[d["MonthInt"] <= d["_limit"]].copy()
        if d.empty:
            return pd.DataFrame(columns=["Year", value_col, "_nm"])

        g = (
            d.groupby("YearInt", observed=False)
            .agg({value_col: "sum", "MonthInt": pd.Series.nunique})
            .reset_index()
            .rename(columns={"YearInt": "Year", "MonthInt": "_nm"})
        )
        return g

    inc_col = "Sum of Fin Nilai Inc"
    out_col = "Sum of Fin Nilai Out"
    dom_col = "Sum of Fin Nilai Dom"

    inc_y = _agg_year_ytd(df_inc, inc_col)
    out_y = _agg_year_ytd(df_out, out_col)
    dom_y = _agg_year_ytd(df_dom, dom_col)

    df_y = inc_y.merge(out_y[["Year", out_col, "_nm"]], on="Year", how="outer", suffixes=("", "_out"))
    df_y = df_y.merge(dom_y[["Year", dom_col, "_nm"]], on="Year", how="outer", suffixes=("", "_dom"))

    if df_y.empty:
        st.info("Data tidak cukup untuk membuat grafik tahunan (YTD).")
        return

    def _max3(a, b, c):
        vals = [v for v in [a, b, c] if pd.notna(v)]
        return int(max(vals)) if vals else 0

    df_y["_nm_out"] = df_y.get("_nm_out")
    df_y["_nm_dom"] = df_y.get("_nm_dom")
    df_y["_nm"] = df_y.apply(lambda r: _max3(r.get("_nm"), r.get("_nm_out"), r.get("_nm_dom")), axis=1)

    df_y["YearInt"] = pd.to_numeric(df_y.get("Year"), errors="coerce")
    df_y = df_y.dropna(subset=["YearInt"]).copy()
    df_y["YearInt"] = df_y["YearInt"].astype(int)

    df_y[inc_col] = pd.to_numeric(df_y.get(inc_col), errors="coerce").fillna(0.0)
    df_y[out_col] = pd.to_numeric(df_y.get(out_col), errors="coerce").fillna(0.0)
    df_y[dom_col] = pd.to_numeric(df_y.get(dom_col), errors="coerce").fillna(0.0)
    df_y = df_y.sort_values("YearInt")

    df_y["_limit"] = df_y["YearInt"].apply(_limit_for_year)
    df_y["_partial"] = df_y["_nm"].astype(int) < df_y["_limit"].astype(int)
    df_y["YearLabel"] = df_y["YearInt"].astype(int).astype(str) + df_y["_partial"].apply(lambda v: "*" if bool(v) else "")

    df_y["Total"] = df_y[inc_col] + df_y[out_col] + df_y[dom_col]
    df_y["YoY"] = df_y["Total"].pct_change() * 100

    prev_partial = df_y["_partial"].shift(1).fillna(False)
    df_y["_yoy_partial"] = (df_y["_partial"] | prev_partial).astype(bool)

    scale_factor = 1e9

    fs = int(font_size) if font_size is not None else 12
    x_tick_fs = int(axis_x_tick_font_size) if axis_x_tick_font_size is not None else max(fs - 1, 9)
    y_tick_fs = int(axis_y_tick_font_size) if axis_y_tick_font_size is not None else max(fs - 1, 9)
    axis_title_fs = fs + 2
    title_fs = fs + 10
    hover_fs = fs
    legend_fs = int(legend_font_size) if legend_font_size is not None else fs

    fig = go.Figure()

    x_years = df_y["YearInt"].astype(int).tolist()
    x_text = df_y["YearLabel"].astype(str).tolist()

    fig.add_trace(
        go.Bar(
            x=x_years,
            y=df_y[inc_col] / scale_factor,
            name="Incoming",
            marker=dict(color="#F5B0CB", line=dict(width=0)),
            hovertemplate="%{x}<br>Incoming: Rp %{y:,.2f} Miliar<extra></extra>",
            yaxis="y1",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_years,
            y=df_y[out_col] / scale_factor,
            name="Outgoing",
            marker=dict(color="#F5CBA7", line=dict(width=0)),
            hovertemplate="%{x}<br>Outgoing: Rp %{y:,.2f} Miliar<extra></extra>",
            yaxis="y1",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_years,
            y=df_y[dom_col] / scale_factor,
            name="Domestik",
            marker=dict(color="#5DADE2", line=dict(width=0)),
            hovertemplate="%{x}<br>Domestik: Rp %{y:,.2f} Miliar<extra></extra>",
            yaxis="y1",
        )
    )

    yoy_color = "#60A5FA"
    fig.add_trace(
        go.Scatter(
            x=x_years,
            y=df_y["YoY"],
            name="YoY",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color=yoy_color, width=4),
            marker=dict(size=10, color=yoy_color, line=dict(color="white", width=2)),
            hovertemplate="%{x}<br>YoY: %{y:.2f}%<extra></extra>",
        )
    )

    yoy_vals = pd.to_numeric(df_y["YoY"], errors="coerce")
    valid = yoy_vals.dropna().astype(float)
    if not valid.empty:
        vmin = float(valid.min())
        vmax = float(valid.max())
        span = vmax - vmin
        gap = max(5.0, span * 0.10)
        placed: list[float] = []

        def _place(y: float) -> float:
            pos = float(y)
            direction = 1.0
            tries = 0
            while any(abs(pos - p) < gap for p in placed) and tries < 12:
                pos += direction * gap
                direction *= -1
                tries += 1
            placed.append(pos)
            return pos

        for x, y, is_partial in zip(x_years, yoy_vals.tolist(), df_y["_yoy_partial"].tolist()):
            if y is None or (isinstance(y, float) and pd.isna(y)):
                continue
            y_float = float(y)
            y_used = _place(y_float)
            suffix = "*" if bool(is_partial) else ""
            fig.add_annotation(
                x=x,
                y=y_used,
                xref="x",
                yref="y2",
                text=f"{y_float:.2f}%{suffix}",
                showarrow=False,
                xanchor="center",
                yanchor="bottom",
                font=dict(size=max(9, fs), family="Inter, Arial, sans-serif", color="#111827"),
                bgcolor="rgba(245, 158, 11, 0.95)",
                bordercolor="rgba(245, 158, 11, 1.0)",
                borderwidth=0,
                borderpad=4,
            )

        all_y = placed + valid.tolist()
        ymin = float(min(all_y))
        ymax = float(max(all_y))
        pad = max(5.0, (ymax - ymin) * 0.15)
        y2_range = [ymin - pad, ymax + pad]
    else:
        y2_range = None

    month_label = f"Jan–{calendar.month_name[end_month_int][:3]}"
    full_label = "Jan–Dec" if default_end_month_int == 12 else f"Jan–{calendar.month_name[default_end_month_int][:3]}"
    mixed_suffix = (
        f" (hanya {', '.join(str(y) for y in sorted(cap_years_set))} pakai {month_label}; lainnya {full_label})"
        if cap_years_set is not None
        else ""
    )

    fig.update_layout(
        title=dict(
            text=f"Perkembangan Nilai Transaksi Tahunan{mixed_suffix} - Stacked & YoY (%)",
            font=dict(size=title_fs, family="Inter, Arial, sans-serif", color="#1f2937", weight=700),
        ),
        barmode="stack",
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="#f9fafb",
        font=dict(family="Inter, Arial, sans-serif", size=fs),
        xaxis=dict(
            title=dict(text="Tahun", font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            tickfont=dict(size=x_tick_fs, family="Inter, Arial, sans-serif"),
            type="linear",
            tickmode="array",
            tickvals=x_years,
            ticktext=x_text,
            range=[min(x_years) - 0.6, max(x_years) + 0.6] if x_years else None,
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor="#d1d5db",
        ),
        yaxis=dict(
            title=dict(text="Rp Miliar", font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            tickformat=",.0f",
            tickfont=dict(size=y_tick_fs, family="Inter, Arial, sans-serif"),
            showgrid=True,
            gridcolor="#e5e7eb",
        ),
        yaxis2=dict(
            title=dict(text="YoY (%)", font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            overlaying="y",
            side="right",
            tickformat=".0f",
            tickfont=dict(size=y_tick_fs, family="Inter, Arial, sans-serif"),
            showgrid=False,
            range=y2_range,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#e5e7eb",
            borderwidth=1,
            font=dict(size=legend_fs, family="Inter, Arial, sans-serif"),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=hover_fs, font_family="Inter, Arial, sans-serif"),
        margin=dict(l=60, r=80, t=80, b=80),
    )

    if chart_height is not None:
        fig.update_layout(height=int(chart_height))

    if chart_width is not None and int(chart_width) > 0:
        fig.update_layout(width=int(chart_width))
        st.plotly_chart(fig, use_container_width=False)
    else:
        st.plotly_chart(fig, use_container_width=True)


def make_quarter_across_years_chart(
    df: pd.DataFrame,
    quarter: int,
    sum_trx_type: str,
    trx_type: str,
    is_combined: bool = False,
    *,
    font_size: int | None = None,
    label_font_size: int | None = None,
    legend_font_size: int | None = None,
    chart_height: int | None = None,
):
    """Bandingkan kuartal yang sama (Q1/Q2/Q3/Q4) antar tahun.

    - Bar: nilai/frekuensi pada kuartal terpilih untuk setiap tahun
    - Line: Growth YoY (%) untuk kuartal yang sama

    Args:
        df: dataframe yang minimal punya kolom Year, Quarter, dan kolom nilai yang relevan.
        quarter: 1-4
        sum_trx_type: "Jumlah" atau "Nilai"
        trx_type: "Inc"|"Out"|"Dom"|"Total"
        is_combined: True untuk df total yang memakai kolom %YoY Jumlah/%YoY Nilai
    """

    if df is None or df.empty:
        st.info("Data kosong.")
        return

    required_cols = {"Year", "Quarter"}
    if not required_cols.issubset(set(df.columns)):
        st.warning("Kolom Year/Quarter tidak ditemukan.")
        return

    if sum_trx_type not in ("Jumlah", "Nilai"):
        st.warning("sum_trx_type harus 'Jumlah' atau 'Nilai'.")
        return

    if trx_type not in ("Inc", "Out", "Dom", "Total"):
        st.warning("trx_type harus salah satu dari Inc/Out/Dom/Total.")
        return

    bar_col = f"Sum of Fin {sum_trx_type} {trx_type}"
    if is_combined:
        growth_col = f"%YoY {sum_trx_type}"
    else:
        growth_col = "%YoY"

    if bar_col not in df.columns:
        st.warning(f"Kolom '{bar_col}' tidak ditemukan.")
        return

    if growth_col not in df.columns:
        st.warning(f"Kolom '{growth_col}' tidak ditemukan.")
        return

    dfc = df.copy()
    dfc = dfc[dfc["Quarter"].astype(int) == int(quarter)].copy()
    if dfc.empty:
        st.info(f"Tidak ada data untuk Q{int(quarter)} pada filter saat ini.")
        return

    dfc["Year"] = dfc["Year"].astype(int)
    dfc = dfc.sort_values("Year")

    # Scale mengikuti style chart lain
    if sum_trx_type == "Jumlah":
        bar_yaxis_title = "Volume (Jutaan)"
        scale_factor = 1e6
    else:
        bar_yaxis_title = "Nilai (Rp Miliar)"
        scale_factor = 1e9

    # Palet konsisten
    if trx_type == "Inc":
        jenis_trx = "INCOMING"
        bar_color = "#F5B0CB"
    elif trx_type == "Out":
        jenis_trx = "OUTGOING"
        bar_color = "#F5CBA7"
    elif trx_type == "Dom":
        jenis_trx = "DOMESTIK"
        bar_color = "#5DADE2"
    else:
        jenis_trx = "TOTAL"
        bar_color = "#6366f1"

    title = f"Perbandingan Q{int(quarter)} Antar Tahun - {bar_yaxis_title} {jenis_trx}"

    years = dfc["Year"].tolist()
    values = pd.to_numeric(dfc[bar_col], errors="coerce") / scale_factor
    yoy = pd.to_numeric(dfc[growth_col], errors="coerce")
    yoy_text = [f"{v:.1f}%" if pd.notna(v) else "" for v in yoy.tolist()]

    fs = int(font_size) if font_size is not None else 12
    tick_fs = max(fs - 1, 9)
    axis_title_fs = fs + 2
    title_fs = fs + 10
    hover_fs = fs
    label_fs = int(label_font_size) if label_font_size is not None else tick_fs
    legend_fs = int(legend_font_size) if legend_font_size is not None else fs

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=years,
            y=values,
            name=bar_yaxis_title,
            marker=dict(color=bar_color, line=dict(width=0)),
            hovertemplate="Year %{x}<br>" + bar_yaxis_title + ": %{y:,.2f}<extra></extra>",
            yaxis="y1",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=years,
            y=yoy,
            name="Growth YoY (%)",
            yaxis="y2",
            mode="lines+markers+text",
            line=dict(color="#1E8449", width=3),
            marker=dict(size=8, color="#1E8449", line=dict(color="white", width=2)),
            text=yoy_text,
            textposition="top center",
            textfont=dict(size=label_fs, color="#1E8449", family="Inter, Arial, sans-serif"),
            hovertemplate="Year %{x}<br>Growth YoY: %{y:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=title_fs, family="Inter, Arial, sans-serif", color="#1f2937", weight=700),
        ),
        xaxis=dict(
            title=dict(text=f"Tahun (Q{int(quarter)})", font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor="#d1d5db",
            tickfont=dict(size=tick_fs, family="Inter, Arial, sans-serif"),
        ),
        yaxis=dict(
            title=dict(text=bar_yaxis_title, font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            tickformat=",.0f",
            showgrid=True,
            gridwidth=1,
            gridcolor="#e5e7eb",
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor="#d1d5db",
            tickfont=dict(size=tick_fs, family="Inter, Arial, sans-serif")
        ),
        yaxis2=dict(
            title=dict(text="Growth (%)", font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            overlaying="y",
            side="right",
            tickformat=".1f",
            showgrid=False,
            tickfont=dict(size=tick_fs, family="Inter, Arial, sans-serif")
        ),
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="#f9fafb",
        font=dict(family="Inter, Arial, sans-serif", size=fs),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#e5e7eb",
            borderwidth=1,
            font=dict(size=legend_fs, family="Inter, Arial, sans-serif"),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=hover_fs, font_family="Inter, Arial, sans-serif"),
    )

    if chart_height is not None:
        fig.update_layout(height=int(chart_height))

    st.plotly_chart(fig, use_container_width=True)


def make_quarter_vs_quarter_chart(
    df: pd.DataFrame,
    year_a: int,
    quarter_a: int,
    year_b: int,
    quarter_b: int,
    sum_trx_type: str,
    trx_type: str,
    is_combined: bool = False,
    *,
    font_size: int | None = None,
    label_font_size: int | None = None,
    legend_font_size: int | None = None,
    axis_x_tick_font_size: int | None = None,
    axis_y_tick_font_size: int | None = None,
    chart_height: int | None = None,
    chart_width: int | None = None,
):
    """Bandingkan 2 periode kuartal (Year, Quarter) vs (Year, Quarter)."""

    if df is None or df.empty:
        st.info("Data kosong.")
        return

    required_cols = {"Year", "Quarter"}
    if not required_cols.issubset(set(df.columns)):
        st.warning("Kolom Year/Quarter tidak ditemukan.")
        return

    if sum_trx_type not in ("Jumlah", "Nilai"):
        st.warning("sum_trx_type harus 'Jumlah' atau 'Nilai'.")
        return

    if trx_type not in ("Inc", "Out", "Dom", "Total"):
        st.warning("trx_type harus salah satu dari Inc/Out/Dom/Total.")
        return

    bar_col = f"Sum of Fin {sum_trx_type} {trx_type}"
    if bar_col not in df.columns:
        st.warning(f"Kolom '{bar_col}' tidak ditemukan.")
        return

    dfa = df[(df["Year"].astype(int) == int(year_a)) & (df["Quarter"].astype(int) == int(quarter_a))].copy()
    dfb = df[(df["Year"].astype(int) == int(year_b)) & (df["Quarter"].astype(int) == int(quarter_b))].copy()

    if dfa.empty or dfb.empty:
        st.info("Data untuk salah satu periode tidak ditemukan.")
        return

    val_a = pd.to_numeric(dfa[bar_col].iloc[0], errors="coerce")
    val_b = pd.to_numeric(dfb[bar_col].iloc[0], errors="coerce")

    if sum_trx_type == "Jumlah":
        y_title = "Volume (Jutaan)"
        scale_factor = 1e6
    else:
        # Khusus chart VS: tampilkan dalam Triliun agar lebih mudah dibaca
        y_title = "Nilai (Rp Triliun)"
        scale_factor = 1e12

    # Palet konsisten
    if trx_type == "Inc":
        jenis_trx = "INCOMING"
        bar_color = "#F5B0CB"
    elif trx_type == "Out":
        jenis_trx = "OUTGOING"
        bar_color = "#F5CBA7"
    elif trx_type == "Dom":
        jenis_trx = "DOMESTIK"
        bar_color = "#5DADE2"
    else:
        jenis_trx = "TOTAL"
        bar_color = "#6366f1"

    label_a = f"Q{int(quarter_a)} {int(year_a)}"
    label_b = f"Q{int(quarter_b)} {int(year_b)}"

    y_vals = [val_a / scale_factor, val_b / scale_factor]

    fs = int(font_size) if font_size is not None else 12
    x_tick_fs = int(axis_x_tick_font_size) if axis_x_tick_font_size is not None else max(fs - 1, 9)
    y_tick_fs = int(axis_y_tick_font_size) if axis_y_tick_font_size is not None else max(fs - 1, 9)
    axis_title_fs = fs + 2
    title_fs = fs + 10
    hover_fs = fs
    label_fs = int(label_font_size) if label_font_size is not None else y_tick_fs
    legend_fs = int(legend_font_size) if legend_font_size is not None else fs

    delta_pct = None
    if pd.notna(val_a) and pd.notna(val_b) and float(val_a) != 0:
        delta_pct = ((float(val_b) - float(val_a)) / float(val_a)) * 100

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=[label_a, label_b],
            y=y_vals,
            name=jenis_trx,
            marker=dict(color=bar_color, line=dict(width=0)),
            hovertemplate="%{x}<br>" + y_title + ": %{y:,.2f}<extra></extra>",
        )
    )

    # Garis trend (dibuat sangat kontras + label % pakai badge putih)
    if pd.notna(y_vals[0]) and pd.notna(y_vals[1]):
        trend_color = "#111827"  # gray-900 (kontras, bukan ungu/biru)
        fig.add_trace(
            go.Scatter(
                x=[label_a, label_b],
                y=y_vals,
                name="Perubahan",
                mode="lines+markers",
                line=dict(color=trend_color, width=4),
                marker=dict(size=10, color=trend_color, line=dict(color="white", width=2)),
                hovertemplate="%{x}<br>" + y_title + ": %{y:,.2f}<extra></extra>",
            )
        )

        if delta_pct is not None and pd.notna(delta_pct):
            fig.add_annotation(
                x=label_b,
                y=y_vals[1],
                text=f"{delta_pct:+.1f}%",
                showarrow=False,
                yshift=18,
                bgcolor="rgba(255, 255, 255, 0.95)",
                bordercolor=trend_color,
                borderwidth=1,
                font=dict(size=label_fs, color="#111827", family="Inter, Arial, sans-serif"),
            )

    # (Delta sudah ditampilkan sebagai text pada garis)

    fig.update_layout(
        title=dict(
            text=f"Perbandingan Periode - {y_title} {jenis_trx}",
            font=dict(size=title_fs, family="Inter, Arial, sans-serif", color="#1f2937", weight=700),
        ),
        xaxis=dict(
            title=dict(text="Periode", font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor="#d1d5db",
            tickfont=dict(size=x_tick_fs, family="Inter, Arial, sans-serif"),
        ),
        yaxis=dict(
            title=dict(text=y_title, font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            tickformat=",.0f",
            showgrid=True,
            gridwidth=1,
            gridcolor="#e5e7eb",
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor="#d1d5db",
            tickfont=dict(size=y_tick_fs, family="Inter, Arial, sans-serif")
        ),
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="#f9fafb",
        font=dict(family="Inter, Arial, sans-serif", size=fs),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#e5e7eb",
            borderwidth=1,
            font=dict(size=legend_fs, family="Inter, Arial, sans-serif"),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=hover_fs, font_family="Inter, Arial, sans-serif"),
    )

    if chart_height is not None:
        fig.update_layout(height=int(chart_height))

    if chart_width is not None and int(chart_width) > 0:
        fig.update_layout(width=int(chart_width))
        st.plotly_chart(fig, use_container_width=False)
    else:
        st.plotly_chart(fig, use_container_width=True)


def make_quarter_vs_quarter_chart_total_breakdown(
    df_inc: pd.DataFrame,
    df_out: pd.DataFrame,
    df_dom: pd.DataFrame,
    year_a: int,
    quarter_a: int,
    year_b: int,
    quarter_b: int,
    sum_trx_type: str,
    *,
    font_size: int | None = None,
    label_font_size: int | None = None,
    legend_font_size: int | None = None,
    axis_x_tick_font_size: int | None = None,
    axis_y_tick_font_size: int | None = None,
    chart_height: int | None = None,
    chart_width: int | None = None,
):
    """VS chart khusus TOTAL: tampilkan stacked bar Inc/Out/Dom + garis perubahan untuk masing-masing + total."""

    if df_inc is None or df_out is None or df_dom is None:
        st.info("Data kosong.")
        return

    required_cols = {"Year", "Quarter"}
    if not (required_cols.issubset(set(df_inc.columns)) and required_cols.issubset(set(df_out.columns)) and required_cols.issubset(set(df_dom.columns))):
        st.warning("Kolom Year/Quarter tidak lengkap untuk membuat grafik.")
        return

    if sum_trx_type not in ("Jumlah", "Nilai"):
        st.warning("sum_trx_type harus 'Jumlah' atau 'Nilai'.")
        return

    col_inc = f"Sum of Fin {sum_trx_type} Inc"
    col_out = f"Sum of Fin {sum_trx_type} Out"
    col_dom = f"Sum of Fin {sum_trx_type} Dom"

    for c, name in [(col_inc, "Inc"), (col_out, "Out"), (col_dom, "Dom")]:
        if c not in df_inc.columns and name == "Inc":
            st.warning(f"Kolom '{c}' tidak ditemukan.")
            return
        if c not in df_out.columns and name == "Out":
            st.warning(f"Kolom '{c}' tidak ditemukan.")
            return
        if c not in df_dom.columns and name == "Dom":
            st.warning(f"Kolom '{c}' tidak ditemukan.")
            return

    def _get_val(df_src: pd.DataFrame, col: str, y: int, q: int):
        dfx = df_src[(df_src["Year"].astype(int) == int(y)) & (df_src["Quarter"].astype(int) == int(q))]
        if dfx.empty:
            return None
        return pd.to_numeric(dfx[col].iloc[0], errors="coerce")

    inc_a = _get_val(df_inc, col_inc, year_a, quarter_a)
    out_a = _get_val(df_out, col_out, year_a, quarter_a)
    dom_a = _get_val(df_dom, col_dom, year_a, quarter_a)

    inc_b = _get_val(df_inc, col_inc, year_b, quarter_b)
    out_b = _get_val(df_out, col_out, year_b, quarter_b)
    dom_b = _get_val(df_dom, col_dom, year_b, quarter_b)

    if any(v is None for v in [inc_a, out_a, dom_a, inc_b, out_b, dom_b]):
        st.info("Data untuk salah satu periode tidak ditemukan (A/B).")
        return

    total_a = (inc_a or 0) + (out_a or 0) + (dom_a or 0)
    total_b = (inc_b or 0) + (out_b or 0) + (dom_b or 0)

    def _delta_pct(a, b):
        if a is None or b is None:
            return None
        try:
            a = float(a)
            b = float(b)
        except Exception:
            return None
        if a == 0:
            return None
        return ((b - a) / a) * 100

    d_inc = _delta_pct(inc_a, inc_b)
    d_out = _delta_pct(out_a, out_b)
    d_dom = _delta_pct(dom_a, dom_b)
    d_tot = _delta_pct(total_a, total_b)

    if sum_trx_type == "Jumlah":
        y_title = "Volume (Jutaan)"
        scale_factor = 1e6
    else:
        y_title = "Nilai (Rp Triliun)"
        scale_factor = 1e12

    label_a = f"Q{int(quarter_a)} {int(year_a)}"
    label_b = f"Q{int(quarter_b)} {int(year_b)}"
    x = [label_a, label_b]

    y_inc = [inc_a / scale_factor, inc_b / scale_factor]
    y_out = [out_a / scale_factor, out_b / scale_factor]
    y_dom = [dom_a / scale_factor, dom_b / scale_factor]
    y_tot = [total_a / scale_factor, total_b / scale_factor]

    fs = int(font_size) if font_size is not None else 12
    x_tick_fs = int(axis_x_tick_font_size) if axis_x_tick_font_size is not None else max(fs - 1, 9)
    y_tick_fs = int(axis_y_tick_font_size) if axis_y_tick_font_size is not None else max(fs - 1, 9)
    axis_title_fs = fs + 2
    title_fs = fs + 10
    hover_fs = fs
    label_fs = int(label_font_size) if label_font_size is not None else y_tick_fs
    legend_fs = int(legend_font_size) if legend_font_size is not None else fs

    fig = go.Figure()

    # Stacked bars seperti Grafik Gabungan
    fig.add_trace(go.Bar(
        x=x,
        y=y_inc,
        name="Incoming",
        marker=dict(color="#F5B0CB", line=dict(width=0)),
        hovertemplate="%{x}<br>Incoming: %{y:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=x,
        y=y_out,
        name="Outgoing",
        marker=dict(color="#F5CBA7", line=dict(width=0)),
        hovertemplate="%{x}<br>Outgoing: %{y:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=x,
        y=y_dom,
        name="Domestik",
        marker=dict(color="#5DADE2", line=dict(width=0)),
        hovertemplate="%{x}<br>Domestik: %{y:,.2f}<extra></extra>",
    ))

    # Garis perubahan untuk masing-masing + total
    # Pakai warna garis yang lebih gelap (lebih kontras) + badge label % (bg putih) supaya tidak "nyaru".
    line_colors = {
        # Hindari merah/orange/biru/ungu: pakai netral + hijau/teal yang kontras
        "Incoming": "#374151",  # gray-700
        "Outgoing": "#065F46",  # emerald-800
        "Domestik": "#0F766E",  # teal-700
        "Total": "#111827",     # gray-900
    }

    def _line(series: str, y_vals, delta, yshift: int):
        color = line_colors[series]
        fig.add_trace(go.Scatter(
            x=x,
            y=y_vals,
            name=f"Δ {series}",
            mode="lines+markers",
            line=dict(color=color, width=4),
            marker=dict(size=10, color=color, line=dict(color="white", width=2)),
            hovertemplate="%{x}<br>" + series + ": %{y:,.2f}<extra></extra>",
        ))

        if delta is not None:
            fig.add_annotation(
                x=label_b,
                y=y_vals[1],
                text=f"{delta:+.1f}%",
                showarrow=False,
                yshift=yshift,
                bgcolor="rgba(255, 255, 255, 0.95)",
                bordercolor=color,
                borderwidth=1,
                font=dict(size=label_fs, color="#111827", family="Inter, Arial, sans-serif"),
            )

    _line("Incoming", y_inc, d_inc, 18)
    _line("Outgoing", y_out, d_out, 0)
    _line("Domestik", y_dom, d_dom, -18)
    _line("Total", y_tot, d_tot, 30)

    fig.update_layout(
        title=dict(
            text=f"Perbandingan Periode - {y_title} TOTAL (Breakdown Inc/Out/Dom)",
            font=dict(size=title_fs, family="Inter, Arial, sans-serif", color="#1f2937", weight=700),
        ),
        barmode="stack",
        xaxis=dict(
            title=dict(text="Periode", font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor="#d1d5db",
            tickfont=dict(size=x_tick_fs, family="Inter, Arial, sans-serif"),
        ),
        yaxis=dict(
            title=dict(text=y_title, font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            tickformat=",.0f",
            showgrid=True,
            gridwidth=1,
            gridcolor="#e5e7eb",
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor="#d1d5db",
            tickfont=dict(size=y_tick_fs, family="Inter, Arial, sans-serif")
        ),
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="#f9fafb",
        font=dict(family="Inter, Arial, sans-serif", size=fs),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#e5e7eb",
            borderwidth=1,
            font=dict(size=legend_fs, family="Inter, Arial, sans-serif"),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=hover_fs, font_family="Inter, Arial, sans-serif"),
    )

    if chart_height is not None:
        fig.update_layout(height=int(chart_height))

    if chart_width is not None and int(chart_width) > 0:
        fig.update_layout(width=int(chart_width))
        st.plotly_chart(fig, use_container_width=False)
    else:
        st.plotly_chart(fig, use_container_width=True)


def make_pie_chart_summary(df, top_n):
    df_sorted = df.sort_values('Market Share (%)', ascending=False)

    df_top_n = df_sorted.head(top_n)

    other_share = df_sorted['Market Share (%)'].sum() - df_top_n['Market Share (%)'].sum()

    df_other = pd.DataFrame([{'Nama PJP': 'Other', 'Market Share (%)': other_share}])
    df_combined = pd.concat([df_top_n, df_other], ignore_index=True)

    fig = px.pie(df_combined,
                 values='Market Share (%)',
                 names='Nama PJP',
                 title=f'Top {top_n} PJPs by Market Share (Including Others)',
                 template='plotly_white')

    fig.update_traces(
        hovertemplate='%{label}: %{value:.2f}%',
        textfont=dict(color='#111827', size=14, family='Inter, Arial, sans-serif', weight='bold'),
        textposition='inside',
        marker=dict(line=dict(color='white', width=3))
    )
    
    fig.update_layout(
        title_font=dict(size=20, family='Inter, Arial, sans-serif', color='#1f2937'),
        font=dict(family='Inter, Arial, sans-serif'),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )

    st.plotly_chart(fig, use_container_width=True)


def make_pie_chart_market_share(df: pd.DataFrame, trx_type: str, key: str ,is_nom: bool = True):
    if is_nom:
        data = {
            "Market Share": ["Jakarta", "National"],
            "Percentage": [df['Nominal (dalam triliun)'].values[2], 100 - df['Nominal (dalam triliun)'].values[2]]
        }
        text = "Nominal"
    else:
        data = {
            "Market Share": ["Jakarta", "National"],
            "Percentage": [df['Frekuensi (dalam jutaan)'].values[2], 100 - df['Frekuensi (dalam jutaan)'].values[2]]
        }
        text = "Frekuensi"

    df_combined = pd.DataFrame(data)
    
    # Konsisten warna: Orange untuk Jakarta (lebih gelap), Biru untuk National (lebih gelap)
    color_map = {
        'Jakarta': '#E8964F',  # Orange yang lebih gelap dan saturated
        'National': '#2E7D9E'  # Blue yang lebih gelap
    }

    fig = px.pie(df_combined,
                 names='Market Share',
                 values='Percentage',
                 title=f'Market Share {text} {trx_type} Jakarta VS National',
                 template='plotly_white',
                 color='Market Share',
                 color_discrete_map=color_map)

    fig.update_traces(
        hovertemplate='%{label}: %{value:.2f}%',
        textfont=dict(color='white', size=14, family='Inter, Arial, sans-serif', weight='bold'),
        textposition='inside',
        marker=dict(line=dict(color='white', width=3))
    )
    
    fig.update_layout(
        title_font=dict(size=20, family='Inter, Arial, sans-serif', color='#1f2937'),
        font=dict(family='Inter, Arial, sans-serif'),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )

    st.plotly_chart(fig, use_container_width=True, key=key)


def make_grouped_bar_chart(df, mode, is_month):
    time_label = 'Quarter'
    if is_month:
        time_label = 'Month'

    value_vars = (['Sum of Fin Jumlah Inc', 'Sum of Fin Jumlah Out', 'Sum of Fin Jumlah Dom']
                  if mode == "Jumlah"
                  else ['Sum of Fin Nilai Inc', 'Sum of Fin Nilai Out', 'Sum of Fin Nilai Dom'])

    df_melted = df.melt(id_vars=[time_label],
                        value_vars=value_vars,
                        var_name='Financial Metric', value_name='Value')

    df_grouped = df_melted.groupby([time_label, 'Financial Metric'], as_index=False, observed=False).sum()

    df_filtered = df_grouped.groupby(time_label, observed=False).filter(lambda x: x['Value'].sum() != 0)

    if mode == "Jumlah":
        label = "Frequency"
    else:
        label = "Nominal"

    # Warna konsisten dengan Chart.js HTML
    color_map = {
        'Sum of Fin Nilai Inc': '#F5B0CB',  # Pink untuk Incoming
        'Sum of Fin Nilai Out': '#F5CBA7',  # Peach/Orange untuk Outgoing
        'Sum of Fin Nilai Dom': '#5DADE2',  # Blue untuk Domestik
        'Sum of Fin Jumlah Inc': '#F5B0CB',
        'Sum of Fin Jumlah Out': '#F5CBA7',
        'Sum of Fin Jumlah Dom': '#5DADE2'
    }

    fig = px.bar(df_filtered,
                 x=time_label,
                 y='Value',
                 color='Financial Metric',
                 barmode='group',
                 title=f'{label} Income, Outcome, and Domestic Transactions by {time_label}',
                 labels={'Value': label, time_label: time_label},
                 template='plotly_white',
                 color_discrete_map=color_map)
    
    fig.update_layout(
        title_font=dict(size=20, family='Inter, Arial, sans-serif', color='#1f2937'),
        font=dict(family='Inter, Arial, sans-serif', size=12),
        paper_bgcolor='white',
        plot_bgcolor='#f9fafb',
        xaxis=dict(
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor='#e5e7eb'
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='#e5e7eb'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )

    st.plotly_chart(fig, use_container_width=True)


def make_combined_bar_line_chart(
    df,
    sum_trx_type: str,
    trx_type: str,
    is_month: bool = False,
    is_combined: bool = False,
    *,
    font_size: int | None = None,
    legend_font_size: int | None = None,
    axis_x_tick_font_size: int | None = None,
    axis_y_tick_font_size: int | None = None,
    chart_height: int | None = None,
    chart_width: int | None = None,
):
    df_copy = df.copy()

    if is_combined:
        if is_month:
            df_copy = df_copy[df_copy[f'%MtM {sum_trx_type}'].notnull()]
            df_copy['Year-Month'] = df_copy['Year'].astype(str) + '-' + df_copy['Month'].astype(str)
            target_col = 'Year-Month'
        else:
            df_copy = df_copy[(df_copy[f'%YoY {sum_trx_type}'].notnull()) & (df_copy[f'%QtQ {sum_trx_type}'].notnull())]
            df_copy['Year-Quarter'] = df_copy['Year'].astype(str) + ' Q' + df_copy['Quarter'].astype(str)
            target_col = 'Year-Quarter'
    else:
        if is_month:
            df_copy = df_copy[df_copy['%MtM'].notnull()]
            df_copy['Year-Month'] = df_copy['Year'].astype(str) + '-' + df_copy['Month'].astype(str)
            target_col = 'Year-Month'
        else:
            df_copy = df_copy[(df_copy['%YoY'].notnull()) & (df_copy['%QtQ'].notnull())]
            df_copy['Year-Quarter'] = df_copy['Year'].astype(str) + ' Q' + df_copy['Quarter'].astype(str)
            target_col = 'Year-Quarter'

    if sum_trx_type == "Jumlah":
        variabel_trx = "Frekuensi"
    else:
        variabel_trx = "Nominal"

    if trx_type == "Out":
        jenis_trx = "Outgoing"
        bar_color = '#F5CBA7'  # Peach/Orange
    elif trx_type == "Inc":
        jenis_trx = "Incoming"
        bar_color = '#F5B0CB'  # Pink
    elif trx_type == "Dom":
        jenis_trx = "Domestik"
        bar_color = '#5DADE2'  # Blue
    else:  # trx_type == "Total"
        jenis_trx = "Keseluruhan (Incoming, Outgoing, Domestik)"
        bar_color = '#6366f1'  # Indigo untuk Total

    bar_col = f'Sum of Fin {sum_trx_type} {trx_type}'
    bar_title = f"Perkembangan {variabel_trx} Transaksi {jenis_trx}"

    if sum_trx_type == "Jumlah":
        bar_yaxis_title = "Volume (Jutaan)"
        scale_factor = 1e6
    else:
        bar_yaxis_title = "Nilai (Rp Miliar)"
        scale_factor = 1e9  # Ubah ke Miliar sesuai Chart.js

    fs = int(font_size) if font_size is not None else 12
    x_tick_fs = int(axis_x_tick_font_size) if axis_x_tick_font_size is not None else max(fs - 1, 9)
    y_tick_fs = int(axis_y_tick_font_size) if axis_y_tick_font_size is not None else max(fs - 1, 9)
    axis_title_fs = fs + 2
    title_fs = fs + 10
    hover_fs = fs
    legend_fs = int(legend_font_size) if legend_font_size is not None else fs

    fig = go.Figure()

    # Bar trace dengan warna sesuai jenis transaksi
    fig.add_trace(go.Bar(
        x=df_copy[target_col],
        y=df_copy[bar_col] / scale_factor,
        name=bar_yaxis_title,
        yaxis='y1',
        marker=dict(
            color=bar_color,
            line=dict(width=0)
        ),
        hovertemplate='%{x}<br>' + bar_yaxis_title + ': %{y:,.2f}<extra></extra>'
    ))

    # Line traces untuk Growth dengan warna hijau gelap (#1E8449)
    if is_combined:
        if is_month:
            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy[f'%MtM {sum_trx_type}'],
                name='Growth MtM (%)',
                yaxis='y2',
                mode='lines+markers',
                line=dict(color='#1E8449', width=3),
                marker=dict(size=8, color='#1E8449', line=dict(color='white', width=2)),
                hovertemplate='%{x}<br>MtM Growth: %{y:.2f}%<extra></extra>'
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy[f'%YoY {sum_trx_type}'],
                name='Growth YoY (%)',
                yaxis='y2',
                mode='lines+markers',
                line=dict(color='#1E8449', width=3),
                marker=dict(size=8, color='#1E8449', line=dict(color='white', width=2)),
                hovertemplate='%{x}<br>YoY Growth: %{y:.2f}%<extra></extra>'
            ))

            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy[f'%QtQ {sum_trx_type}'],
                name='Growth QtQ (%)',
                yaxis='y2',
                mode='lines+markers',
                line=dict(color='#16a34a', width=3, dash='dot'),
                marker=dict(size=8, color='#16a34a', line=dict(color='white', width=2)),
                hovertemplate='%{x}<br>QtQ Growth: %{y:.2f}%<extra></extra>'
            ))
    else:
        if is_month:
            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy['%MtM'],
                name='Growth MtM (%)',
                yaxis='y2',
                mode='lines+markers',
                line=dict(color='#1E8449', width=3),
                marker=dict(size=8, color='#1E8449', line=dict(color='white', width=2)),
                hovertemplate='%{x}<br>MtM Growth: %{y:.2f}%<extra></extra>'
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy['%YoY'],
                name='Growth YoY (%)',
                yaxis='y2',
                mode='lines+markers',
                line=dict(color='#1E8449', width=3),
                marker=dict(size=8, color='#1E8449', line=dict(color='white', width=2)),
                hovertemplate='%{x}<br>YoY Growth: %{y:.2f}%<extra></extra>'
            ))

            fig.add_trace(go.Scatter(
                x=df_copy[target_col],
                y=df_copy['%QtQ'],
                name='Growth QtQ (%)',
                yaxis='y2',
                mode='lines+markers',
                line=dict(color='#16a34a', width=3, dash='dot'),
                marker=dict(size=8, color='#16a34a', line=dict(color='white', width=2)),
                hovertemplate='%{x}<br>QtQ Growth: %{y:.2f}%<extra></extra>'
            ))

    fig.update_layout(
        title=dict(
            text=bar_title,
            font=dict(size=title_fs, family='Inter, Arial, sans-serif', color='#1f2937', weight=700)
        ),
        xaxis=dict(
            title=dict(text="Periode", font=dict(size=axis_title_fs, family='Inter, Arial, sans-serif')),
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor='#d1d5db',
            tickangle=-45,
            tickfont=dict(size=x_tick_fs, family='Inter, Arial, sans-serif')
        ),
        yaxis=dict(
            title=dict(text=bar_yaxis_title, font=dict(size=axis_title_fs, family='Inter, Arial, sans-serif')),
            tickformat=",.0f",
            showgrid=True,
            gridwidth=1,
            gridcolor='#e5e7eb',
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='#d1d5db',
            tickfont=dict(size=y_tick_fs, family='Inter, Arial, sans-serif')
        ),
        yaxis2=dict(
            title=dict(text='Growth (%)', font=dict(size=axis_title_fs, family='Inter, Arial, sans-serif')),
            overlaying='y',
            side='right',
            tickformat=".1f",
            showgrid=False,
            tickfont=dict(size=y_tick_fs, family='Inter, Arial, sans-serif')
        ),
        template="plotly_white",
        paper_bgcolor='white',
        plot_bgcolor='#f9fafb',
        font=dict(family='Inter, Arial, sans-serif', size=fs),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='#e5e7eb',
            borderwidth=1,
            font=dict(size=legend_fs, family='Inter, Arial, sans-serif')
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=hover_fs,
            font_family="Inter, Arial, sans-serif"
        )
    )

    if chart_height is not None:
        fig.update_layout(height=int(chart_height))

    if chart_width is not None and int(chart_width) > 0:
        fig.update_layout(width=int(chart_width))
        st.plotly_chart(fig, use_container_width=False)
    else:
        st.plotly_chart(fig, use_container_width=True)


def make_overall_total_stacked_growth_chart(
    df_total: pd.DataFrame,
    df_inc: pd.DataFrame,
    df_out: pd.DataFrame,
    df_dom: pd.DataFrame,
    sum_trx_type: str,
    is_month: bool = False,
    show_breakdown_growth: bool = False,
    visible_periods: list[str] | None = None,
    *,
    font_size: int | None = None,
    label_font_size: int | None = None,
    legend_font_size: int | None = None,
    axis_x_tick_font_size: int | None = None,
    axis_y_tick_font_size: int | None = None,
    chart_height: int | None = None,
    chart_width: int | None = None,
):
    """Visualisasi Keseluruhan TOTAL: stacked bar (Inc/Out/Dom) + Growth YoY & QtQ.

    Disamakan gaya grafiknya dengan chart TOTAL di Perbandingan Periode (stacked breakdown),
    tapi tetap mempertahankan garis Growth YoY dan Growth QtQ.
    """

    if df_total is None or df_total.empty:
        st.info("Data kosong.")
        return

    if sum_trx_type not in ("Jumlah", "Nilai"):
        st.warning("sum_trx_type harus 'Jumlah' atau 'Nilai'.")
        return

    # Styling knobs (ubah di sini untuk atur ketebalan garis, marker, dan label %)
    TOTAL_GROWTH_LINE_WIDTH = 5
    BREAKDOWN_GROWTH_LINE_WIDTH = 6
    TOTAL_GROWTH_MARKER_SIZE = 10
    BREAKDOWN_GROWTH_MARKER_SIZE = 8
    LABEL_BORDER_WIDTH = 2
    fs = int(font_size) if font_size is not None else 12
    x_tick_fs = int(axis_x_tick_font_size) if axis_x_tick_font_size is not None else max(fs - 1, 9)
    y_tick_fs = int(axis_y_tick_font_size) if axis_y_tick_font_size is not None else max(fs - 1, 9)
    axis_title_fs = fs + 2
    title_fs = fs + 10
    hover_fs = fs
    legend_fs = int(legend_font_size) if legend_font_size is not None else fs

    LABEL_FONT_SIZE = int(label_font_size) if label_font_size is not None else 12
    # Offset dibuat kecil agar label % tetap “mepet” dengan titiknya (bukan naik/serong jauh)
    LABEL_OFFSET_TOTAL = 0.18
    LABEL_OFFSET_BREAKDOWN_STEP = 0.12

    # Layout padding knobs
    # - Right margin: ruang untuk label % di sisi kanan
    # - Top margin: ruang untuk title (responsif terhadap font)
    # - Bottom margin: ruang untuk legend (legend dipindah ke bawah agar tidak bisa nabrak title)
    TOP_MARGIN_PX = max(95, int(title_fs * 4.5))
    RIGHT_MARGIN_PX = 110

    # Tentukan kolom periode
    if is_month:
        required = {"Year", "Month"}
        if not required.issubset(set(df_total.columns)):
            st.warning("Kolom Year/Month tidak ditemukan.")
            return
        target_col = "Year-Month"
        df_plot = df_total.copy()
        df_plot[target_col] = df_plot["Year"].astype(str) + "-" + df_plot["Month"].astype(str)
        df_plot = df_plot.sort_values(["Year", "Month"])
        growth_yoy_col = f"%YoY {sum_trx_type}" if f"%YoY {sum_trx_type}" in df_plot.columns else "%YoY"
        growth_qoq_col = f"%MtM {sum_trx_type}" if f"%MtM {sum_trx_type}" in df_plot.columns else "%MtM"
        yoy_label = "Growth YoY (%)"
        qoq_label = "Growth MtM (%)"
        period_label = "Bulan"
    else:
        required = {"Year", "Quarter"}
        if not required.issubset(set(df_total.columns)):
            st.warning("Kolom Year/Quarter tidak ditemukan.")
            return
        target_col = "Year-Quarter"
        df_plot = df_total.copy()
        df_plot[target_col] = df_plot["Year"].astype(str) + " Q" + df_plot["Quarter"].astype(str)
        df_plot = df_plot.sort_values(["Year", "Quarter"])
        growth_yoy_col = f"%YoY {sum_trx_type}" if f"%YoY {sum_trx_type}" in df_plot.columns else "%YoY"
        growth_qoq_col = f"%QtQ {sum_trx_type}" if f"%QtQ {sum_trx_type}" in df_plot.columns else "%QtQ"
        yoy_label = "Growth YoY (%)"
        qoq_label = "Growth QtQ (%)"
        period_label = "Kuartal"

    if growth_yoy_col not in df_plot.columns or growth_qoq_col not in df_plot.columns:
        st.warning("Kolom growth (YoY/QtQ) tidak ditemukan untuk Total.")
        return

    # Filter agar garis growth tidak putus-putus
    df_plot = df_plot[df_plot[growth_yoy_col].notnull() & df_plot[growth_qoq_col].notnull()].copy()
    if df_plot.empty:
        st.info("Data growth (YoY/QtQ) tidak tersedia pada rentang periode ini.")
        return

    # Kolom nilai untuk bar
    inc_col = f"Sum of Fin {sum_trx_type} Inc"
    out_col = f"Sum of Fin {sum_trx_type} Out"
    dom_col = f"Sum of Fin {sum_trx_type} Dom"

    for src, col_name in [(df_inc, inc_col), (df_out, out_col), (df_dom, dom_col)]:
        if src is None or src.empty or col_name not in src.columns:
            st.warning(f"Kolom '{col_name}' tidak ditemukan untuk stacked breakdown.")
            return

    # Build lookup per periode agar align dengan df_plot
    if is_month:
        key_cols = ["Year", "Month"]
        def _key(df_):
            return df_["Year"].astype(int).astype(str) + "-" + df_["Month"].astype(str)
    else:
        key_cols = ["Year", "Quarter"]
        def _key(df_):
            return df_["Year"].astype(int).astype(str) + " Q" + df_["Quarter"].astype(int).astype(str)

    df_inc_map = df_inc.copy()
    df_out_map = df_out.copy()
    df_dom_map = df_dom.copy()
    df_inc_map[target_col] = _key(df_inc_map)
    df_out_map[target_col] = _key(df_out_map)
    df_dom_map[target_col] = _key(df_dom_map)

    # Optional: ambil growth YoY/QtQ per jenis transaksi (Inc/Out/Dom)
    if show_breakdown_growth and (not is_month):
        for src_df, label in [(df_inc_map, "Incoming"), (df_out_map, "Outgoing"), (df_dom_map, "Domestik")]:
            if "%YoY" not in src_df.columns or "%QtQ" not in src_df.columns:
                st.warning(f"Kolom growth (%YoY/%QtQ) tidak ditemukan untuk {label}.")
                show_breakdown_growth = False
                break

    # Rename kolom growth agar tidak bentrok saat merge
    if show_breakdown_growth and (not is_month):
        df_inc_map = df_inc_map.rename(columns={"%YoY": "_inc_yoy", "%QtQ": "_inc_qoq"})
        df_out_map = df_out_map.rename(columns={"%YoY": "_out_yoy", "%QtQ": "_out_qoq"})
        df_dom_map = df_dom_map.rename(columns={"%YoY": "_dom_yoy", "%QtQ": "_dom_qoq"})

    inc_merge_cols = [target_col, inc_col] + (["_inc_yoy", "_inc_qoq"] if show_breakdown_growth and (not is_month) else [])
    out_merge_cols = [target_col, out_col] + (["_out_yoy", "_out_qoq"] if show_breakdown_growth and (not is_month) else [])
    dom_merge_cols = [target_col, dom_col] + (["_dom_yoy", "_dom_qoq"] if show_breakdown_growth and (not is_month) else [])

    df_plot = df_plot.merge(df_inc_map[inc_merge_cols], on=target_col, how="left")
    df_plot = df_plot.merge(df_out_map[out_merge_cols], on=target_col, how="left")
    df_plot = df_plot.merge(df_dom_map[dom_merge_cols], on=target_col, how="left")

    if df_plot[[inc_col, out_col, dom_col]].isna().all(axis=None):
        st.info("Data breakdown Inc/Out/Dom tidak tersedia.")
        return

    # Visual-only filter: sembunyikan periode tertentu tanpa mengubah nilai growth
    df_show = df_plot
    if visible_periods is not None:
        visible = [p for p in visible_periods if isinstance(p, str) and p.strip()]
        if len(visible) == 0:
            st.info("Tidak ada periode yang dipilih untuk ditampilkan.")
            return
        df_show = df_plot[df_plot[target_col].isin(visible)].copy()
        if df_show.empty:
            st.info("Tidak ada data pada periode yang dipilih.")
            return

    # Skala sumbu utama
    if sum_trx_type == "Jumlah":
        y_title = "Volume (Jutaan)"
        scale_factor = 1e6
    else:
        # Disamakan dengan chart VS: tampilkan Triliun
        y_title = "Nilai (Rp Triliun)"
        scale_factor = 1e12

    fig = go.Figure()

    def _lighten_hex(hex_color: str, amount: float = 0.35) -> str:
        """Lighten hex color by mixing with white (amount 0..1)."""
        try:
            h = hex_color.lstrip("#")
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            r = int(r + (255 - r) * amount)
            g = int(g + (255 - g) * amount)
            b = int(b + (255 - b) * amount)
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return hex_color

    def _calc_y2_offset_unit() -> float:
        series_list: list[pd.Series] = []
        try:
            series_list.extend([yoy, qoq])
        except Exception:
            pass

        if show_breakdown_growth and (not is_month):
            for col in ("_inc_yoy", "_inc_qoq", "_out_yoy", "_out_qoq", "_dom_yoy", "_dom_qoq"):
                if col in df_show.columns:
                    series_list.append(pd.to_numeric(df_show[col], errors="coerce"))

        vals = []
        for s in series_list:
            try:
                vals.extend(pd.to_numeric(s, errors="coerce").dropna().tolist())
            except Exception:
                continue

        if not vals:
            return 1.0

        vmin = float(min(vals))
        vmax = float(max(vals))
        span = vmax - vmin
        # Lebih kecil dari sebelumnya supaya label tidak “lari” jauh dari titik
        return span * 0.015 if span > 0 else 1.0

    label_y_values: list[float] = []
    min_label_gap = 1  # will be recalculated after y2_offset_unit is known

    def _add_last_point_label_trace(
        *,
        x_val: str,
        y_val: float,
        text: str,
        legend_group: str,
        border_color: str,
        y_offset: float = 0.0,
    ):
        """Tambahkan label di titik terakhir sebagai trace agar ikut hide saat legend-toggle."""

        try:
            y_num = float(y_val)
        except Exception:
            return

        # Sesuaikan ukuran kotak dengan panjang teks agar tulisan tidak "keluar" dari box
        safe_text = str(text)

        # Cari slot y yang tidak terlalu dekat dengan label lain (auto spacing)
        def _find_non_overlap_y(target_y: float) -> float:
            step = max(float(min_label_gap), 0.1)
            pos = float(target_y)
            direction = 1.0
            tries = 0
            while any(abs(pos - existing) < step for existing in label_y_values) and tries < 14:
                pos += direction * step
                direction *= -1
                tries += 1
            return pos

        placed_y = _find_non_overlap_y(y_num + float(y_offset))
        label_y_values.append(float(placed_y))
        fig.add_trace(
            go.Scatter(
                x=[x_val],
                y=[placed_y],
                name=text,
                legendgroup=legend_group,
                showlegend=False,
                yaxis="y2",
                mode="text",
                # Jangan keluar area plot supaya tidak “nabrak” komponen lain (mis. tabel)
                cliponaxis=True,
                text=[f"<b>{safe_text}</b>"],
                textposition="middle right",
                textfont=dict(
                    size=LABEL_FONT_SIZE,
                    color=border_color,
                    family="Inter, Arial, sans-serif",
                    # Tipiskan pemisah visual via text shadow (Plotly tidak punya border untuk textfont)
                    shadow="0px 0px 1px #ffffff",
                ),
                hoverinfo="skip",
            )
        )

    # Stacked bars (tetap pakai warna pastel untuk breakdown)
    fig.add_trace(go.Bar(
        x=df_show[target_col],
        y=pd.to_numeric(df_show[inc_col], errors="coerce") / scale_factor,
        name="Incoming",
        marker=dict(color="#F5B0CB", line=dict(width=0)),
        hovertemplate="%{x}<br>Incoming: %{y:,.2f}<extra></extra>",
        yaxis="y1",
    ))
    fig.add_trace(go.Bar(
        x=df_show[target_col],
        y=pd.to_numeric(df_show[out_col], errors="coerce") / scale_factor,
        name="Outgoing",
        marker=dict(color="#F5CBA7", line=dict(width=0)),
        hovertemplate="%{x}<br>Outgoing: %{y:,.2f}<extra></extra>",
        yaxis="y1",
    ))
    fig.add_trace(go.Bar(
        x=df_show[target_col],
        y=pd.to_numeric(df_show[dom_col], errors="coerce") / scale_factor,
        name="Domestik",
        marker=dict(color="#5DADE2", line=dict(width=0)),
        hovertemplate="%{x}<br>Domestik: %{y:,.2f}<extra></extra>",
        yaxis="y1",
    ))

    yoy = pd.to_numeric(df_show[growth_yoy_col], errors="coerce")
    qoq = pd.to_numeric(df_show[growth_qoq_col], errors="coerce")

    # Garis growth dibuat gelap tapi kontras (hindari hitam tua & biru tua)
    yoy_color = "#14532D"  # green-900
    qoq_color = "#7F1D1D"  # red-900
    total_yoy_group = "overall_total_yoy"
    total_qoq_group = "overall_total_qoq"

    fig.add_trace(go.Scatter(
        x=df_show[target_col],
        y=yoy,
        name=yoy_label,
        legendgroup=total_yoy_group,
        yaxis="y2",
        mode="lines+markers",
        line=dict(color=yoy_color, width=TOTAL_GROWTH_LINE_WIDTH),
        marker=dict(size=TOTAL_GROWTH_MARKER_SIZE, color=yoy_color, line=dict(color="white", width=2), symbol="circle"),
        hovertemplate="%{x}<br>YoY Growth: %{y:.2f}%<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=df_show[target_col],
        y=qoq,
        name=qoq_label,
        legendgroup=total_qoq_group,
        yaxis="y2",
        mode="lines+markers",
        line=dict(color=qoq_color, width=TOTAL_GROWTH_LINE_WIDTH, dash="dash"),
        marker=dict(size=TOTAL_GROWTH_MARKER_SIZE, color=qoq_color, line=dict(color="white", width=2), symbol="diamond"),
        hovertemplate="%{x}<br>QtQ Growth: %{y:.2f}%<extra></extra>",
    ))

    y2_offset_unit = _calc_y2_offset_unit()
    # Gap minimum antar label (supaya tidak tumpang tindih) disesuaikan skala data
    min_label_gap = max(y2_offset_unit * 0.8, 0.6)

    def _add_breakdown_growth(prefix: str, label: str, base_color: str, dash_qoq: str, yshift_base: int):
        yoy_col = f"_{prefix}_yoy"
        qoq_col = f"_{prefix}_qoq"
        if yoy_col not in df_show.columns or qoq_col not in df_show.columns:
            return

        s_yoy = pd.to_numeric(df_show[yoy_col], errors="coerce")
        s_qoq = pd.to_numeric(df_show[qoq_col], errors="coerce")

        group_yoy = f"overall_{prefix}_yoy"
        group_qoq = f"overall_{prefix}_qoq"

        qoq_line_color = base_color

        fig.add_trace(go.Scatter(
            x=df_show[target_col],
            y=s_yoy,
            name=f"{label} YoY (%)",
            legendgroup=group_yoy,
            yaxis="y2",
            mode="lines+markers",
            line=dict(color=base_color, width=BREAKDOWN_GROWTH_LINE_WIDTH),
            marker=dict(size=BREAKDOWN_GROWTH_MARKER_SIZE, color=base_color, line=dict(color="white", width=1.5), symbol="circle"),
            hovertemplate="%{x}<br>" + label + " YoY: %{y:.2f}%<extra></extra>",
        ))

        fig.add_trace(go.Scatter(
            x=df_show[target_col],
            y=s_qoq,
            name=f"{label} QtQ (%)",
            legendgroup=group_qoq,
            yaxis="y2",
            mode="lines+markers",
            line=dict(color=qoq_line_color, width=BREAKDOWN_GROWTH_LINE_WIDTH, dash=dash_qoq),
            marker=dict(size=BREAKDOWN_GROWTH_MARKER_SIZE, color=qoq_line_color, line=dict(color="white", width=1.5), symbol="diamond"),
            hovertemplate="%{x}<br>" + label + " QtQ: %{y:.2f}%<extra></extra>",
        ))

        # Label di titik terakhir sebagai trace (biar ikut hide kalau legend di-click)
        last_x_local = df_show[target_col].iloc[-1]
        if pd.notna(s_yoy.iloc[-1]):
            _add_last_point_label_trace(
                x_val=last_x_local,
                y_val=float(s_yoy.iloc[-1]),
                text=f"{label[:3]} YoY {float(s_yoy.iloc[-1]):+.1f}%",
                legend_group=group_yoy,
                border_color=base_color,
                y_offset=float(yshift_base) * LABEL_OFFSET_BREAKDOWN_STEP * y2_offset_unit,
            )
        if pd.notna(s_qoq.iloc[-1]):
            _add_last_point_label_trace(
                x_val=last_x_local,
                y_val=float(s_qoq.iloc[-1]),
                text=f"{label[:3]} QtQ {float(s_qoq.iloc[-1]):+.1f}%",
                legend_group=group_qoq,
                border_color=qoq_line_color,
                y_offset=(float(yshift_base) - 0.6) * LABEL_OFFSET_BREAKDOWN_STEP * y2_offset_unit,
            )

    if show_breakdown_growth and (not is_month):
        # Warna & pola dibuat beda jelas antara YoY vs QtQ
        _add_breakdown_growth("inc", "Incoming", base_color="#701A75", dash_qoq="dot", yshift_base=3)
        _add_breakdown_growth("out", "Outgoing", base_color="#7C7812", dash_qoq="dot", yshift_base=1)
        _add_breakdown_growth("dom", "Domestik", base_color="#0F766E", dash_qoq="dot", yshift_base=-1)

    # Badge/label di titik terakhir (sebagai trace supaya ikut toggle)
    last_x = df_show[target_col].iloc[-1]
    if pd.notna(yoy.iloc[-1]):
        _add_last_point_label_trace(
            x_val=last_x,
            y_val=float(yoy.iloc[-1]),
            text=f"YoY {float(yoy.iloc[-1]):+.1f}%",
            legend_group=total_yoy_group,
            border_color=yoy_color,
            y_offset=LABEL_OFFSET_TOTAL * y2_offset_unit,
        )
    if pd.notna(qoq.iloc[-1]):
        _add_last_point_label_trace(
            x_val=last_x,
            y_val=float(qoq.iloc[-1]),
            text=f"{'MtM' if is_month else 'QtQ'} {float(qoq.iloc[-1]):+.1f}%",
            legend_group=total_qoq_group,
            border_color=qoq_color,
            y_offset=-LABEL_OFFSET_TOTAL * y2_offset_unit,
        )

    # Pastikan area y2 cukup untuk menampung label (tanpa keluar canvas)
    try:
        y2_series_vals: list[float] = []
        for s in [yoy, qoq]:
            y2_series_vals.extend(pd.to_numeric(s, errors="coerce").dropna().astype(float).tolist())

        if show_breakdown_growth and (not is_month):
            for col in ("_inc_yoy", "_inc_qoq", "_out_yoy", "_out_qoq", "_dom_yoy", "_dom_qoq"):
                if col in df_show.columns:
                    y2_series_vals.extend(
                        pd.to_numeric(df_show[col], errors="coerce").dropna().astype(float).tolist()
                    )

        y2_all = y2_series_vals + label_y_values
        if y2_all:
            y2_min = float(min(y2_all))
            y2_max = float(max(y2_all))
            y2_span = y2_max - y2_min
            y2_pad = max(1.0, y2_span * 0.12)
            y2_range = [y2_min - y2_pad, y2_max + y2_pad]
        else:
            y2_range = None
    except Exception:
        y2_range = None

    legend_items = 0
    try:
        legend_items = sum(1 for tr in fig.data if getattr(tr, "showlegend", True))
    except Exception:
        legend_items = 0
    legend_rows = max(1, (int(legend_items) + 3) // 4)
    # Space atas dinamis untuk title + legend (legend tetap di atas grafik, tapi tidak nabrak title)
    legend_block_px = max(32, 14 + legend_rows * (legend_fs + 10))
    top_margin_px = TOP_MARGIN_PX + legend_block_px
    bottom_margin_px = 80

    fig.update_layout(
        title=dict(
            text=f"Visualisasi Keseluruhan Data Transaksi - {y_title} (Per {period_label})",
            font=dict(size=title_fs, family="Inter, Arial, sans-serif", color="#1f2937", weight=700),
            y=0.98,
            yanchor="top",
        ),
        barmode="stack",
        xaxis=dict(
            title=dict(text="Periode", font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor="#d1d5db",
            tickangle=-45,
            tickfont=dict(size=x_tick_fs, family="Inter, Arial, sans-serif"),
        ),
        yaxis=dict(
            title=dict(text=y_title, font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            tickformat=",.0f",
            showgrid=True,
            gridwidth=1,
            gridcolor="#e5e7eb",
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor="#d1d5db",
            tickfont=dict(size=y_tick_fs, family="Inter, Arial, sans-serif")
        ),
        yaxis2=dict(
            title=dict(text="Growth (%)", font=dict(size=axis_title_fs, family="Inter, Arial, sans-serif")),
            overlaying="y",
            side="right",
            tickformat=".1f",
            showgrid=False,
            range=y2_range,
            tickfont=dict(size=y_tick_fs, family="Inter, Arial, sans-serif")
        ),
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="#f9fafb",
        font=dict(family="Inter, Arial, sans-serif", size=fs),
        legend=dict(
            orientation="h",
            # Legend diletakkan di area margin atas (bukan menimpa plot)
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#e5e7eb",
            borderwidth=1,
            groupclick="togglegroup",
            font=dict(size=legend_fs, family="Inter, Arial, sans-serif"),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=hover_fs, font_family="Inter, Arial, sans-serif"),
        margin=dict(l=60, r=RIGHT_MARGIN_PX, t=top_margin_px, b=bottom_margin_px),
    )

    # Tambah ruang kanan berbasis index kategori supaya label di kanan tidak kepotong.
    try:
        cats = df_show[target_col].astype(str).tolist()
        if len(cats) > 0:
            fig.update_layout(
                xaxis=dict(
                    type="category",
                    categoryorder="array",
                    categoryarray=cats,
                    range=[-0.5, (len(cats) - 0.5) + 0.9],
                )
            )
    except Exception:
        pass

    if chart_height is not None:
        fig.update_layout(height=int(chart_height))

    if chart_width is not None and int(chart_width) > 0:
        fig.update_layout(width=int(chart_width))
        st.plotly_chart(fig, use_container_width=False)
    else:
        st.plotly_chart(fig, use_container_width=True)

def make_combined_bar_line_chart_profile(df: pd.DataFrame, trx_type: str, nama_pjp: str, selected_year: str):
    # Buat label time-series lintas tahun: YYYY-MM dan urutkan kronologis
    df_copy = df.copy()
    
    if 'Year' in df_copy.columns and 'Month' in df_copy.columns:
        df_copy['MonthNum'] = df_copy['Month'].apply(lambda m: list(calendar.month_name).index(m) if isinstance(m, str) else int(m))
        df_copy['YearMonth'] = df_copy['Year'].astype(int).astype(str) + '-' + df_copy['MonthNum'].astype(int).astype(str).str.zfill(2)
        df_copy = df_copy.sort_values(['Year', 'MonthNum'])
    else:
        df_copy['YearMonth'] = df_copy.index.astype(str)

    if trx_type == 'Inc':
        trx_title = "Incoming"
        bar_color = '#F5B0CB'  # Pink
    elif trx_type == 'Out':
        trx_title = "Outgoing"
        bar_color = '#F5CBA7'  # Peach/Orange
    else:
        trx_title = "Domestik"
        bar_color = '#5DADE2'  # Blue

    fig = go.Figure()

    # Bar trace
    fig.add_trace(go.Bar(
        x=df_copy['YearMonth'],
        y=df_copy[f'Sum of Fin Nilai {trx_type}'],
        name="Nilai",
        yaxis='y1',
        marker=dict(
            color=bar_color,
            line=dict(width=0)
        ),
        hovertemplate="%{x}<br>Nilai: Rp %{y:,.0f}<extra></extra>"
    ))

    # Line trace dengan warna hijau
    fig.add_trace(go.Scatter(
        x=df_copy['YearMonth'],
        y=df_copy[f'Sum of Fin Jumlah {trx_type}'],
        name='Frekuensi',
        yaxis='y2',
        mode='lines+markers',
        line=dict(color='#1E8449', width=3),
        marker=dict(size=8, color='#1E8449', line=dict(color='white', width=2)),
        hovertemplate="%{x}<br>Frekuensi: %{y:,.0f}<extra></extra>"
    ))

    fig.update_layout(
        title=dict(
            text=f"Perkembangan Transaksi {trx_title} - {nama_pjp} ({selected_year})",
            font=dict(size=22, family='Inter, Arial, sans-serif', color='#1f2937', weight=700)
        ),
        xaxis=dict(
            title=dict(text="Periode (YYYY-MM)", font=dict(size=14, family='Inter, Arial, sans-serif')),
            tickangle=-45,
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor='#d1d5db',
            tickfont=dict(size=11, family='Inter, Arial, sans-serif')
        ),
        yaxis=dict(
            title=dict(text="Nilai (Rp Miliar)", font=dict(size=14, family='Inter, Arial, sans-serif')),
            tickformat=",.0f",
            showgrid=True,
            gridwidth=1,
            gridcolor='#e5e7eb',
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='#d1d5db'
        ),
        yaxis2=dict(
            title=dict(text='Frekuensi', font=dict(size=14, family='Inter, Arial, sans-serif')),
            overlaying='y',
            side='right',
            tickformat=",.0f",
            showgrid=False
        ),
        template="plotly_white",
        paper_bgcolor='white',
        plot_bgcolor='#f9fafb',
        font=dict(family='Inter, Arial, sans-serif', size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='#e5e7eb',
            borderwidth=1
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Inter, Arial, sans-serif"
        )
    )

    st.plotly_chart(fig, use_container_width=True)

