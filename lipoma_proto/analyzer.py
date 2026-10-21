"""Inference: image in -> imaging type, lipoma location, body region and similar cases."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from . import config, licence, matching
from .classifier import l2
from .features import FeatureExtractor, image_hash

COLOUR_PHOTO_THRESHOLD = 12.0   # mean channel difference (0-255) above which an image is "colour photo"


@dataclass
class Neighbor:
    path: str
    label: str
    modality: str
    similarity: float


@dataclass
class Analysis:
    modality: str                        # e.g. "MRI"
    modality_prob: float
    locations: list[tuple[str, float]]   # top-k (class, probability)
    regions: list[tuple[str, float]]     # regions sorted by summed probability
    similarity: float                    # cosine similarity to the closest stored image
    similarity_percentile: float         # where that sits among the stored images (0-100)
    usable: bool                         # False for images that are not medical images
    note: str                            # message shown when usable is False
    neighbors: list[Neighbor] = field(default_factory=list)
    match: Neighbor | None = None        # the stored image this upload is (also re-saved, resized, cropped ...)

    @property
    def location(self) -> str:
        return self.match.label if self.match else self.locations[0][0]

    @property
    def region(self) -> str:
        return config.region_of(self.match.label) if self.match else self.regions[0][0]

    @property
    def type_name(self) -> str:
        return (self.match.modality or self.modality) if self.match else self.modality

    @property
    def confidence(self) -> float | None:
        """Probability of the leading location; None for a stored image (its label is exact)."""
        return None if self.match else self.locations[0][1]


def colourfulness(img: Image.Image) -> float:
    rgb = np.asarray(img.convert("RGB").resize((128, 128)), dtype=np.float32)
    return float((np.abs(rgb[..., 0] - rgb[..., 1]) + np.abs(rgb[..., 1] - rgb[..., 2])).mean() / 2)


def _hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


class LipomaAnalyzer:
    def __init__(self, bundle_path: Path | str = config.MODEL_FILE):
        self.bundle = licence.load_model(bundle_path)
        b = self.bundle
        self.extractor = FeatureExtractor(b["backbone"], b["img_size"])
        self.head = b["head"]
        self.mod_head = b["mod_head"]
        self.ref = b["ref_feats"]            # L2-normalised reference features
        self.ref_hash = b["ref_hash"]
        self.ref_kp = b["ref_keypoints"]
        self.sim_oof = np.sort(b["sim_oof"])
        self.path_index = {p: i for i, p in enumerate(b["ref_paths"])}

    def _neighbor(self, i: int, sim: float) -> Neighbor:
        b = self.bundle
        return Neighbor(b["ref_paths"][i], b["ref_labels"][i], config.MODALITY_NAMES.get(b["ref_modality"][i], ""), float(sim))

    def find_match(self, img: Image.Image, sims: np.ndarray, exclude: int | None = None) -> int | None:
        """Index of the stored image this upload is a copy of (exact, re-saved, resized, cropped,
        screenshotted, slightly rotated)."""
        h = image_hash(img)
        d = np.array([_hamming(h, r) for r in self.ref_hash], dtype=float)
        sims = sims.copy()
        if exclude is not None:
            d[exclude], sims[exclude] = np.inf, -np.inf
        if d.min() <= config.KNOWN_IMAGE_HASH_BITS:
            return int(d.argmin())
        return matching.find(img, sims, self.ref_kp)[0]

    # ------------------------------------------------------------------ main entry
    def analyze(self, img: Image.Image, top_k: int = 5, n_neighbors: int = 5) -> Analysis:
        img.load()
        feat = self.extractor.features(img)[None]
        fn = l2(feat)
        sims = (self.ref @ fn[0]).astype(float)
        hi = self.find_match(img, sims)

        mod_p = self.mod_head.proba(feat)[0] if hi is None else self.bundle["oof_mod_proba"][hi]
        mod_classes = [config.MODALITY_NAMES.get(m, m) for m in self.mod_head.classes]
        mod_i = int(mod_p.argmax())

        p = self.head.proba(feat)[0] if hi is None else self.bundle["oof_proba"][hi]
        order = np.argsort(-p)
        locations = [(str(self.head.classes[i]), float(p[i])) for i in order[:top_k]]
        reg: dict[str, float] = {}
        for c, pc in zip(self.head.classes, p):
            r = config.region_of(str(c))
            reg[r] = reg.get(r, 0.0) + float(pc)
        regions = sorted(reg.items(), key=lambda kv: -kv[1])

        match = None
        if hi is not None:
            match = self._neighbor(hi, sims[hi])
            sims[hi] = -1.0                              # not offered as its own similar case
        nn = np.argsort(-sims)[:n_neighbors]
        neighbors = [self._neighbor(i, sims[i]) for i in nn]
        top_sim = float(sims[nn[0]])
        pct = float((self.sim_oof <= top_sim).mean() * 100)
        usable = match is not None or not self._not_medical(pct, colourfulness(img) > COLOUR_PHOTO_THRESHOLD)

        return Analysis(
            modality=mod_classes[mod_i], modality_prob=float(mod_p[mod_i]),
            locations=locations, regions=regions, similarity=top_sim, similarity_percentile=pct,
            usable=usable, note="" if usable else "This does not look like a medical image.",
            neighbors=neighbors, match=match,
        )

    @staticmethod
    def _not_medical(pct: float, colour: bool) -> bool:
        return (colour and pct < 25) or pct < 5
