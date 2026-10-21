"""Project documentation: purpose, workflow, method and data."""
import streamlit as st

from lipoma_proto import config
from lipoma_proto.ui import get_bundle, kpi_row, page_title

page_title("Reference", "Documentation", "Purpose, workflow, method and data of the platform.")

bundle = get_bundle()
N_IMAGES, N_CLASSES = bundle["n_images"], bundle["n_classes"]

kpi_row([("Images", N_IMAGES, "PNG 512 x 512"),
         ("Lipoma locations", N_CLASSES, "anatomical sites"),
         ("Imaging types", 5, "MRI, CT, US, X-ray, mammo"),
         ("Model", "BiomedCLIP", "ViT-B/16, PubMed images")])

t_over, t_use, t_method, t_data, t_files = st.tabs(["Overview", "How to use", "Method", "Data", "Folder structure"])

with t_over:
    with st.container(border=True):
        st.markdown("""
**Purpose.** An academic platform that takes a medical image, checks what kind of image it is, identifies the lipoma location
and presents the related clinical background for that location.

**What it reports**
- Imaging type (MRI, CT, ultrasound, X-ray, mammography).
- The lipoma location and the body region.
- Similar cases.
- A clinical profile for the location: how common, typical age and sex, treatment options, medicines, follow-up and warning signs.
- A downloadable HTML report.
""")

with t_use:
    with st.container(border=True):
        st.markdown("""
**Image analysis**
1. Open *Image analysis* and import one or more PNG, JPG, TIFF or DICOM files.
2. Press *Run analysis*.
3. Review the findings, the similar cases and the clinical profile, then download the report if needed.

**Other pages**
- *Clinical knowledge* - the profile of every location, a side-by-side comparison and general rules.
- *Dataset* - browse the images, composition, the curation log and the datasheet.
""")

with t_method:
    with st.container(border=True):
        st.markdown(f"""
**Pipeline**
1. *Preparation* - orientation from EXIF, 16-bit and DICOM windowing, conversion to 8-bit grayscale, resize to {config.IMG_SIZE} px.
2. *Features* - the frozen BiomedCLIP image encoder (a vision-language model trained on 15 million PubMed figure-caption pairs) produces 512 values, L2-normalised and averaged over the image and its mirror.
3. *Classification* - class-balanced logistic regression (C = {config.LOGREG_C}) for lipoma location, combined with BiomedCLIP's zero-shot match between the image and the text of every location name (weight {config.TEXT_PRIOR_WEIGHT}); a second logistic regression (C = {config.MODALITY_C}) for imaging type. The body region is the sum of the location probabilities.
4. *Matching* - borders are trimmed; an image fingerprint and, if needed, ORB keypoints with a RANSAC check match the image with the stored images, also when it was re-saved, resized, screenshotted, cropped or slightly rotated.
5. *Similar cases* - cosine similarity against all stored images.
6. *Image check* - images that do not look like medical images are flagged and not interpreted.
""")

with t_data:
    with st.container(border=True):
        st.markdown(f"""
**Dataset** - {N_IMAGES} images in {N_CLASSES} location classes, all PNG, 8-bit grayscale, 512 x 512, aspect ratio preserved by padding,
named `<location>_<nnn>.png`.

**Documentation shipped with the images:** `metadata.csv` (geometry, quality measures, fold, source fields), `excluded.csv` (every removed file with the reason),
`class_summary.csv`, `DATASHEET.md` and `CHECKSUMS.sha256`.

**Curation.** Duplicates, label conflicts, collages, non-images, unusable and low-resolution files were removed or quarantined. See the *Dataset* page for the full log.
""")

with t_files:
    with st.container(border=True):
        st.code("""run.py, start.bat      launcher (one command)
app.py, views/         the application pages
lipoma_proto/          code and clinical knowledge base
dataset_curated/       dataset: encrypted images (images.vault), metadata, datasheet, checksums
data/                  annotations used to build the dataset
scripts/               train.py, curate_dataset.py
models/                BiomedCLIP weights (downloaded on the first run)
docs/                  complete guide
LICENSE.md             licence terms""", language="text")

st.html('<div class="lp-foot">Lipoma Imaging - Academic Projects. Copyright (c) 2026 Getwebsite.Today. '
        'Developer: Shahul Hameed.S - shahul@getwebsite.today. Licensed for academic, educational and non-commercial research use.</div>')
