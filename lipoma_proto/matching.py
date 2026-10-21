"""Image matching: is an upload one of the stored pictures?

Candidates come from BiomedCLIP similarity; each is then confirmed by ORB keypoints and a RANSAC
similarity transform (rotation + scale + shift). A copy of a curated picture - exact, re-saved, resized,
cropped, screenshotted, slightly rotated or brightened - keeps 60+ consistent keypoints; the most similar
*different* stored picture keeps at most 14."""
from __future__ import annotations

import warnings

import numpy as np
from PIL import Image

from . import config
from .features import to_gray

SIDE = 256


def _canon(img: Image.Image) -> np.ndarray:
    g = to_gray(img)
    s = SIDE / max(g.size)
    g = g.resize((max(16, round(g.width * s)), max(16, round(g.height * s))), Image.BILINEAR)
    return np.asarray(g, dtype=np.float32) / 255


def keypoints(img: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    """(keypoints [n, 2] float32, descriptors packed to [n, 32] uint8)."""
    from skimage.feature import ORB
    orb = ORB(n_keypoints=300, fast_threshold=0.05, downscale=1.3, n_scales=6)
    try:
        orb.detect_and_extract(_canon(img))
    except Exception:          # flat image without corners
        return np.zeros((0, 2), np.float32), np.zeros((0, 32), np.uint8)
    return orb.keypoints.astype(np.float32), np.packbits(orb.descriptors, axis=1)


def inliers(a: tuple[np.ndarray, np.ndarray], b: tuple[np.ndarray, np.ndarray]) -> int:
    """Number of keypoint pairs consistent with one rotation + scale + shift between the two images."""
    from skimage.feature import match_descriptors
    from skimage.measure import ransac
    from skimage.transform import SimilarityTransform
    (k1, d1), (k2, d2) = a, b
    if len(k1) < 8 or len(k2) < 8:
        return 0
    m = match_descriptors(np.unpackbits(d1, axis=1).astype(bool), np.unpackbits(d2, axis=1).astype(bool),
                          cross_check=True, max_ratio=0.85)
    if len(m) < min(6, config.MATCH_MIN_INLIERS):
        return 0
    if len(m) < config.MATCH_MIN_INLIERS:      # cannot reach the threshold - skip RANSAC
        return len(m) // 3
    src, dst = k1[m[:, 0]][:, ::-1], k2[m[:, 1]][:, ::-1]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model, inl = ransac((src, dst), SimilarityTransform, min_samples=3, residual_threshold=3,
                            max_trials=300, rng=0)
    if not model or inl is None or not 0.4 < model.scale < 2.5:
        return 0
    return int(inl.sum())


def find(img: Image.Image, sims: np.ndarray, ref_kp: list, n_candidates: int = config.MATCH_CANDIDATES):
    """(index of the matching curated picture or None, keypoint inliers of the best candidate)."""
    q = keypoints(img)
    best_n = 0
    for i in np.argsort(-sims)[:n_candidates]:
        n = inliers(q, ref_kp[i])
        if n >= config.MATCH_MIN_INLIERS:
            return int(i), n
        best_n = max(best_n, n)
    return None, best_n
