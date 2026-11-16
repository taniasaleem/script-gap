"""Shared constants, paths and JSONL helpers."""
from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "items.jsonl"
RUNS_DIR = ROOT / "results" / "runs"
SCORES_DIR = ROOT / "results" / "scores"
OUT_DIR = ROOT / "results"
CONFIG = ROOT / "config.toml"

TASK_TYPES = ("factual", "instruction", "reasoning", "abstention")
SCRIPTS = ("english", "nastaliq", "roman_urdu")

# Reply-language codes a scorer assigns to each response (see RUBRIC.md).
REPLY_LANGS = {
    "e": "english",
    "n": "nastaliq",
    "r": "roman_urdu",
    "m": "mixed",
    "x": "none",  # empty, refused, or error
}


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{n}: invalid JSON ({e})")
    return rows


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_config(path: Path = CONFIG) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def arabic_ratio(text: str) -> float:
    """Share of letters that are in the Arabic-script Unicode blocks."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    arabic = sum(
        1 for c in letters
        if "؀" <= c <= "ۿ" or "ݐ" <= c <= "ݿ"
        or "ﭐ" <= c <= "﷿" or "ﹰ" <= c <= "﻿"
    )
    return arabic / len(letters)


# Very common Roman Urdu function words. Only used to *suggest* a reply
# language to the scorer, who always confirms or overrides it.
_ROMAN_URDU_MARKERS = {
    "hai", "hain", "ka", "ki", "ke", "ko", "se", "mein", "main", "nahi",
    "nahin", "aur", "kya", "ye", "yeh", "woh", "wo", "tha", "thi", "thay",
    "hota", "hoti", "hum", "aap", "ap", "kar", "karna", "liye", "lekin",
    "agar", "jo", "bhi", "sirf", "kyun", "kyunke", "gaya", "gayi",
}


def suggest_reply_lang(text: str) -> str:
    """Heuristic guess at the reply language code. Never final."""
    if not text or not text.strip():
        return "x"
    ar = arabic_ratio(text)
    if ar > 0.85:
        return "n"
    if ar > 0.15:
        return "m"
    words = [w.strip(".,!?;:()\"'*-").lower() for w in text.split()]
    words = [w for w in words if w]
    if not words:
        return "x"
    share = sum(w in _ROMAN_URDU_MARKERS for w in words) / len(words)
    if share > 0.08:
        return "r"
    return "e"
