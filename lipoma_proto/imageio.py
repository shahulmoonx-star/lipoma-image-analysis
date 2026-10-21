"""Open user images (no torch import, so pages that only show pictures stay fast)."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageOps


def load_image(fp, name: str = "") -> Image.Image:
    """Open a user file as an 8-bit PIL image: handles EXIF rotation, 16-bit / float TIFF and
    (if `pydicom` is installed) DICOM files - the middle frame of a multi-slice file."""
    if str(name).lower().endswith((".dcm", ".dicom")):
        try:
            import pydicom
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Reading DICOM needs the optional package: pip install pydicom") from exc
        ds = pydicom.dcmread(fp)
        arr = ds.pixel_array.astype(np.float32)
        if arr.ndim == 3 and arr.shape[-1] not in (3, 4):
            arr = arr[arr.shape[0] // 2]
        lo, hi = np.percentile(arr, [0.5, 99.5])
        arr = np.clip((arr - lo) / max(hi - lo, 1e-6), 0, 1) * 255
        if getattr(ds, "PhotometricInterpretation", "") == "MONOCHROME1":
            arr = 255 - arr
        return Image.fromarray(arr.astype(np.uint8))
    img = ImageOps.exif_transpose(Image.open(fp))
    if img.mode.startswith("I") or img.mode == "F":       # 16-bit / 32-bit grayscale
        arr = np.asarray(img, dtype=np.float32)
        lo, hi = np.percentile(arr, [0.5, 99.5])
        img = Image.fromarray((np.clip((arr - lo) / max(hi - lo, 1e-6), 0, 1) * 255).astype(np.uint8))
    img.load()
    return img
