"""Curated dataset: explorer, composition, quality control, curation log, datasheet."""
import pandas as pd
import streamlit as st

from lipoma_proto import config
from html import escape as esc

from lipoma_proto.ui import bar_chart, table_html, chip, page_title, pct, read_csv, read_json, kpi_row, show_image, thumbnail

page_title("Evidence", "Curated dataset", "A cleaned, documented and checksummed image collection prepared for academic use.")

meta = read_csv(str(config.CURATED_DIR / "metadata.csv"))
excl = read_csv(str(config.CURATED_DIR / "excluded.csv"))
cur = read_json(config.CURATED_DIR / "curation_stats.json")

kpi_row([("Images", len(meta), "PNG, 512 x 512"), ("Classes", meta.class_name.nunique(), "lipoma locations"),
         ("MRI images", int((meta.modality_code == "MR").sum()), pct((meta.modality_code == "MR").mean()) + " of set"),
         ("ML-eligible classes", cur["classes_ml_eligible"], f"of {cur['classes']} (3+ images)"),
         ("Files excluded", len(excl), f"of {cur['raw_files']} raw"), ("Checksummed", "100%", "SHA-256 per image")])

t_exp, t_comp, t_log, t_sheet = st.tabs(["Explorer", "Composition", "Curation log", "Datasheet & downloads"])

with t_exp:
    f1, f2, f3, f4 = st.columns([2, 1.4, 1.4, 0.8])
    cls_sel = f1.multiselect("Location", sorted(meta.class_name.unique()), placeholder="All locations")
    mod_sel = f2.multiselect("Imaging type", sorted(meta.modality.unique()), placeholder="All types")
    reg_sel = f3.multiselect("Body region", sorted(meta.body_region.unique()), placeholder="All regions")
    view = meta
    if cls_sel:
        view = view[view.class_name.isin(cls_sel)]
    if mod_sel:
        view = view[view.modality.isin(mod_sel)]
    if reg_sel:
        view = view[view.body_region.isin(reg_sel)]
    st.caption(f"{len(view)} images match")
    per_page = 8
    pages = max(1, -(-len(view) // per_page))
    page = f4.number_input("Page", 1, pages, 1, step=1)
    chunk = view.iloc[(page - 1) * per_page: page * per_page]
    for row_start in range(0, len(chunk), 4):
        cols = st.columns(4)
        for col, (_, r) in zip(cols, chunk.iloc[row_start: row_start + 4].iterrows()):
            with col.container(border=True):
                st.image(thumbnail(r.file), width="stretch")
                st.caption(f"**{r.image_id}** | {r.modality}  \n{r.class_name.replace(' lipoma', '').capitalize()}")
                if st.button("Enlarge", key=f"enl_{r.image_id}", width="stretch"):
                    show_image(r.file, f"{r.image_id} | {r.class_name} | {r.modality} | {r.width} x {r.height} px")
    with st.expander("Table view"):
        st.dataframe(view[["image_id", "class_name", "body_region", "modality", "width", "height", "blur_score", "contrast_std",
                           "has_color_overlay", "ml_eligible", "cv_fold", "label_source"]], hide_index=True)

with t_comp:
    c1, c2 = st.columns(2)
    with c1.container(border=True):
        st.markdown("**Images by imaging type**")
        bar_chart(meta.modality.value_counts(), rows=8)
    with c2.container(border=True):
        st.markdown("**Images by body region**")
        bar_chart(meta.body_region.value_counts(), rows=8)
    with st.container(border=True):
        st.markdown("**Images per location, split by imaging type**")
        bar_chart(pd.crosstab(meta.class_name.str.replace(" lipoma", "", regex=False).str.capitalize(), meta.modality), stacked=True, row_h=24)
    summ = read_csv(str(config.CURATED_DIR / "class_summary.csv"))
    summ = summ.rename(columns={c: c.replace("_", " ").capitalize() for c in summ.columns}).rename(columns={"Mri": "MRI", "Ct": "CT", "Xray": "X-ray", "Ml eligible": "ML-eligible", "Class name": "Location", "Body region": "Region"})
    st.dataframe(summ, hide_index=True)

with t_log:
    st.caption("Every raw file that did not enter the curated set, with the reason. Raw files are never modified - the original `dataset/` folder is kept as an archive.")
    with st.container(border=True):
        st.markdown("**Exclusions by reason**")
        bar_chart(excl.category.value_counts())
    table_html(["Raw file", "Category", "Reason"],
               [(esc(r.original_path), chip(esc(r.category), "info"), esc(r.reason)) for r in excl.itertuples()],
               ["2fr", "1.3fr", "3fr"])
    st.markdown("**Curation rules**")
    st.markdown("- Non-image files (video) are not used.\n- Identical pictures: one copy is kept; if the copies carry different class labels, all are removed.\n"
                f"- Longer side below {400} px: removed.\n- Collages, screenshots of spectra and unidentifiable crops: removed.\n"
                "- Images whose lesion could not be seen are quarantined until a radiologist confirms the label (`needs expert confirmation`).")

with t_sheet:
    sheet = (config.CURATED_DIR / "DATASHEET.md").read_text(encoding="utf-8")
    d1, d2, d3 = st.columns(3)
    d1.download_button("metadata.csv", (config.CURATED_DIR / "metadata.csv").read_bytes(), "metadata.csv", "text/csv", icon=":material/download:", width="stretch")
    d2.download_button("DATASHEET.md", sheet.encode("utf-8"), "DATASHEET.md", "text/markdown", icon=":material/download:", width="stretch")
    d3.download_button("CHECKSUMS.sha256", (config.CURATED_DIR / "CHECKSUMS.sha256").read_bytes(), "CHECKSUMS.sha256", "text/plain", icon=":material/download:", width="stretch")
    with st.container(border=True):
        st.markdown(sheet)

