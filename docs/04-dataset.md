# 4. Dataset

`dataset_curated/` is the cleaned, standardised reference collection used by the platform.

## 4.1 At a glance

| Item | Value |
|---|---|
| Images | 224 |
| Location classes | 29 (22 with at least 3 images) |
| Imaging types | CT 110, MRI 81, ultrasound 15, X-ray 12, mammography 6 |
| File format | PNG, 8-bit grayscale |
| Size | exactly 512 x 512 pixels, aspect ratio preserved by centring on a black canvas |
| Names | `<location>_<nnn>.png` inside `images/<location>/`, numbered from 001 |
| Integrity | SHA-256 checksum for every image (`CHECKSUMS.sha256`) |

Raw collection: 238 files; 14 were left out (see 4.3).

## 4.2 Files in `dataset_curated/`

| File | Content |
|---|---|
| `images.vault` | the standardised images `images/<location>/<location>_<nnn>.png`, stored encrypted (AES-256-GCM). While the platform runs they are also written, read-only, to `images/`; that folder is deleted when it stops (not stored in Git) |
| `metadata.csv` | one row per image (columns below) |
| `class_summary.csv` | images per location, split by imaging type, with the ML-eligible flag |
| `excluded.csv` | every raw file that was left out, with category and reason |
| `curation_stats.json` | counts used by the app and the datasheet |
| `CHECKSUMS.sha256` | SHA-256 of every image, in `sha256sum` format |
| `DATASHEET.md` | the dataset datasheet (motivation, composition, format, collection, maintenance) |

### `metadata.csv` columns

| Column | Meaning |
|---|---|
| `image_id`, `file` | identifier and relative path of the standardised image |
| `class_name`, `class_slug` | location label and its file-name form |
| `body_region` | one of the eight regions |
| `modality_code`, `modality` | imaging type (MR, CT, US, XR, MG) and its name |
| `width`, `height`, `format`, `colour_mode`, `size_kb` | properties of the standardised file |
| `orig_width`, `orig_height`, `aspect_ratio` | geometry of the original picture |
| `content_width`, `content_height`, `pad_x`, `pad_y` | where the picture sits on the 512 x 512 canvas |
| `sha256` | checksum of the standardised file |
| `original_path`, `origin`, `label_source` | where the image came from and how its label was set |
| `blur_score`, `contrast_std`, `entropy`, `color_overlay_pct` | automatic quality measures |
| `annotation_note`, `has_color_overlay` | notes on arrows, text or colour overlays in the original |
| `source_url`, `licence` | fields for recording the source and licence of each image |
| `ml_eligible` | class has at least 3 images |
| `cv_fold` | fixed fold number (1-5, seed 42, stratified by class) |

## 4.3 How it was built (`scripts/curate_dataset.py`)

1. **Scan** the raw `dataset/` folder (one sub-folder per location).
2. **Apply decisions** from `data/curation_decisions.csv` (manual review of every doubtful file) and `data/modality_annotations.csv` (imaging type for each image, assigned by visual inspection).
3. **Remove duplicates**: exact and near-identical copies are found by checksum and perceptual hash; one copy is kept. If copies carry different labels, all are removed.
4. **Exclude** collages, spectra and screenshots, non-image files, unusable pictures and pictures with a longer side below 400 px.
5. **Quarantine** pictures whose lesion could not be seen until a radiologist confirms the label.
6. **Merge** `peritesticular` and `inguinal canal`, which held the same pictures.
7. **Standardise**: convert to 8-bit grayscale, scale the longer side to 512 px, centre on a black 512 x 512 canvas, save as PNG, name by location and number.
8. **Document**: write metadata, quality measures, folds, the exclusion list, checksums, the class summary and the datasheet.

| Exclusion category | Files |
|---|---|
| duplicate | 3 |
| collage | 2 |
| not an image | 2 |
| label conflict | 2 |
| needs expert confirmation | 2 |
| low resolution | 1 |
| not a plain image | 1 |
| unusable | 1 |

## 4.4 Annotation files in `data/`

| File | Columns | Purpose |
|---|---|---|
| `curation_decisions.csv` | `path, category, reason` | the manual decision for every raw file that is removed or quarantined |
| `manual_review_notes.csv` | `path, issue, note` | observations from the manual review of individual files |
| `modality_annotations.csv` | `path, modality` | imaging type of every raw image |

## 4.5 Verifying integrity

`CHECKSUMS.sha256` lists the SHA-256 of every image inside the vault. The vault itself is protected by AES-GCM: any change to `images.vault` makes it fail to open, so the platform never works with damaged images.

## 4.6 Copyright and licence of the images

The copyright in the images and in all other dataset files is held by Getwebsite.Today. They may be used for academic, educational and non-commercial research under the terms of the [LICENSE](../LICENSE.md), with the credit line given there. The `source_url` and `licence` columns in `metadata.csv` are available for recording the origin of individual images.
