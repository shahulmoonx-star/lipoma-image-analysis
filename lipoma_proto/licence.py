"""Licence check, in-memory dataset and encrypted model.

The platform runs only with a licence file issued by the developer. A licence names its holder, has an
expiry date (normally 500 days after issue) and is signed with the developer's private key, which is not part
of this repository; the app verifies the signature with the public key below, so licences cannot be made or
altered by anyone else.

The curated images are stored encrypted (dataset_curated/images.vault, AES-256-GCM). The key that opens them
is carried inside the licence. With a valid licence the vault is decrypted into memory; while the platform
runs (run.py) the images are also written, read-only, to dataset_curated/images/ so that they can be picked in
a file dialog, and that folder is deleted when the platform stops. The trained model is saved encrypted with
the same key, so it is unusable without a licence. A copy of the repository without a valid licence contains
no usable images or model."""
from __future__ import annotations

import base64
import datetime as dt
import io
import json
import os
import shutil
import stat
import sys
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import config

PRODUCT = "lipoma-imaging"
PUBLIC_KEY_FILE = Path(__file__).resolve().parent / "licence_public_key.pem"
VAULT_FILE = config.CURATED_DIR / "images.vault"
IMAGES_DIR = config.CURATED_DIR / "images"          # plain images: only on the developer's computer, never needed to run
CLOCK_FILE = config.ROOT / "outputs" / ".licence_clock"
VAULT_MAGIC = b"LIPOMA-VAULT-1\n"
MODEL_MAGIC = b"LIPOMA-MODEL-1\n"
BEGIN, END = "-----BEGIN LIPOMA LICENCE-----", "-----END LIPOMA LICENCE-----"
CONTACT = "Shahul Hameed.S - shahul@getwebsite.today"


class LicenceError(Exception):
    pass


@dataclass
class Licence:
    licence_id: str
    name: str
    email: str
    issued: dt.date
    expires: dt.date
    content_key: bytes

    @property
    def days_left(self) -> int:
        return (self.expires - dt.date.today()).days


# ---------------------------------------------------------------- licence files
def encode_licence(payload: dict, signature: bytes) -> str:
    body = base64.b64encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).decode()
    sig = base64.b64encode(signature).decode()
    wrap = lambda s: "\n".join(s[i:i + 64] for i in range(0, len(s), 64))  # noqa: E731
    return (f"{BEGIN}\nLicensed to: {payload['name']} <{payload['email']}>\nValid until: {payload['expires']}\n\n"
            f"{wrap(body)}\n.\n{wrap(sig)}\n{END}\n")


def decode_licence(text: str) -> tuple[dict, bytes, bytes]:
    """(payload, signed bytes, signature) from the text of a licence file."""
    try:
        inner = text.replace("\r\n", "\n").split(BEGIN, 1)[1].split(END, 1)[0]
        header, blocks = inner.strip().split("\n\n", 1)
        body, sig = blocks.split("\n.\n")
        signed = base64.b64decode("".join(body.split()))
        payload = json.loads(signed)
    except Exception as exc:
        raise LicenceError("The licence file is damaged or not a Lipoma Imaging licence.") from exc
    # the readable lines must match the signed data, so an edited date or name is rejected, not silently ignored
    expected = f"Licensed to: {payload.get('name')} <{payload.get('email')}>\nValid until: {payload.get('expires')}"
    if header.strip() != expected:
        raise LicenceError("The licence file is not valid: its name or date was changed. Use the original file you received. "
                           f"Contact {CONTACT}.")
    return payload, signed, base64.b64decode("".join(sig.split()))


def _check_clock(today: dt.date) -> None:
    """Refuse to run if the computer clock was set back to stretch a licence."""
    try:
        last = dt.date.fromisoformat(CLOCK_FILE.read_text().strip())
    except Exception:
        last = None
    if last and today < last - dt.timedelta(days=2):
        raise LicenceError(f"The computer date ({today}) is earlier than the last use ({last}). Correct the date and try again.")
    try:
        CLOCK_FILE.parent.mkdir(exist_ok=True)
        CLOCK_FILE.write_text(max(today, last or today).isoformat())
    except OSError:
        pass


def licence_files() -> list[Path]:
    """Candidate licence files: $LIPOMA_LICENCE, then every *.licence* file in the project folder."""
    env = os.environ.get("LIPOMA_LICENCE")
    found = ([Path(env)] if env else []) + sorted(config.ROOT.glob("*.licence*"))
    return list(dict.fromkeys(p for p in found if p.is_file()))


def _load_one(path: Path, today: dt.date) -> Licence:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    payload, signed, sig = decode_licence(path.read_text(encoding="utf-8", errors="replace"))
    try:
        load_pem_public_key(PUBLIC_KEY_FILE.read_bytes()).verify(sig, signed)
    except InvalidSignature as exc:
        raise LicenceError("The licence file is not valid (signature check failed). It may have been edited. "
                           f"Contact {CONTACT}.") from exc
    if payload.get("product") != PRODUCT:
        raise LicenceError("This licence is for another product.")
    lic = Licence(payload["licence_id"], payload["name"], payload["email"], dt.date.fromisoformat(payload["issued"]),
                  dt.date.fromisoformat(payload["expires"]), base64.b64decode(payload["content_key"]))
    if today < lic.issued - dt.timedelta(days=2):
        raise LicenceError(f"The licence starts on {lic.issued}; the computer date is {today}.")
    if today > lic.expires:
        raise LicenceError(f"The licence of {lic.name} expired on {lic.expires}. To renew it contact {CONTACT}.")
    return lic


def load_licence(path: Path | None = None) -> Licence:
    """Verified, unexpired licence, or LicenceError with a message for the user. Without `path` every licence
    file in the project folder is tried and the valid one that lasts longest is used."""
    today = dt.date.today()
    _check_clock(today)
    paths = [path] if path else licence_files()
    if not paths:
        raise LicenceError(f"No licence file found. Put the licence file you received (ending in .licence) in {config.ROOT}. "
                           f"To request a licence contact {CONTACT}.")
    valid, errors = [], []
    for p in paths:
        try:
            valid.append(_load_one(p, today))
        except LicenceError as exc:
            errors.append(exc)
    if not valid:
        raise errors[0]
    return max(valid, key=lambda lic: lic.expires)


# ---------------------------------------------------------------- encrypted dataset
_lock = threading.Lock()
_files: dict[str, bytes] | None = None
_key: bytes | None = None


def _content_key() -> bytes:
    global _key
    if _key is None:
        _key = load_licence().content_key
    return _key


def dataset_files() -> dict[str, bytes]:
    """All curated images, decrypted into memory: {"images/<location>/<file>.png": bytes}. Needs a valid licence."""
    global _files
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    with _lock:
        if _files is None:
            if not VAULT_FILE.exists():
                raise LicenceError(f"{VAULT_FILE.name} is missing - the project folder is incomplete.")
            data = VAULT_FILE.read_bytes()
            if not data.startswith(VAULT_MAGIC):
                raise LicenceError(f"{VAULT_FILE.name} is damaged.")
            nonce, ct = data[len(VAULT_MAGIC):len(VAULT_MAGIC) + 12], data[len(VAULT_MAGIC) + 12:]
            try:
                plain = AESGCM(_content_key()).decrypt(nonce, ct, VAULT_MAGIC)
            except InvalidTag as exc:
                raise LicenceError(f"This licence cannot open the dataset. Contact {CONTACT}.") from exc
            with zipfile.ZipFile(io.BytesIO(plain)) as z:
                _files = {f"images/{n}": z.read(n) for n in z.namelist() if not n.endswith("/")}
    return _files


def dataset_image(rel: str):
    """A curated image as a loaded PIL image; `rel` is the `file` column of metadata.csv (images/...)."""
    from PIL import Image
    im = Image.open(io.BytesIO(dataset_files()[str(rel).replace("\\", "/")]))
    im.load()
    return im


# ---------------------------------------------------------------- encrypted model
def save_model(obj, path: Path) -> None:
    import joblib
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    buf = io.BytesIO()
    joblib.dump(obj, buf, compress=3)
    nonce = os.urandom(12)
    Path(path).write_bytes(MODEL_MAGIC + nonce + AESGCM(_content_key()).encrypt(nonce, buf.getvalue(), MODEL_MAGIC))


def load_model(path: Path):
    import joblib
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    data = Path(path).read_bytes()
    if not data.startswith(MODEL_MAGIC):
        raise LicenceError("The saved model is not in the encrypted format - it will be rebuilt.")
    nonce, ct = data[len(MODEL_MAGIC):len(MODEL_MAGIC) + 12], data[len(MODEL_MAGIC) + 12:]
    try:
        return joblib.load(io.BytesIO(AESGCM(_content_key()).decrypt(nonce, ct, MODEL_MAGIC)))
    except InvalidTag as exc:
        raise LicenceError("The saved model belongs to another licence key - it will be rebuilt.") from exc


def extract_plain() -> int:
    """Write the curated images, read-only, to dataset_curated/images/ for the time the platform runs."""
    remove_plain()
    n = 0
    for rel, data in dataset_files().items():
        dest = config.CURATED_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        os.chmod(dest, stat.S_IREAD)
        n += 1
    return n


_remove_lock = threading.Lock()


def remove_plain() -> None:
    """Delete dataset_curated/images/ (also read-only files, also leftovers of a run that was killed).
    Safe to call from several threads at once (normal shutdown and the Windows console-close handler)."""
    def _unlock(func, path, exc):
        if isinstance(exc[1], FileNotFoundError) if isinstance(exc, tuple) else isinstance(exc, FileNotFoundError):
            return
        os.chmod(path, stat.S_IWRITE)
        func(path)
    with _remove_lock:
        for _ in range(3):
            if not (IMAGES_DIR.exists() and VAULT_FILE.exists()):    # never delete images when there is no vault copy
                return
            try:
                if sys.version_info >= (3, 12):
                    shutil.rmtree(IMAGES_DIR, onexc=lambda f, p, e: _unlock(f, p, e))
                else:
                    shutil.rmtree(IMAGES_DIR, onerror=_unlock)
            except OSError:
                pass


def lock_local_copy() -> None:
    """Remove the trained model (and any plain copy of the images) - used when the licence is no longer valid."""
    if VAULT_FILE.exists():                       # never delete the only copy of the images
        remove_plain()
        shutil.rmtree(config.ARTIFACT_DIR, ignore_errors=True)
