"""Technical requirements for running the platform."""
import sys

import pandas as pd
import streamlit as st

from lipoma_proto.ui import kpi_row, page_title

page_title("Reference", "Technical requirements", "What a computer needs to run the platform.")

kpi_row([("Python", "3.10+", f"running {sys.version.split()[0]}"), ("Memory", "4 GB", "8 GB recommended"),
         ("Disk space", "3 GB", "including packages"), ("GPU", "Not needed", "runs on CPU"),
         ("Internet", "First run only", "to install packages")])

t_sys, t_pkg, t_run = st.tabs(["System", "Software packages", "Run and options"])

with t_sys:
    with st.container(border=True):
        st.dataframe(pd.DataFrame([
            ("Operating system", "Windows 10/11, macOS 12+, or a recent Linux"),
            ("Python", "3.10 or newer (64-bit)"),
            ("Processor", "Any 64-bit CPU, 4 cores recommended"),
            ("Memory", "4 GB minimum, 8 GB recommended"),
            ("Free disk space", "About 3 GB (packages about 2.5 GB, project about 70 MB)"),
            ("Browser", "Current Chrome, Edge, Firefox or Safari"),
            ("Network", "Needed once, to install packages; afterwards the platform runs offline")],
            columns=["Item", "Requirement"]), hide_index=True)
        st.caption("Network weights and the trained model are bundled, so nothing is downloaded when the platform starts.")

with t_pkg:
    with st.container(border=True):
        from importlib.metadata import PackageNotFoundError, version

        def ver(name):
            try:
                return version(name)
            except PackageNotFoundError:
                return "not installed"
        pk = [("streamlit", ">= 1.50", "Web interface"), ("torch", "any recent release (CPU build is enough)", "Feature extraction"),
              ("torchvision", "matching torch", "Image utilities"), ("open_clip_torch", ">= 2.23", "BiomedCLIP model"), ("transformers", "any recent release", "BiomedCLIP text encoder"), ("scikit-learn", "any recent release", "Classifiers"),
              ("numpy", "-", "Numerical arrays"), ("pandas", "-", "Tables and CSV"), ("pillow", "-", "Image reading and resizing"),
              ("joblib", "-", "Model file"), ("pydicom", "optional", "DICOM files")]
        st.dataframe(pd.DataFrame([(n, req, use, ver(n)) for n, req, use in pk], columns=["Package", "Required", "Used for", "Installed here"]), hide_index=True)
        st.caption("`python run.py` creates a private `.venv` in the project folder and installs everything from `requirements.txt`.")

with t_run:
    with st.container(border=True):
        st.markdown("**Start**")
        st.code("python run.py", language="bash")
        st.markdown("On Windows, double-click `start.bat`. The page opens at http://localhost:8501.")
        st.markdown("**Options**")
        st.dataframe(pd.DataFrame([("--port 9000", "Use another port"), ("--no-browser", "Do not open the browser automatically"),
                                   ("--rebuild", "Retrain the model from the curated dataset"),
                                   ("--make-offline-bundle", "Download packages into the folder for a computer without internet")],
                                  columns=["Option", "Effect"]), hide_index=True)
