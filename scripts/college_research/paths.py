from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = PROJECT_ROOT / "input"
WORK_DIR = PROJECT_ROOT / "work"
OUTPUT_DIR = PROJECT_ROOT / "output"
CONFIG_DIR = PROJECT_ROOT / "config"
CACHE_DIR = PROJECT_ROOT / "cache"


def ensure_dirs() -> None:
    for path in [INPUT_DIR, WORK_DIR, OUTPUT_DIR, CACHE_DIR]:
        path.mkdir(parents=True, exist_ok=True)
