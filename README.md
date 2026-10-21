# Lipoma Imaging

An academic platform for lipoma imaging. Import a medical image and the platform:

1. identifies the imaging type (MRI, CT, ultrasound, X-ray or mammography);
2. identifies the lipoma location (29 locations) and the body region;
3. shows similar cases;
4. presents the clinical background for that location: how common it is, typical age and sex, treatment options, medicines, follow-up and warning signs;
5. produces a downloadable report.

The repository also contains the cleaned and documented dataset of 224 images.

*Academic Projects - Getwebsite.Today.*

---

## Quick start (3 steps)

### Step 1 - Install Python (once)

| Software | Version | Download |
|---|---|---|
| **Python** (64-bit) | 3.10 or newer (3.11 or 3.12 recommended) | <https://www.python.org/downloads/> |

- **Windows:** run the installer and **tick "Add python.exe to PATH"** on the first screen, then *Install Now*.
- **macOS:** <https://www.python.org/downloads/macos/>
- **Linux:** `sudo apt install python3 python3-venv python3-pip`

Check it in a terminal: `python --version` (macOS / Linux: `python3 --version`).

Your computer needs about 6 GB free disk space, 4 GB memory (8 GB recommended) and internet for the first start. No graphics card is needed.

### Step 2 - Get the project and your licence file

1. On GitHub press **Code > Download ZIP** and **extract all** (do not run it from inside the zip). Or: `git clone https://github.com/shahulmoonx-star/lipoma-image-analysis.git`
2. Put the **licence file** you received by e-mail (its name ends with `.licence`) into the project folder, next to `run.py`. If you forget, the launcher looks in your Downloads folder or asks you for it.

### Step 3 - Run it

Open a terminal in the project folder and type:

```
python run.py
```

(Windows: you can also double-click **`start.bat`**. macOS / Linux: `python3 run.py`.)

That is all. `run.py` does everything for you and tells you what it is doing:

| What you will see | What it means | Time |
|---|---|---|
| creating a private environment | makes the `.venv` folder (nothing is installed on your system) | seconds |
| installing the required packages | downloads Streamlit, PyTorch and the others (about 3 GB) | 5-15 minutes |
| downloading the model weights | the BiomedCLIP model (about 800 MB) | a few minutes |
| training the model | prepares the model from the dataset | 5-15 minutes |
| starting the app on http://localhost:8501 | your browser opens by itself | - |

All of this happens only on the **first start**; later starts take a few seconds. **Do not close the window while it works.** To stop the platform press **Ctrl+C** in the terminal.

If something goes wrong, `run.py` stops with a boxed message that says what happened and what to do. Fix that, run `python run.py` again and it continues where it stopped. Everything it does is saved in `outputs/setup_log.txt`; send that file to the developer if you need help.

### Using the platform

1. Open **Image analysis**.
2. Import one or more images (PNG, JPG, BMP, TIFF, WEBP or DICOM). While the platform runs, the images you can try are in the `dataset_curated/images` folder.
3. Press **Run analysis** to see the imaging type, lipoma location, body region, similar cases, the clinical profile and a downloadable report.

### Options

| Command | Effect |
|---|---|
| `python run.py --port 9000` | use another port (a busy port is replaced automatically) |
| `python run.py --no-browser` | do not open the browser |
| `python run.py --rebuild` | retrain the model |
| `python run.py --make-offline-bundle` | download the packages so another computer can install without internet |

Problems? See [docs/06-troubleshooting.md](docs/06-troubleshooting.md).

---

## What is inside the platform

| Page | Purpose |
|---|---|
| **Image analysis** | import one or many images: imaging type, location and region, similar cases, clinical profile, report |
| **Clinical knowledge** | profiles of all 29 locations, a side-by-side comparison and general rules |
| **Dataset** | explorer, composition charts, curation log, datasheet and downloads |
| **Documentation** | short in-app overview |
| **Technical requirements** | what a computer needs to run the platform |

## The dataset

`dataset_curated/` holds 224 images in 29 location classes, standardised for academic use: PNG, 8-bit grayscale, 512 x 512 pixels with the aspect ratio preserved, named `<location>_<nnn>.png`, each with a SHA-256 checksum, and documented by `metadata.csv`, `DATASHEET.md`, `class_summary.csv` and `excluded.csv`. How it was built and what every column means: [docs/04-dataset.md](docs/04-dataset.md).

## Project structure

```
run.py, start.bat      one-command launcher
app.py                 application entry point and navigation
views/                 the pages
lipoma_proto/          code library and clinical knowledge base
dataset_curated/       the curated dataset (images encrypted in images.vault) with metadata, datasheet and checksums
data/                  annotation files used to build the dataset
scripts/               train.py, curate_dataset.py
models/                BiomedCLIP weights (downloaded on the first run, then offline)
docs/                  complete guide
.streamlit/            colour theme and settings
requirements.txt       Python packages
LICENSE.md             licence terms
```

`artifacts/` (trained model), `outputs/` (analysis log) and `.venv/` are created on the first run and are not stored in Git.

## Documentation

The complete guide is in [`docs/`](docs/README.md):

1. [Installation](docs/01-installation.md)
2. [User guide](docs/02-user-guide.md)
3. [Architecture](docs/03-architecture.md)
4. [Dataset](docs/04-dataset.md)
5. [Maintenance](docs/05-maintenance.md)
6. [Troubleshooting](docs/06-troubleshooting.md)

## Technology

Python, Streamlit, PyTorch with open_clip (frozen BiomedCLIP features and zero-shot text prior), scikit-learn (logistic-regression classifiers), pandas, NumPy, Pillow.

## Licence and credits

Copyright (c) 2026 **Getwebsite.Today** - copyright holder.
Developer: **Shahul Hameed.S** - shahul@getwebsite.today.
Programme: Academic Projects.

Licensed for academic, educational and non-commercial research use. See [LICENSE](LICENSE.md). For other use, contact shahul@getwebsite.today.
