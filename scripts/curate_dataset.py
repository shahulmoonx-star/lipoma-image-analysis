#!/usr/bin/env python
"""Build the curated, publication-ready dataset from the raw ./dataset folder.

    python scripts/curate_dataset.py

Reads   dataset/ (raw, never modified), data/modality_annotations.csv, data/curation_decisions.csv,
        data/manual_review_notes.csv
Writes  dataset_curated/  images/<class>/LIP-xxxx.ext, metadata.csv, excluded.csv, class_summary.csv,
                          CHECKSUMS.sha256, DATASHEET.md
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
from sklearn.model_selection import StratifiedGroupKFold

from lipoma_proto import config
from lipoma_proto.dataset import duplicate_groups, scan_dataset

STD = 512                   # every published image is STD x STD pixels
MIN_SIDE_FOR_USE = 400      # images whose longer side is below this are too small to be useful
OVERLAY_SPREAD = 60         # channel spread above which a pixel counts as "coloured annotation"


def slug(label: str) -> str:
    return label.replace(" / ", "_").replace(" ", "_")


def standardize(src: Path, dest: Path) -> dict:
    """8-bit grayscale PNG, longest side scaled to STD, aspect ratio kept, centred on a black STD x STD canvas."""
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            im = Image.alpha_composite(Image.new("RGBA", im.size, (0, 0, 0, 255)), im)
        g = im.convert("L")
    w, h = g.size
    k = STD / max(w, h)
    nw, nh = max(1, round(w * k)), max(1, round(h * k))
    g = g.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("L", (STD, STD), 0)
    ox, oy = (STD - nw) // 2, (STD - nh) // 2
    canvas.paste(g, (ox, oy))
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest, format="PNG", optimize=True)
    return dict(orig_width=w, orig_height=h, aspect_ratio=round(w / h, 3), content_width=nw, content_height=nh, pad_x=ox, pad_y=oy)


def quality_metrics(path: Path) -> dict:
    with Image.open(path) as im:
        rgb = np.asarray(im.convert("RGB"), dtype=np.int16)
    gray = rgb.mean(axis=2)
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:])
    spread = rgb.max(axis=2) - rgb.min(axis=2)
    hist = np.bincount(gray.astype(np.uint8).ravel(), minlength=256) / gray.size
    nz = hist[hist > 0]
    return dict(blur_score=round(float(lap.var()), 1), contrast_std=round(float(gray.std()), 1),
                entropy=round(float(-(nz * np.log2(nz)).sum()), 2),
                color_overlay_pct=round(float((spread > OVERLAY_SPREAD).mean() * 100), 2))


def main():
    out_dir = config.CURATED_DIR
    df = scan_dataset(config.RAW_DATASET_DIR)
    manual = pd.read_csv(config.DATA_DIR / "curation_decisions.csv").set_index("path")
    notes = pd.read_csv(config.DATA_DIR / "manual_review_notes.csv").groupby("path").note.apply(" | ".join)

    decisions = {}                                   # path -> (category, reason)
    for _, r in df[df.kind != "image"].iterrows():
        decisions[r.path] = ("not an image", f"{r.ext} file - the pipeline only reads still images")
    imgs = df[df.kind == "image"].reset_index(drop=True)

    # duplicates: keep one copy (prefer class folder); if the copies disagree on the class, drop all copies
    imgs["grp"] = duplicate_groups(imgs)
    for _, d in imgs.groupby("grp"):
        if len(d) < 2:
            continue
        if d.label.nunique() > 1:
            for p in d.path:
                decisions[p] = ("label conflict", "Identical picture filed under different classes (" +
                                " vs ".join(sorted(set(d.raw_label))) + ") - cannot be both.")
        else:
            keep = d.sort_values(["source", "path"]).iloc[0].path
            for p in d.path:
                if p != keep:
                    decisions[p] = ("duplicate", f"Identical to {keep}")
    for p, r in manual.iterrows():
        decisions.setdefault(p, (r.category, r.reason))
    for _, r in imgs.iterrows():
        if max(r.width, r.height) < MIN_SIDE_FOR_USE:
            decisions.setdefault(r.path, ("low resolution", f"{r.width}x{r.height} px - longer side below {MIN_SIDE_FOR_USE}"))

    excluded = pd.DataFrame([dict(original_path=p, category=c, reason=why) for p, (c, why) in sorted(decisions.items())])
    keep = imgs[~imgs.path.isin(decisions)].copy().sort_values(["label", "path"]).reset_index(drop=True)

    # ---- write curated tree ----
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "images").mkdir(parents=True)
    rows, seq = [], {}
    for _, r in keep.iterrows():
        seq[r.label] = seq.get(r.label, 0) + 1
        image_id = f"{slug(r.label)}_{seq[r.label]:03d}"
        rel = f"images/{slug(r.label)}/{image_id}.png"
        dest = out_dir / rel
        geo = standardize(Path(r.abs_path), dest)
        q = quality_metrics(Path(r.abs_path))
        rows.append(dict(
            image_id=image_id, file=rel, class_name=r.label, class_slug=slug(r.label), body_region=r.region,
            modality_code=r.modality, modality=config.MODALITY_NAMES.get(r.modality, r.modality),
            width=STD, height=STD, format="PNG", colour_mode="L (8-bit grayscale)", size_kb=round(dest.stat().st_size / 1024, 1), **geo,
            sha256=hashlib.sha256(dest.read_bytes()).hexdigest(), original_path=r.path,
            origin=r.source, label_source="file name" if r.source == "loose file" else "folder name",
            **q, annotation_note=notes.get(r.path, ""), source_url="", licence=""))
    meta = pd.DataFrame(rows)
    counts = meta.class_name.value_counts()
    meta["ml_eligible"] = meta.class_name.map(lambda c: bool(counts[c] >= config.MIN_IMAGES_PER_CLASS))
    meta["has_color_overlay"] = meta.color_overlay_pct > 0.3

    # fixed, reproducible 5-fold assignment (copies already removed, so no picture straddles folds)
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    fold = np.zeros(len(meta), dtype=int)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for k, (_, te) in enumerate(cv.split(meta, meta.class_name, np.arange(len(meta)))):
            fold[te] = k + 1
    meta["cv_fold"] = fold
    meta.to_csv(out_dir / "metadata.csv", index=False)
    excluded.to_csv(out_dir / "excluded.csv", index=False)

    summ = (meta.groupby(["class_name", "body_region"]).agg(
        images=("image_id", "count"), mri=("modality_code", lambda s: int((s == "MR").sum())),
        ct=("modality_code", lambda s: int((s == "CT").sum())), ultrasound=("modality_code", lambda s: int((s == "US").sum())),
        xray=("modality_code", lambda s: int((s == "XR").sum())), mammography=("modality_code", lambda s: int((s == "MG").sum())),
        ml_eligible=("ml_eligible", "first")).reset_index().sort_values("images", ascending=False))
    summ.to_csv(out_dir / "class_summary.csv", index=False)
    (out_dir / "CHECKSUMS.sha256").write_text(
        "\n".join(f"{r.sha256}  {r.file}" for r in meta.itertuples()) + "\n", encoding="utf-8")

    stats = dict(
        raw_files=int(len(df)), kept=int(len(meta)), excluded=int(len(excluded)),
        excluded_by_category=excluded.category.value_counts().to_dict(), classes=int(counts.size),
        classes_ml_eligible=int((counts >= config.MIN_IMAGES_PER_CLASS).sum()),
        modality=meta.modality.value_counts().to_dict(), overlay_images=int(meta.has_color_overlay.sum()),
        median_width=int(meta.orig_width.median()), median_height=int(meta.orig_height.median()))
    (out_dir / "curation_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    write_datasheet(out_dir, meta, excluded, summ, stats)
    print(json.dumps(stats, indent=2))


def write_datasheet(out_dir, meta, excluded, summ, st):
    mri = st["modality"].get("MRI", 0)
    L = [
        "# Datasheet - Multi-modality Lipoma Image Collection (v1.0)", "",
        "Follows the structure of *Datasheets for Datasets* (Gebru et al.).", "",
        "## Motivation", "",
        "A collection of imaging examples of lipomas at 29 anatomical locations, assembled for an academic platform "
        "(imaging type, lipoma location and similar cases).", "",
        "## Composition", "",
        f"* **{st['kept']} images**, {st['classes']} classes (one per lipoma location; `peritesticular` and `inguinal canal` merged because the source held the same pictures).",
        "* Imaging types: " + ", ".join(f"{k} {v}" for k, v in st["modality"].items()) + f" - only {mri} images ({mri / st['kept']:.0%}) are MRI.",
        f"* {st['classes_ml_eligible']} of {st['classes']} classes have at least {config.MIN_IMAGES_PER_CLASS} images (`ml_eligible`); the rest are kept as rare-entity references only.",
        f"* {st['overlay_images']} images contain coloured annotations (arrows, text, Doppler); see `has_color_overlay` / `annotation_note`.",
        "* Source pictures were web-resolution (median %d x %d px); no DICOM headers, pixel spacing, patient, scanner or sequence information." % (st["median_width"], st["median_height"]), "",
        "## Standard format", "",
        "* **File format:** PNG, 8-bit grayscale (colour annotations such as arrows are flattened to grey).",
        f"* **Size:** every image is exactly {STD} x {STD} pixels.",
        "* **Aspect ratio:** preserved - the longest side is scaled to the full size and the image is centred on a black canvas; `content_width`, `content_height`, `pad_x`, `pad_y` and `aspect_ratio` in `metadata.csv` give the original geometry (images were resampled with Lanczos; small ones were enlarged slightly).",
        "* **Names:** `<location>_<number>.png` inside `images/<location>/`, numbered from 001 per location.",
        "",
        "## Collection and cleaning", "",
        "* Collected by the developer, Shahul Hameed.S (copyright held by Getwebsite.Today); class = folder name chosen by the developer.",
        "* Imaging type (MRI / CT / ultrasound / X-ray / mammography) was annotated by visual inspection (`modality_annotations.csv`).",
        f"* Curation removed {st['excluded']} of {st['raw_files']} raw files (`excluded.csv`, with reasons):", ""]
    for k, v in st["excluded_by_category"].items():
        L.append(f"  * {k}: {v}")
    L += ["", "* Files were converted to the standard format above, named by location and checksummed (`CHECKSUMS.sha256`).",
          "* Per-image quality metrics (`blur_score`, `contrast_std`, `entropy`, `color_overlay_pct`) are computed automatically.",
          "* `cv_fold` is a fixed 5-fold assignment (seed 42, stratified by class); exact copies were removed first.", "",
                  "## Maintenance", "", "Re-run `python scripts/curate_dataset.py` after editing `data/curation_decisions.csv`, `modality_annotations.csv` or the raw folder.", "",
          "## Classes", "", "| Class | Region | Images | MRI | CT | US | X-ray | Mammo | ML-eligible |", "|---|---|---|---|---|---|---|---|---|"]
    for r in summ.itertuples():
        L.append(f"| {r.class_name} | {r.body_region} | {r.images} | {r.mri} | {r.ct} | {r.ultrasound} | {r.xray} | {r.mammography} | {'yes' if r.ml_eligible else 'no'} |")
    (out_dir / "DATASHEET.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
