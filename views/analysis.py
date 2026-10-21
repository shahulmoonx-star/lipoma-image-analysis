"""Image analysis: import one or many images, see the imaging type, lipoma location and clinical profile."""
import datetime as dt

import pandas as pd
import streamlit as st

from lipoma_proto import config, licence
from lipoma_proto.imageio import load_image
from lipoma_proto.knowledge_ui import render_class
from lipoma_proto.report import build_report
from lipoma_proto.ui import kpi_row, get_analyzer, get_bundle, page_title, pct, show_image

bundle = get_bundle()
LOG_FILE = config.OUTPUT_DIR / "analysis_log.csv"
TYPES = ["png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp", "dcm"]

page_title("Platform", "Image analysis", "Import a medical image to identify the imaging type and the lipoma location, and review the clinical profile.")


def short(label: str) -> str:
    return label.replace(" lipoma", "").capitalize()


def log_analysis(name, a):
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    row = dict(time=dt.datetime.now().isoformat(timespec="seconds"), file=name, image_type=a.type_name, location=a.location)
    new = pd.DataFrame([row])
    if LOG_FILE.exists() and pd.read_csv(LOG_FILE, nrows=0).columns.tolist() != list(row):   # older log layout
        pd.concat([pd.read_csv(LOG_FILE), new]).to_csv(LOG_FILE, index=False)
    else:
        new.to_csv(LOG_FILE, mode="a", header=not LOG_FILE.exists(), index=False)


@st.dialog("Report preview", width="large")
def preview_report(html):
    st.iframe(html, height=620)


def ranking_table(a):
    tbl = pd.DataFrame({"Location": [c.capitalize() for c, _ in a.locations], "Confidence": [p for _, p in a.locations],
                        "Region": [config.region_of(c) for c, _ in a.locations]})
    st.dataframe(tbl, hide_index=True, column_config={
        "Confidence": st.column_config.ProgressColumn("Confidence", min_value=0.0, max_value=1.0, format="percent")})


def show_detail(res):
    a, img = res["analysis"], res["image"]
    left, right = st.columns([1.15, 1.6])
    with left:
        st.image(img, caption=res["name"], width="stretch")
    with right:
        if not a.usable:
            kpi_row([("Imaging type", a.modality, f"{pct(a.modality_prob)} confidence"), ("Lipoma location", "-", ""), ("Body region", "-", "")])
            st.warning(a.note)
        else:
            conf = a.confidence
            kpi_row([("Imaging type", a.type_name, "" if a.match else f"{pct(a.modality_prob)} confidence"),
                     ("Lipoma location", short(a.location), "" if conf is None else f"{pct(conf)} confidence"),
                     ("Body region", a.region, "" if a.match else pct(a.regions[0][1]))])
            if not a.match:
                ranking_table(a)

    t_sim, t_prof, t_rep = st.tabs(["Similar cases", "Clinical profile", "Report"])
    with t_sim:
        for start in range(0, len(a.neighbors), 3):
            cols = st.columns(3)
            for col, n in zip(cols, a.neighbors[start:start + 3]):
                with col.container(border=True):
                    st.image(licence.dataset_image(n.path), width="stretch")
                    st.caption(f"**{short(n.label)}**  \n{n.modality} | similarity {n.similarity:.2f}")
                    if st.button("Enlarge", key=f"nb_{res['name']}_{n.path}", width="stretch"):
                        show_image(n.path, f"{n.label} | {n.modality} | similarity {n.similarity:.2f}")
    with t_prof:
        if a.usable:
            options = [a.location] if a.match else list(dict.fromkeys([a.location] + [c for c, _ in a.locations]))
            selected = st.selectbox("Profile for location", options, index=0, format_func=str.capitalize, key=f"prof_{res['name']}")
            render_class(selected)
        else:
            st.caption("No clinical profile is shown for this image.")
    with t_rep:
        if a.usable:
            html = build_report(img, res["name"], a, a.location, model_note=f"model {bundle['backbone']}, trained {bundle['trained_at']}")
            st.caption("A self-contained HTML report with findings, similar cases and clinical profile. Open it in a browser and print to PDF if needed.")
            b1, b2, _ = st.columns([1, 1, 3])
            if b1.button("Preview report", icon=":material/visibility:", width="stretch", key=f"prev_{res['name']}"):
                preview_report(html)
            b2.download_button("Download report (HTML)", html.encode("utf-8"), type="primary", icon=":material/download:", width="stretch",
                               file_name=f"lipoma_report_{dt.datetime.now():%Y%m%d_%H%M%S}.html", mime="text/html", key=f"dl_{res['name']}")
        else:
            st.caption("No report is available for this image.")


def show_batch(results):
    d = pd.DataFrame([dict(File=r["name"], Type=r["analysis"].type_name,
                           Location=short(r["analysis"].location) if r["analysis"].usable else "-",
                           Region=r["analysis"].region if r["analysis"].usable else "-") for r in results])
    kpi_row([("Images", len(d), "analysed")])
    st.dataframe(d, hide_index=True, width="stretch")
    st.download_button("Download results (CSV)", d.to_csv(index=False).encode("utf-8"), "lipoma_results.csv", "text/csv", icon=":material/download:")
    pick = st.selectbox("Show details for", range(len(results)), format_func=lambda i: results[i]["name"])
    st.divider()
    show_detail(results[pick])


with st.container(border=True):
    files = st.file_uploader("Import one or more images - PNG, JPG, TIFF or DICOM", type=TYPES, accept_multiple_files=True)
    items = []
    for f in files or []:
        try:
            items.append((f.name, load_image(f, f.name)))
        except Exception as exc:
            st.error(f"Could not open {f.name}: {exc}")
    run = st.button(f"Run analysis ({len(items)} image{'s' if len(items) != 1 else ''})" if items else "Run analysis",
                    type="primary", disabled=not items, icon=":material/play_arrow:")

if run:
    an = get_analyzer()
    results = []
    bar = st.progress(0.0, text="Analysing ...")
    for k, (name, image) in enumerate(items):
        a = an.analyze(image)
        results.append(dict(analysis=a, image=image, name=name))
        log_analysis(name, a)
        bar.progress((k + 1) / len(items), text=f"Analysed {k + 1} of {len(items)}")
    bar.empty()
    st.session_state["results"] = results

if st.session_state.get("results"):
    res = st.session_state["results"]
    st.divider()
    st.subheader("Findings" if len(res) == 1 else f"Findings - {len(res)} images")
    if len(res) == 1:
        show_detail(res[0])
    else:
        show_batch(res)
