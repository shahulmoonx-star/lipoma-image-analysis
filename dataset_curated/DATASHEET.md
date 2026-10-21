# Datasheet - Multi-modality Lipoma Image Collection (v1.0)

Follows the structure of *Datasheets for Datasets* (Gebru et al.).

## Motivation

A collection of imaging examples of lipomas at 29 anatomical locations, assembled for an academic platform (imaging type, lipoma location and similar cases).

## Composition

* **224 images**, 29 classes (one per lipoma location; `peritesticular` and `inguinal canal` merged because the source held the same pictures).
* Imaging types: CT 110, MRI 81, Ultrasound 15, X-ray 12, Mammography 6 - only 81 images (36%) are MRI.
* 22 of 29 classes have at least 3 images (`ml_eligible`); the rest are kept as rare-entity references only.
* 5 images contain coloured annotations (arrows, text, Doppler); see `has_color_overlay` / `annotation_note`.
* Source pictures were web-resolution (median 630 x 630 px); no DICOM headers, pixel spacing, patient, scanner or sequence information.

## Standard format

* **File format:** PNG, 8-bit grayscale (colour annotations such as arrows are flattened to grey).
* **Size:** every image is exactly 512 x 512 pixels.
* **Aspect ratio:** preserved - the longest side is scaled to the full size and the image is centred on a black canvas; `content_width`, `content_height`, `pad_x`, `pad_y` and `aspect_ratio` in `metadata.csv` give the original geometry (images were resampled with Lanczos; small ones were enlarged slightly).
* **Names:** `<location>_<number>.png` inside `images/<location>/`, numbered from 001 per location.

## Collection and cleaning

* Collected by the developer, Shahul Hameed.S (copyright held by Getwebsite.Today); class = folder name chosen by the developer.
* Imaging type (MRI / CT / ultrasound / X-ray / mammography) was annotated by visual inspection (`modality_annotations.csv`).
* Curation removed 14 of 238 raw files (`excluded.csv`, with reasons):

  * duplicate: 3
  * collage: 2
  * not an image: 2
  * label conflict: 2
  * needs expert confirmation: 2
  * low resolution: 1
  * not a plain image: 1
  * unusable: 1

* Files were converted to the standard format above, named by location and checksummed (`CHECKSUMS.sha256`).
* Per-image quality metrics (`blur_score`, `contrast_std`, `entropy`, `color_overlay_pct`) are computed automatically.
* `cv_fold` is a fixed 5-fold assignment (seed 42, stratified by class); exact copies were removed first.

## Maintenance

Re-run `python scripts/curate_dataset.py` after editing `data/curation_decisions.csv`, `modality_annotations.csv` or the raw folder.

## Classes

| Class | Region | Images | MRI | CT | US | X-ray | Mammo | ML-eligible |
|---|---|---|---|---|---|---|---|---|
| pericallosal lipoma | Brain / skull / scalp | 26 | 16 | 8 | 2 | 0 | 0 | yes |
| intraosseous lipoma | Muscle / bone (limbs & trunk) | 24 | 9 | 5 | 0 | 10 | 0 | yes |
| quadrigeminal cistern lipoma | Brain / skull / scalp | 17 | 15 | 2 | 0 | 0 | 0 | yes |
| intestinal lipoma | Abdomen | 16 | 0 | 16 | 0 | 0 | 0 | yes |
| intramuscular lipoma | Muscle / bone (limbs & trunk) | 12 | 6 | 5 | 1 | 0 | 0 | yes |
| filar lipoma | Spine | 11 | 9 | 2 | 0 | 0 | 0 | yes |
| breast lipoma | Breast | 10 | 1 | 0 | 3 | 0 | 6 | yes |
| parotid lipoma | Head & neck | 10 | 0 | 7 | 3 | 0 | 0 | yes |
| suprasellar cistern lipoma | Brain / skull / scalp | 8 | 6 | 2 | 0 | 0 | 0 | yes |
| pancreatic lipoma | Abdomen | 8 | 2 | 6 | 0 | 0 | 0 | yes |
| gastric lipoma | Abdomen | 8 | 0 | 8 | 0 | 0 | 0 | yes |
| cerebellopontine angle lipoma | Brain / skull / scalp | 7 | 4 | 3 | 0 | 0 | 0 | yes |
| intermuscular lipoma | Muscle / bone (limbs & trunk) | 7 | 5 | 2 | 0 | 0 | 0 | yes |
| choroid plexus lipoma | Brain / skull / scalp | 7 | 2 | 5 | 0 | 0 | 0 | yes |
| mesenteric lipoma | Abdomen | 6 | 0 | 5 | 1 | 0 | 0 | yes |
| cardiac lipoma | Chest | 6 | 1 | 5 | 0 | 0 | 0 | yes |
| paracaval lipoma | Abdomen | 6 | 0 | 6 | 0 | 0 | 0 | yes |
| pleural lipoma | Chest | 5 | 0 | 3 | 0 | 2 | 0 | yes |
| inguinal canal / peritesticular lipoma | Groin / genital | 5 | 1 | 1 | 3 | 0 | 0 | yes |
| subgaleal lipoma | Brain / skull / scalp | 5 | 2 | 2 | 1 | 0 | 0 | yes |
| mediastinal lipoma | Chest | 4 | 1 | 3 | 0 | 0 | 0 | yes |
| hepatic lipoma | Abdomen | 3 | 0 | 3 | 0 | 0 | 0 | yes |
| endobronchial lipoma | Chest | 2 | 0 | 2 | 0 | 0 | 0 | no |
| adrenal lipoma | Abdomen | 2 | 0 | 2 | 0 | 0 | 0 | no |
| chest wall lipoma | Chest | 2 | 0 | 1 | 1 | 0 | 0 | no |
| pericardial lipoma | Chest | 2 | 0 | 2 | 0 | 0 | 0 | no |
| intracranial osteolipoma | Brain / skull / scalp | 2 | 1 | 1 | 0 | 0 | 0 | no |
| parosteal lipoma | Muscle / bone (limbs & trunk) | 2 | 0 | 2 | 0 | 0 | 0 | no |
| esophageal lipoma | Chest | 1 | 0 | 1 | 0 | 0 | 0 | no |
