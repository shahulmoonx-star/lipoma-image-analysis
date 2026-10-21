# 5. Maintenance

All commands are run from the project folder. Inside the project's own environment (`.venv`) use `.venv\Scripts\python` on Windows or `.venv/bin/python` on macOS and Linux, or simply let `run.py` do the work.

## 5.1 Retrain the model

```
python run.py --rebuild
```

or, directly:

```
python scripts/train.py
```

This extracts features (cached in `artifacts/features_cache.npz`; only new images are processed), fits the final models and rewrites `artifacts/lipoma_model.joblib`. It takes a few minutes.

The launcher rebuilds the model automatically when it is missing, was saved with a different scikit-learn version or with another backbone.

## 5.2 Rebuild the curated dataset from the original images

The original collection is not part of the repository. To rebuild:

1. Put the original folders into a folder named `dataset/` in the project root (one sub-folder per location, e.g. `dataset/adrenal lipoma/1.png`). `dataset/` is ignored by Git.
2. Edit the decision files in `data/` if needed:
   - `curation_decisions.csv` - files to remove or quarantine, with category and reason
   - `modality_annotations.csv` - imaging type of every image
   - `manual_review_notes.csv` - review notes
3. Run:

   ```
   python scripts/curate_dataset.py
   python scripts/train.py
   ```

`dataset_curated/` is regenerated (images, metadata, exclusions, checksums, datasheet) and the model is retrained.

The platform reads the images only from `dataset_curated/images.vault`; the developer stores new images there before retraining and committing.

## 5.3 Add new images to the curated dataset

The simplest route is to add them to `dataset/` as above, add their imaging type to `data/modality_annotations.csv`, and re-run the two commands. Keep these rules:

- one folder per location, named exactly like the existing locations;
- check that the image is not a duplicate and shows a single image rather than a collage;
- record the origin of each new image in `metadata.csv` (`source_url`, `licence`).

## 5.4 Add or edit clinical text

`lipoma_proto/knowledge_base.json` holds the text:

- `general` - text shown on *Clinical knowledge > General rules*;
- `classes.<location name>` - one entry per location with `how_common`, `typical_age` (low, high), `typical_age_text`, `sex_note`, `typical_sites`, `symptoms`, `imaging_note`, `differential` (list), `management`, `medicines`, `follow_up` and `red_flags` (list).

Location names must match the class names exactly (see `class_summary.csv`). A new location also needs a body region in `lipoma_proto/config.py` (`REGION_OF_CLASS`).

## 5.5 Change the look

Colours and fonts are in `.streamlit/config.toml`. The shared styles, figure cards, charts and tables are in `lipoma_proto/ui.py`. Pages are in `views/`; the navigation is in `app.py`.

## 5.6 Files created at run time

| Path | Created by | Notes |
|---|---|---|
| `.venv/` | `run.py` | private Python environment; safe to delete (recreated on the next run) |
| `artifacts/` | `train.py` | trained model and feature cache; safe to delete (rebuilt on the next run) |
| `outputs/analysis_log.csv` | the Image analysis page | one line per analysis |
| `wheels/` | `run.py --make-offline-bundle` | offline packages |

None of these are stored in Git.
