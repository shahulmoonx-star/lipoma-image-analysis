# 3. Architecture

## 3.1 What the system does

```
 uploaded image
      |
      v
 load_image  (EXIF rotation, 16-bit / DICOM handling, 8-bit grayscale)
      |
      v
 FeatureExtractor  (frozen BiomedCLIP ViT-B/16 image encoder, flip averaging -> 512 numbers)
      |
      +--> imaging-type head ------> MRI / CT / ultrasound / X-ray / mammography
      +--> location head ----------> 29 lipoma locations (+ body region from the location probabilities)
      |      fused with  BiomedCLIP zero-shot text match of every location name
      +--> image matching --------> the stored picture the upload is, if any
      +--> cosine similarity ------> similar cases, and the image check
      |
      v
 Streamlit pages  ->  findings, similar cases, clinical profile, report
```

The network is used only as a fixed feature extractor; nothing is fine-tuned. The location classifier is a class-balanced logistic regression (C = 0.05) on standardised features; its log-probabilities are added to 0.3 x the log-probabilities of BiomedCLIP's zero-shot match between the image and the text "a CT scan showing a gastric lipoma" (and five other templates) for every location. The text prior uses no training images, which helps the locations with only one or two images. The imaging-type classifier is a logistic regression (C = 0.3).

## 3.2 Folder map

| Path | Purpose |
|---|---|
| `run.py`, `start.bat` | one-command launcher: environment, packages, model, start |
| `app.py` | Streamlit entry point: page set-up, start-up screen, navigation |
| `views/` | the pages (`analysis`, `knowledge`, `dataset`, `documentation`, `requirements`) |
| `lipoma_proto/` | the code library (see below) and `knowledge_base.json` |
| `scripts/` | `train.py` (train the model), `curate_dataset.py` (build the curated dataset) |
| `dataset_curated/` | the publication dataset: 224 images (stored encrypted in `images.vault`; `images/` exists only while the platform runs) plus metadata, datasheet and checksums |
| `data/` | the annotation files that `curate_dataset.py` reads |
| `models/hf/` | BiomedCLIP weights, downloaded on the first run (not stored in Git) |
| `artifacts/` | the trained model and feature cache (created by `train.py`, not stored in Git) |
| `outputs/` | analysis log written while the platform is used (not stored in Git) |
| `.streamlit/config.toml` | colour theme and Streamlit settings |
| `docs/` | this guide |

## 3.3 Code library (`lipoma_proto/`)

| Module | Responsibility |
|---|---|
| `config.py` | paths, the BiomedCLIP model id, classifier settings, text-prior settings, class merging, body region of every class |
| `imageio.py` | opens uploaded files without importing PyTorch (so picture-only pages stay fast) |
| `features.py` | `FeatureExtractor` (BiomedCLIP image and text embeddings), the perceptual image hash and the on-disk feature cache |
| `matching.py` | image matching: candidate search, ORB keypoints, RANSAC check |
| `classifier.py` | logistic-regression heads, the zero-shot `TextPrior`, similarity reference |
| `analyzer.py` | `LipomaAnalyzer.analyze()` - turns an image into an `Analysis` (type, locations, regions, similar cases) |
| `dataset.py` | reads the curated dataset for training; scans raw folders for the curation script |
| `knowledge.py`, `knowledge_ui.py`, `knowledge_base.json` | the clinical text per location and how it is shown |
| `report.py` | builds the self-contained HTML report |
| `ui.py` | shared look and feel: CSS, figure cards, charts, tables, start-up screen, cached loaders |

### Behaviour worth knowing

- **Image matching** (`matching.py`). Every upload is first normalised: grayscale, auto-contrast and removal of uniform margins (black padding, white or dark screenshot frames). Then:
  1. *Fingerprint* - a 256-bit perceptual hash; within 20 bits of a stored image means the same picture (exact files and re-saved / resized copies). Different stored images are at least 37 bits apart.
  2. *Keypoints* - otherwise the 8 most similar stored images (BiomedCLIP cosine) are checked with ORB keypoints and a RANSAC similarity transform (rotation, scale, shift). 30 or more consistent keypoints confirm the match: copies keep 60 or more even when cropped, screenshotted or rotated; the most similar *different* picture keeps at most 14.

  A matched upload shows the stored image's label; the picture is left out of its own similar-case list.
- **Image check.** The similarity of an upload to its closest stored image is ranked against how similar the stored images are to each other. A very low rank, or a colour photograph with a low rank, marks the upload as not a medical image.
- **Start-up.** `app.py` starts a background thread that imports PyTorch, loads the model and warms the engine while a progress screen shows the percentage; every page is then fast.
- **Threads.** Streamlit runs scripts in worker threads, so `torch.no_grad()` is applied inside each call.

## 3.4 Body regions

Each of the 29 locations belongs to one of eight regions: Abdomen, Brain / skull / scalp, Breast, Chest, Groin / genital, Head & neck, Muscle / bone (limbs & trunk), Spine. The region result is the sum of the probabilities of the locations in each region. The mapping is in `lipoma_proto/config.py`.

## 3.5 Technology

Python, Streamlit (interface), PyTorch and open_clip / transformers (BiomedCLIP), scikit-learn (classifiers), pandas and NumPy (data), Pillow (images), Altair (charts, included with Streamlit), joblib (model file), pydicom (optional DICOM support).
