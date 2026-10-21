"""Knowledge-base look-ups (educational text per lipoma location)."""
from __future__ import annotations

import json
from functools import lru_cache

from . import config


@lru_cache(maxsize=1)
def load_kb() -> dict:
    with open(config.KNOWLEDGE_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def class_info(label: str) -> dict:
    return load_kb()["classes"].get(label, {})


def general_info() -> dict:
    return load_kb()["general"]
