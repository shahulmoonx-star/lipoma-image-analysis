#!/usr/bin/env python
"""Train the platform model from the curated dataset (run automatically by run.py).

    python scripts/train.py

Output: artifacts/lipoma_model.joblib (encrypted)."""
from __future__ import annotations

import datetime as dt
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore")

import numpy as np
import sklearn

from lipoma_proto import config, licence
from lipoma_proto.classifier import TextPrior, cross_val_proba, fit_head, l2, max_similarity_outside_group
from lipoma_proto.dataset import load_curated
from lipoma_proto.features import FeatureExtractor, cached_features, image_hash
from lipoma_proto.matching import keypoints


def progress(i, n):
    if i % 40 == 0 or i == n:
        print(f"  images {i}/{n}", flush=True)


def main():
    config.ARTIFACT_DIR.mkdir(exist_ok=True)
    try:
        licence.dataset_files()
    except licence.LicenceError as exc:
        sys.exit(f"Licence problem: {exc}")
    if not (config.CURATED_DIR / "metadata.csv").exists():
        sys.exit("dataset_curated/ not found - run: python scripts/curate_dataset.py")

    print("1/4 reading the images ...")
    df = load_curated()
    pool = df[df.kind == "image"].reset_index(drop=True)
    ex = FeatureExtractor()
    X = cached_features(pool.path, pool.md5, ex, progress=progress, open_image=licence.dataset_image)
    g = np.arange(len(pool))                              # every picture is its own group
    y = pool.label.values
    mod = pool.modality.values
    prior = TextPrior(np.unique(y), ex.text_embeddings(np.unique(y)))

    print("2/4 preparing the location model ...")
    classes, P, _ = cross_val_proba(X, y, g, repeats=5, prior=prior)
    print("3/4 preparing the imaging-type model ...")
    mod_classes, Pm, _ = cross_val_proba(X, mod, g, repeats=3, C=config.MODALITY_C)
    sim_oof = max_similarity_outside_group(l2(X), g)      # how similar images are to their nearest other image

    print("4/4 saving ...")
    hashes, kps = [], []
    for p in pool.path:
        im = licence.dataset_image(p)
        hashes.append(image_hash(im))
        kps.append(keypoints(im))
    bundle = dict(
        backbone=config.BACKBONE, img_size=config.IMG_SIZE,
        head=fit_head(X, y, prior=prior), mod_head=fit_head(X, mod, C=config.MODALITY_C),
        ref_feats=l2(X).astype(np.float32), ref_paths=pool.path.tolist(), ref_labels=y.tolist(),
        ref_modality=mod.tolist(), ref_hash=hashes, ref_keypoints=kps, sim_oof=sim_oof,
        oof_proba=P.astype(np.float32), oof_mod_proba=Pm.astype(np.float32),
        trained_at=dt.datetime.now().isoformat(timespec="seconds"), sklearn_version=sklearn.__version__,
        n_images=int(len(pool)), n_classes=int(len(classes)),
    )
    licence.save_model(bundle, config.MODEL_FILE)
    print("Done.")


if __name__ == "__main__":
    main()
