from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .paths import CONFIG_DIR


def load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def load_field_mapping() -> dict[str, list[str]]:
    raw = load_yaml("field_mapping.yaml")
    return {str(key): [str(item) for item in value] for key, value in raw.items()}


def load_slug_overrides() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    raw = load_yaml("school_aliases.yaml")
    slug_overrides = {
        str(key): [str(item) for item in value]
        for key, value in (raw.get("slug_overrides") or {}).items()
    }
    aliases = {
        str(key): [str(item) for item in value]
        for key, value in (raw.get("aliases") or {}).items()
    }
    return slug_overrides, aliases


def load_campus_address_overrides() -> dict[str, dict[str, str]]:
    raw = load_yaml("campus_address_overrides.yaml")
    return {
        str(school): {
            "campus_addresses": str(value.get("campus_addresses", "")),
            "source": str(value.get("source", "")),
        }
        for school, value in raw.items()
        if isinstance(value, dict)
    }
