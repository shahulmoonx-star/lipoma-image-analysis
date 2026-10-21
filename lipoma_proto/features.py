"""Image -> feature vector with BiomedCLIP (frozen), plus the class text embeddings used as a zero-shot prior."""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageOps

from . import config

os.environ.setdefault("HF_HUB_CACHE", str(config.HF_CACHE_DIR))     # weights live inside the project folder
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch  # noqa: E402

_MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)    # CLIP normalisation
_STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)


def trim_border(g: Image.Image, tol: float = 8.0) -> Image.Image:
    """Remove uniform margins on every side: black padding, white screenshot borders, grey frames."""
    a = np.asarray(g, dtype=np.float32)
    top, bot, left, right = 0, a.shape[0], 0, a.shape[1]
    while bot - top > 16 and a[top, left:right].std() < tol:
        top += 1
    while bot - top > 16 and a[bot - 1, left:right].std() < tol:
        bot -= 1
    while right - left > 16 and a[top:bot, left].std() < tol:
        left += 1
    while right - left > 16 and a[top:bot, right - 1].std() < tol:
        right -= 1
    return g.crop((left, top, right, bot))


def to_gray(img: Image.Image) -> Image.Image:
    """8-bit grayscale, auto-contrast, uniform borders removed (so a screenshot of a picture equals the picture)."""
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
        img = Image.alpha_composite(bg, img)
    return trim_border(ImageOps.autocontrast(img.convert("L"), cutoff=1))


def prepare_image(img: Image.Image, size: int = config.IMG_SIZE) -> Image.Image:
    """Grayscale -> auto-contrast -> trim uniform borders -> letter-box to a square (keeps the aspect ratio).

    Colour is dropped on purpose: coloured arrows / text overlays in screenshots would
    otherwise be an easy shortcut for the classifier."""
    g = to_gray(img)
    w, h = g.size
    scale = size / max(w, h)
    g = g.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BICUBIC)
    canvas = Image.new("L", (size, size), 0)
    canvas.paste(g, ((size - g.width) // 2, (size - g.height) // 2))
    return canvas


def image_hash(img: Image.Image) -> str:
    """256-bit difference hash of the prepared image (finds re-saved / resized copies of a picture)."""
    g = prepare_image(img, 128).resize((17, 16), Image.LANCZOS)
    a = np.asarray(g, dtype=np.int16)
    bits = (a[:, 1:] > a[:, :-1]).flatten()
    return format(int("".join("1" if b else "0" for b in bits), 2), "064x")


def _to_tensor(gray: Image.Image) -> torch.Tensor:
    a = np.asarray(gray, dtype=np.float32) / 255.0
    a = np.stack([a, a, a], axis=-1)
    a = (a - _MEAN) / _STD
    return torch.from_numpy(a.transpose(2, 0, 1))


class FeatureExtractor:
    """Frozen BiomedCLIP ViT-B/16 image encoder: 512 numbers per image, averaged over the image and
    its mirror, L2-normalised. The same model embeds the class names, which gives a zero-shot prior."""

    VERSION = "biomedclip-v2-trim"

    def __init__(self, backbone: str = config.BACKBONE, size: int = config.IMG_SIZE):
        if backbone != "biomedclip":
            raise ValueError(f"unsupported backbone: {backbone} - retrain with: python run.py --rebuild")
        import open_clip
        self.size = size
        self.backbone = backbone
        self.model, _, _ = open_clip.create_model_and_transforms(config.BIOMEDCLIP_ID)
        self.model.eval()
        self._tokenizer = open_clip.get_tokenizer(config.BIOMEDCLIP_ID)

    # torch.no_grad() is thread-local, so it is applied per call (Streamlit runs scripts in worker threads).
    def features(self, img: Image.Image, flip_tta: bool = True) -> np.ndarray:
        gray = prepare_image(img, self.size)
        views = [gray] + ([gray.transpose(Image.FLIP_LEFT_RIGHT)] if flip_tta else [])
        with torch.no_grad():
            f = self.model.encode_image(torch.stack([_to_tensor(v) for v in views])).float().mean(0)
        f = f / f.norm().clamp_min(1e-12)
        return f.numpy().astype(np.float32)

    def text_embeddings(self, class_names) -> np.ndarray:
        """One L2-normalised embedding per class: the mean over the prompt templates in config."""
        out = []
        with torch.no_grad():
            for c in class_names:
                name = str(c).replace(" / ", " or ")
                e = self.model.encode_text(self._tokenizer([t.format(name) for t in config.TEXT_TEMPLATES])).float()
                e = e / e.norm(dim=-1, keepdim=True)
                m = e.mean(0)
                out.append((m / m.norm()).numpy())
        return np.stack(out).astype(np.float32)


def cached_features(paths, md5s, extractor: FeatureExtractor, cache_file=config.FEATURE_CACHE,
                    progress=None, open_image=Image.open) -> np.ndarray:
    """Features for many images; results are cached by file hash so re-runs are instant.
    `open_image(path)` returns a PIL image (the curated images come from the encrypted vault)."""
    tag = f"{extractor.backbone}-{extractor.VERSION}-{extractor.size}"
    cache = {}
    if cache_file.exists():
        with np.load(cache_file, allow_pickle=False) as z:
            if str(z["tag"]) == tag:
                cache = dict(zip(z["md5"].tolist(), z["feat"]))
    out = []
    for i, (p, h) in enumerate(zip(paths, md5s)):
        if h not in cache:
            cache[h] = extractor.features(open_image(p))
        out.append(cache[h])
        if progress:
            progress(i + 1, len(paths))
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    keys = list(cache)
    np.savez_compressed(cache_file, tag=np.array(tag), md5=np.array(keys), feat=np.stack([cache[k] for k in keys]))
    return np.stack(out)
