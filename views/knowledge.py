"""Clinical knowledge browser."""
from html import escape as esc

import streamlit as st

from lipoma_proto import config
from lipoma_proto.knowledge import general_info, load_kb
from lipoma_proto.knowledge_ui import render_class
from lipoma_proto.ui import page_title

page_title("Reference", "Clinical knowledge", "Reference profiles for 29 lipoma locations.")

kb, gen = load_kb(), general_info()
t_loc, t_cmp, t_gen = st.tabs(["Location profile", "Compare all locations", "General rules"])

with t_loc:
    regions = sorted({config.region_of(c) for c in kb["classes"]})
    r = st.selectbox("Body region", ["All"] + regions)
    opts = sorted(c for c in kb["classes"] if r == "All" or config.region_of(c) == r)
    label = st.selectbox("Location", opts, format_func=str.capitalize)
    render_class(label)

with t_cmp:
    def first(text, n=150):
        t = text.split(". ")[0].rstrip(".")
        return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + " ..."
    f1, f2 = st.columns([2, 1])
    q = f1.text_input("Search", placeholder="e.g. surgery, children, bronchoscopy")
    reg = f2.selectbox("Region", ["All"] + sorted({config.region_of(c) for c in kb["classes"]}), key="cmp_region")
    items = []
    for c, v in kb["classes"].items():
        blob = " ".join([c, config.region_of(c)] + [str(x) for x in v.values()]).lower()
        if (not q or q.lower() in blob) and (reg == "All" or config.region_of(c) == reg):
            items.append((c, v))
    st.caption(f"{len(items)} locations")
    items.sort(key=lambda cv: (config.region_of(cv[0]), cv[0]))
    cards = "".join(f'<div class="lp-card"><div class="t">{esc(c.capitalize())}</div><div class="r">{esc(config.region_of(c))}</div>'
                    f'<div class="k">How common</div><div class="v">{esc(first(v["how_common"]))}</div>'
                    f'<div class="k">Typical age</div><div class="v">{esc(first(v["typical_age_text"], 80))}</div>'
                    f'<div class="k">Management</div><div class="v">{esc(first(v["management"]))}</div></div>' for c, v in items)
    st.html(f'<div class="lp-grid">{cards}</div>')

with t_gen:
    def fact(title, *paras):
        return f'<div class="lp-fact"><div class="l">{title}</div><div class="v">' + "".join(f"<p>{esc(p)}</p>" for p in paras) + "</div></div>"
    st.html('<div class="lp-grid2">'
            + fact("What a lipoma is", gen["what_is_it"], gen["how_common"])
            + fact("Management", gen["management"])
            + fact("Typical imaging", gen["imaging_mri"], gen["imaging_ct"], gen["imaging_us"])
            + fact("Medicines", gen["medicines"]) + "</div>")
    ag = gen["age_groups"]
    rows = "".join(f'<div class="row"><b>{a}</b><span>{esc(ag[k])}</span></div>' for a, k in
                   (("Under 3 years", "under_3"), ("3-17 years", "3_to_17"), ("18-39 years", "18_to_39"), ("40-59 years", "40_to_59"), ("60+ years", "60_plus")))
    st.html(f'<div class="lp-sec">Notes by age group</div><div class="lp-rows">{rows}</div>')
