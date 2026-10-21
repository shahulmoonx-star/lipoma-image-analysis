"""Scan the ./dataset folder, build a manifest and run structural checks on it."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from . import config

ROOT_NAME_RE = re.compile(r"^(?P<label>.+?)\s*-\s*(?P<num>\d+)$")


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def dhash(img: Image.Image, size: int = 8) -> int:
    """64-bit difference hash: robust to rescaling / recompression."""
    g = img.convert("L").resize((size + 1, size), Image.LANCZOS)
    a = np.asarray(g, dtype=np.int16)
    bits = (a[:, 1:] > a[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def load_modality_annotations() -> dict[str, str]:
    if not config.MODALITY_FILE.exists():
        return {}
    df = pd.read_csv(config.MODALITY_FILE)
    return dict(zip(df["path"], df["modality"]))


def scan_dataset(dataset_dir: Path | None = None) -> pd.DataFrame:
    """One row per file under the dataset folder (images and videos)."""
    dataset_dir = Path(dataset_dir or config.RAW_DATASET_DIR)
    modality = load_modality_annotations()
    rows = []
    for path in sorted(p for p in dataset_dir.rglob("*") if p.is_file()):
        ext = path.suffix.lower()
        rel = path.relative_to(dataset_dir).as_posix()
        in_root = path.parent == dataset_dir
        kind = "image" if ext in config.IMAGE_EXT else "video" if ext in config.VIDEO_EXT else "other"

        if in_root:
            m = ROOT_NAME_RE.match(path.stem)
            raw_label = m.group("label").strip().lower() if m else ""
        else:
            raw_label = path.relative_to(dataset_dir).parts[0].lower()

        row = dict(
            path=rel, abs_path=str(path), source="loose file" if in_root else "class folder",
            kind=kind, ext=ext, size_kb=round(path.stat().st_size / 1024, 1),
            raw_label=raw_label, label=config.canonical_label(raw_label) if raw_label else "",
            md5=_md5(path), width=None, height=None, mode="", gray_as_rgb=False,
            dhash=None, modality=modality.get(rel, ""),
        )
        if kind == "image":
            try:
                with Image.open(path) as im:
                    row["width"], row["height"], row["mode"] = im.width, im.height, im.mode
                    row["dhash"] = format(dhash(im), "016x")
                    if im.mode in ("RGB", "RGBA"):
                        a = np.asarray(im.convert("RGB"), dtype=np.int16)
                        row["gray_as_rgb"] = bool(np.abs(a[..., 0] - a[..., 1]).max() < 8 and
                                                  np.abs(a[..., 1] - a[..., 2]).max() < 8)
            except Exception as exc:  # unreadable / corrupt file
                row["kind"] = "broken"
                row["mode"] = f"error: {exc}"
        rows.append(row)
    df = pd.DataFrame(rows)
    df["region"] = df["label"].map(config.region_of)
    return df


class _UnionFind:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def duplicate_groups(df: pd.DataFrame, features: np.ndarray | None = None,
                     hash_dist: int = 4, cos_thr: float | None = None) -> np.ndarray:
    """Group ids so that exact copies / near copies (same picture re-saved, resized,
    cropped) share an id. Used both for reporting and to keep copies of one picture
    out of both train and test folds."""
    n = len(df)
    uf = _UnionFind(n)
    md5 = df["md5"].tolist()
    first = {}
    for i, h in enumerate(md5):
        if h in first:
            uf.union(i, first[h])
        else:
            first[h] = i
    hashes = [int(h, 16) if isinstance(h, str) else None for h in df["dhash"]]
    for i in range(n):
        if hashes[i] is None:
            continue
        for j in range(i + 1, n):
            if hashes[j] is not None and hamming(hashes[i], hashes[j]) <= hash_dist:
                uf.union(i, j)
    if features is not None and cos_thr is not None:
        f = features / np.linalg.norm(features, axis=1, keepdims=True)
        sim = f @ f.T
        for i, j in zip(*np.where(np.triu(sim, 1) >= cos_thr)):
            uf.union(int(i), int(j))
    roots = [uf.find(i) for i in range(n)]
    remap = {r: k for k, r in enumerate(dict.fromkeys(roots))}
    return np.array([remap[r] for r in roots])


def load_curated() -> pd.DataFrame:
    """The curated dataset as a frame with the columns the pipeline expects."""
    meta = pd.read_csv(config.CURATED_DIR / "metadata.csv", keep_default_na=False)
    df = pd.DataFrame(dict(
        path=meta.file, abs_path=[str(config.CURATED_DIR / f) for f in meta.file], source=meta.origin,
        kind="image", ext=["." + f.lower() for f in meta.format], size_kb=meta.size_kb, raw_label=meta.class_name,
        label=meta.class_name, md5=meta.sha256, width=meta.width, height=meta.height, mode="",
        modality=meta.modality_code, region=meta.body_region, image_id=meta.image_id, cv_fold=meta.cv_fold))
    return df
