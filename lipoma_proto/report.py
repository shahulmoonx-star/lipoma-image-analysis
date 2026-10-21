"""Self-contained HTML report (open in a browser, print to PDF if needed)."""
from __future__ import annotations

import base64
import datetime as dt
import html
import io

from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from .analyzer import Analysis
from .knowledge import class_info, general_info


def _data_uri(img: Image.Image, max_side: int = 520) -> str:
    im = img.convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _e(x) -> str:
    return html.escape(str(x))


def _list(items) -> str:
    return "<ul>" + "".join(f"<li>{_e(i)}</li>" for i in items) + "</ul>" if items else "<p>-</p>"


def build_report(image: Image.Image, filename: str, a: Analysis, selected: str,
                 model_note: str = "") -> str:
    info = class_info(selected)
    gen = general_info()
    rows = "".join(f"<tr><td>{_e(c)}</td><td>{p * 100:.1f}%</td></tr>" for c, p in a.locations)
    regs = "".join(f"<tr><td>{_e(r)}</td><td>{p * 100:.1f}%</td></tr>" for r, p in a.regions[:4])
    if a.match:
        result = (f"<p>Lipoma location: <b>{_e(a.location)}</b><br>Body region: <b>{_e(a.region)}</b></p>")
    else:
        result = (f"<table><tr><th>Location</th><th>Confidence</th></tr>{rows}</table>"
                  f"<h3>Body region</h3><table><tr><th>Region</th><th>Confidence</th></tr>{regs}</table>")
    nn = "".join(f"<tr><td>{_e(n.label)}</td><td>{_e(n.modality)}</td><td>{n.similarity:.3f}</td></tr>" for n in a.neighbors)
    css = ("body{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#222}"
           "h1{font-size:22px}h2{font-size:17px;border-bottom:1px solid #ddd;padding-bottom:4px;margin-top:26px}h3{font-size:14px}"
           "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 10px;text-align:left;font-size:13px}"
           "img{max-width:420px;width:100%;border:1px solid #ddd}p,li{font-size:14px;line-height:1.45}")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Lipoma analysis report</title><style>{css}</style></head><body>
<h1>Lipoma imaging - analysis report</h1>
<p>File: <b>{_e(filename)}</b> &nbsp;|&nbsp; Created: {dt.datetime.now():%Y-%m-%d %H:%M} &nbsp;|&nbsp; {_e(model_note)}</p>
<div><img src="{_data_uri(image)}"></div>

<h2>1. Image check</h2>
<p>Image type: <b>{_e(a.type_name)}</b>{'' if a.match else f' ({a.modality_prob * 100:.0f}% confidence)'}.</p>

<h2>2. Lipoma location</h2>
{result}
<h3>Similar cases</h3><table><tr><th>Location</th><th>Type</th><th>Similarity</th></tr>{nn}</table>

<h2>3. About: {_e(selected)}</h2>
<p><b>How common (approx.):</b> {_e(info.get('how_common', '-'))}</p>
<p><b>Typical age:</b> {_e(info.get('typical_age_text', '-'))} &nbsp; <b>Sex:</b> {_e(info.get('sex_note', '-'))}</p>
<p><b>Typical sites:</b> {_e(info.get('typical_sites', '-'))}</p>
<p><b>Symptoms:</b> {_e(info.get('symptoms', '-'))}</p>
<p><b>Imaging:</b> {_e(info.get('imaging_note', '-'))}</p>
<p><b>Mimics to exclude:</b></p>{_list(info.get('differential', []))}
<p><b>Management options:</b> {_e(info.get('management', '-'))}</p>
<p><b>Medicines:</b> {_e(info.get('medicines', '-'))}</p>
<p><b>General note on medicines:</b> {_e(gen['medicines'])}</p>
<p><b>Follow-up:</b> {_e(info.get('follow_up', '-'))}</p>
<p><b>Warning signs:</b></p>{_list(info.get('red_flags', []))}
</body></html>"""
