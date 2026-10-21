"""Shared look-and-feel helpers for the Streamlit app (corporate theme lives in .streamlit/config.toml)."""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pandas as pd
import streamlit as st

from . import config

NAVY = "#14304D"
ACCENT = "#0F8B8D"

_CSS = f"""
<style>
.block-container {{ padding-top:2.2rem; padding-bottom:1.5rem; }}
[data-testid="stSidebarNav"]::before {{ content:"Lipoma Imaging"; display:block; color:#FFFFFF; font-size:18px; font-weight:650;
  letter-spacing:.01em; padding:6px 14px 14px 14px; margin-bottom:6px; border-bottom:1px solid #26425E; }}
[data-testid="stMarkdownContainer"] h1 {{ font-size:22px; color:{NAVY}; padding:0 0 6px 0; }}
[data-testid="stMarkdownContainer"] h2 {{ font-size:17px; color:{NAVY}; padding:14px 0 4px 0; }}
[data-testid="stMarkdownContainer"] h3 {{ font-size:15px; color:{NAVY}; }}
.lp-page {{ border-bottom:1px solid #D5DDE6; padding-bottom:10px; margin-bottom:14px; }}
.lp-page .eyebrow {{ font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:{ACCENT}; font-weight:600; }}
.lp-page h2 {{ margin:2px 0 2px 0; padding:0; font-size:24px; color:{NAVY}; }}
.lp-page p {{ margin:0; color:#5B6B7B; font-size:14px; }}
.lp-chip {{ display:inline-block; font-size:11px; font-weight:600; padding:2px 9px; border-radius:11px; margin-right:6px; }}
.lp-ok {{ background:#DCF3E7; color:#067647; }} .lp-warn {{ background:#FDEBD0; color:#B54708; }}
.lp-info {{ background:#E1EDF8; color:#0B4F8A; }} .lp-bad {{ background:#FBE0DD; color:#B42318; }}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] {{ border-radius:8px; padding:9px 12px; margin:2px 0; border-left:3px solid transparent; }}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"] {{ background:#1D4263; border-left:3px solid #0F8B8D; font-weight:600; }}
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] {{ display:none !important; }}
.lp-card {{ border:1px solid #D5DDE6; border-top:3px solid {ACCENT}; border-radius:8px; padding:14px 16px 12px 16px; background:#fff; }}
.lp-card .t {{ font-size:16px; font-weight:650; color:{NAVY}; }}
.lp-card .r {{ font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:{ACCENT}; font-weight:600; margin-bottom:8px; }}
.lp-card .k {{ font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:#5B6B7B; margin-top:8px; }}
.lp-card .v {{ font-size:13px; color:#1B2733; line-height:1.4; }}
.lp-fhead {{ display:flex; align-items:baseline; gap:12px; margin:2px 0 10px 0; }}
.lp-fhead .t {{ font-size:20px; font-weight:650; color:{NAVY}; }}
.lp-fhead .r {{ font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:{ACCENT}; font-weight:600; }}
.lp-facts {{ display:grid; grid-template-columns:2fr 1fr 1fr; gap:12px; margin:0 0 14px 0; }}
.lp-fact {{ border:1px solid #D5DDE6; border-top:3px solid {ACCENT}; border-radius:8px; padding:14px 16px; background:#fff; }}
.lp-fact .l {{ font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:#5B6B7B; font-weight:600; margin-bottom:6px; }}
.lp-fact .v {{ font-size:14px; color:#1B2733; line-height:1.5; }}
@media (max-width:900px) {{ .lp-facts {{ grid-template-columns:1fr; }} }}
.lp-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:6px 0 14px 0; }}
.lp-grid2 {{ display:grid; grid-template-columns:repeat(2,1fr); gap:14px; margin:6px 0 14px 0; }}
.lp-fact .v p {{ margin:0 0 8px 0; }}
.lp-fact .v p:last-child {{ margin:0; }}
.lp-rows {{ border:1px solid #D5DDE6; border-radius:8px; background:#fff; margin:6px 0 14px 0; }}
.lp-rows .row {{ display:grid; grid-template-columns:150px 1fr; gap:16px; padding:11px 16px; border-bottom:1px solid #E6ECF2; font-size:14px; line-height:1.5; color:#1B2733; }}
.lp-rows .row:last-child {{ border-bottom:0; }}
.lp-rows .row b {{ color:{NAVY}; font-weight:600; }}
.lp-sec {{ font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:{ACCENT}; font-weight:600; margin:18px 0 6px 0; }}
@media (max-width:1100px) {{ .lp-grid {{ grid-template-columns:repeat(2,1fr); }} }}
.lp-table {{ border:1px solid #D5DDE6; border-radius:8px; overflow:hidden; background:#fff; margin:6px 0 14px 0; }}
.lp-table .trow {{ display:grid; gap:16px; padding:9px 16px; border-bottom:1px solid #E6ECF2; font-size:13px; line-height:1.45; color:#1B2733; }}
.lp-table .trow:last-child {{ border-bottom:0; }}
.lp-table .thead {{ background:#14304D; color:#fff; font-weight:600; border-bottom:0; }}
.lp-kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:4px 0 14px 0; }}
.lp-kpi {{ border:1px solid #D5DDE6; border-radius:8px; padding:14px 16px; background:#fff; min-height:104px; }}
.lp-kpi .l {{ font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:#5B6B7B; font-weight:600; }}
.lp-kpi .v {{ font-size:28px; font-weight:600; color:{NAVY}; line-height:1.25; margin-top:4px; }}
.lp-kpi .v.sm {{ font-size:20px; line-height:2.2rem; }}
.lp-kpi .s {{ font-size:12px; color:#5B6B7B; min-height:16px; }}
.lp-foot {{ font-size:12px; color:#5B6B7B; border-top:1px solid #D5DDE6; margin-top:30px; padding-top:10px; }}
</style>
"""


def inject_css() -> None:
    st.html(_CSS)


def page_title(eyebrow: str, title: str, text: str = "") -> None:
    st.html(f'<div class="lp-page"><div class="eyebrow">{eyebrow}</div><h2>{title}</h2>' + (f"<p>{text}</p>" if text else "") + "</div>")


def kpi_html(items) -> str:
    """Equal-size indicator cards. items: (label, value[, note])."""
    def cell(i):
        small = " sm" if len(str(i[1])) > 12 else ""
        note = i[2] if len(i) > 2 else ""
        return f'<div class="lp-kpi"><div class="l">{i[0]}</div><div class="v{small}">{i[1]}</div><div class="s">{note}</div></div>'
    return '<div class="lp-kpis">' + "".join(cell(i) for i in items) + "</div>"


def kpi_row(items) -> None:
    st.html(kpi_html(items))


def chip(text: str, kind: str = "info") -> str:
    return f'<span class="lp-chip lp-{kind}">{text}</span>'


@st.cache_data(show_spinner=False)
def read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=False)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def pct(v: float, digits: int = 0) -> str:
    return f"{v * 100:.{digits}f}%"


_lock = threading.Lock()
_analyzer = None


def get_analyzer():
    """The image model (imports PyTorch, a few seconds) - created once, shared by all sessions."""
    global _analyzer
    with _lock:
        if _analyzer is None:
            from .analyzer import LipomaAnalyzer
            _analyzer = LipomaAnalyzer()
    return _analyzer


_state = {"pct": 0, "msg": "Starting", "done": False, "error": None, "started": False}


def _warm() -> None:
    """Load everything slow once, in the background, reporting progress for the start-up screen."""
    def step(pct, msg):
        _state["pct"], _state["msg"] = pct, msg
    try:
        step(5, "Loading numerical libraries")
        import numpy as np, sklearn, altair  # noqa: F401
        step(15, "Loading deep-learning libraries")
        import torch, open_clip  # noqa: F401
        step(40, "Loading the image model (BiomedCLIP)")
        an = get_analyzer()
        step(65, "Loading the image library")
        from . import licence
        meta = pd.read_csv(config.CURATED_DIR / "metadata.csv")
        licence.dataset_files()
        step(75, "Warming up the image engine")
        an.analyze(licence.dataset_image(meta.file.iloc[0]))
        step(100, "Ready")
        _state["done"] = True
    except Exception as exc:  # shown on the start-up screen
        _state["error"] = f"{type(exc).__name__}: {exc}"


def start_warmup() -> dict:
    """Start the background loader once and return its progress state."""
    with _lock:
        if not _state["started"]:
            _state["started"] = True
            threading.Thread(target=_warm, daemon=True).start()
    return _state


def loading_screen(state: dict) -> None:
    """Full-page start-up screen with a percentage; returns when everything is loaded."""
    import time
    slot = st.empty()
    while not state["done"] and not state["error"]:
        with slot.container():
            st.html('<div style="height:18vh"></div><div class="lp-page"><div class="eyebrow">Starting</div>'
                    '<h2>Lipoma Imaging Platform</h2></div>')
            st.progress(state["pct"] / 100, text=f"{state['pct']}%  -  {state['msg']}")
        time.sleep(0.15)
    if state["error"]:
        slot.error(f"Start-up failed: {state['error']}")
        st.stop()
    slot.empty()


@st.cache_resource(show_spinner=False)
def get_bundle() -> dict:
    """Saved model data without loading PyTorch (enough for the dataset page)."""
    from . import licence
    return licence.load_model(config.MODEL_FILE)


@st.cache_data(show_spinner=False)
def thumbnail(rel: str, side: int = 520):
    """Square preview of a curated image (rel = metadata `file`, read from the in-memory dataset)."""
    from PIL import Image, ImageOps
    from . import licence
    im = ImageOps.contain(licence.dataset_image(rel).convert("RGB"), (side, side))
    canvas = Image.new("RGB", (side, side), (12, 16, 22))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    return canvas


SERIES = ["#0B4F8A", "#0F8B8D", "#7A5AA6", "#C2701E", "#B42318"]


def bar_chart(data, stacked: bool = False, row_h: int = 28, rows: int = 0) -> None:
    """Horizontal bars in the app theme. data: Series (name -> count) or, if stacked, a crosstab DataFrame (rows x series)."""
    import altair as alt
    axis_y = alt.Axis(labelLimit=260, title=None, ticks=False, domain=False, labelOverlap=False, labelColor="#1B2733", labelFontSize=12)
    if stacked:
        long = data.stack().rename("count").reset_index()
        long.columns = ["name", "series", "count"]
        order = list(data.sum(axis=1).sort_values(ascending=False).index)
        chart = alt.Chart(long).mark_bar(stroke="#FFFFFF", strokeWidth=1).encode(
            y=alt.Y("name:N", sort=order, axis=axis_y), x=alt.X("count:Q", title=None, axis=alt.Axis(grid=True, tickMinStep=1)),
            color=alt.Color("series:N", scale=alt.Scale(domain=list(data.columns), range=SERIES), legend=alt.Legend(orient="top", title=None)),
            tooltip=["name", "series", "count"])
        n = len(data)
    else:
        df = data.rename_axis("name").reset_index(name="count").sort_values("count", ascending=False)
        base = alt.Chart(df).encode(y=alt.Y("name:N", sort=list(df["name"]), axis=axis_y))
        chart = base.mark_bar(color=SERIES[0]).encode(x=alt.X("count:Q", title=None, axis=alt.Axis(grid=True, tickMinStep=1)), tooltip=["name", "count"])             + base.mark_text(align="left", dx=4, fontSize=12, color="#1B2733").encode(x="count:Q", text="count:Q")
        n = len(df)
    st.altair_chart(chart.properties(height=row_h * max(n, rows) + 30), width="stretch")


def table_html(header, rows, widths) -> None:
    st.html(table_markup(header, rows, widths))


def table_markup(header, rows, widths) -> str:
    """Wrapping, theme-consistent table (no truncated cells). rows: list of tuples of already-escaped HTML strings."""
    cols = " ".join(widths)
    head = f'<div class="trow thead" style="grid-template-columns:{cols}">' + "".join(f"<span>{h}</span>" for h in header) + "</div>"
    body = "".join(f'<div class="trow" style="grid-template-columns:{cols}">' + "".join(f"<span>{c}</span>" for c in r) + "</div>" for r in rows)
    return f'<div class="lp-table">{head}{body}</div>'


@st.dialog("Image viewer", width="large")
def show_image(rel: str, caption: str = ""):
    from . import licence
    st.image(licence.dataset_image(rel), width="stretch")
    if caption:
        st.caption(caption)
