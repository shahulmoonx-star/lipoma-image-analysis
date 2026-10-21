"""Streamlit rendering of knowledge-base entries and the clinical-context result."""
from __future__ import annotations

import streamlit as st

from . import config
from .knowledge import class_info


def render_class(label: str) -> None:
    info = class_info(label)
    if not info:
        st.info("No knowledge-base entry for this class.")
        return
    from html import escape as e
    cells = "".join(f'<div class="lp-fact"><div class="l">{k}</div><div class="v">{e(info[f])}</div></div>'
                    for k, f in (("How common (approx.)", "how_common"), ("Typical age", "typical_age_text"), ("Sex", "sex_note")))
    st.html(f'<div class="lp-fhead"><span class="t">{e(label.capitalize())}</span><span class="r">{e(config.region_of(label))}</span></div>'
            f'<div class="lp-facts">{cells}</div>')
    t1, t2, t3 = st.tabs(["Clinical overview", "Management & medicines", "Follow-up & warning signs"])
    with t1:
        st.markdown(f"**Typical sites:** {info['typical_sites']}")
        st.markdown(f"**Symptoms:** {info['symptoms']}")
        st.markdown(f"**Imaging:** {info['imaging_note']}")
        st.markdown("**Look-alikes a clinician must exclude**\n" + "\n".join(f"- {d}" for d in info["differential"]))
    with t2:
        st.markdown(f"**Management options:** {info['management']}")
        st.markdown(f"**Medicines at this location:** {info['medicines']}")
    with t3:
        st.markdown(f"**Follow-up:** {info['follow_up']}")
        st.markdown("**Warning signs - seek medical review if present**\n" + "\n".join(f"- {r}" for r in info["red_flags"]))
