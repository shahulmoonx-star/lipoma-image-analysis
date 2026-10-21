# 2. User guide

The platform has four pages, listed in the left sidebar: Image analysis, Clinical knowledge, Dataset and Documentation (plus Technical requirements).

## 2.1 Image analysis

1. Import one or more images with the uploader: PNG, JPG, BMP, TIFF (including 16-bit), WEBP or DICOM (`.dcm`; the middle slice of multi-slice files). While the platform runs, sample images are in `dataset_curated/images/`; the folder is removed when the platform stops.
2. Press **Run analysis**.

Imported files are not stored. Each analysis is recorded as one line (time, file name, result) in `outputs/analysis_log.csv`.

### Findings

| Item | Meaning |
|---|---|
| Imaging type | MRI, CT, ultrasound, X-ray or mammography. |
| Lipoma location | The lipoma location of the image. |
| Body region | The region (for example Abdomen, Brain / skull / scalp). |
| Location table | Shown when the location is determined by the model: the five most likely locations with confidence and region. |

An image that does not look like a medical image is flagged and is not interpreted.

### Many images at once

With several files the page lists every file with its imaging type, location and region. **Download results (CSV)** saves the list; *Show details for* opens the full findings of one file.

### Tabs below the findings

- **Similar cases** - the closest images of the dataset with similarity scores; *Enlarge* opens the full image.
- **Clinical profile** - how common the condition is, typical age and sex, typical sites, symptoms, imaging, look-alikes, management options, medicines, follow-up and warning signs for the location.
- **Report** - **Preview report** opens the report in a pop-up; **Download report (HTML)** saves it. Open the file in a browser and print to PDF if needed.

## 2.2 Clinical knowledge

- **Location profile** - choose a body region and a location to see its profile.
- **Compare all locations** - cards for all 29 locations; search by any word (for example *surgery* or *children*) and filter by region.
- **General rules** - what a lipoma is, general management and medicines, typical imaging, and notes by age group.

The knowledge text is educational background written from general medical teaching. It is not generated from the images.

## 2.3 Dataset

- **Explorer** - browse all 224 images; filter by location, imaging type and body region; *Enlarge* shows the full image; *Table view* shows the metadata.
- **Composition** - charts of images by imaging type, body region and location.
- **Curation log** - every raw file that was left out of the curated set, with the reason.
- **Datasheet & downloads** - the datasheet, plus downloads of `metadata.csv`, `DATASHEET.md` and `CHECKSUMS.sha256`.

## 2.4 Documentation and Technical requirements

Short in-app reference pages. The full guide is this `docs/` folder.
