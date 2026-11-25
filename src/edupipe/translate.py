"""Generate language versions of a template from one string table.

Every language version is produced from the English master, so the
structure (cells, formulas, validation) is identical across languages.
Untranslated strings are reported instead of silently left in English.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from openpyxl import load_workbook

from .spec import CONFIG

LANGS = ["fr", "es", "pt", "ru"]


def load_strings(path: Path | str = CONFIG / "translations.csv") -> dict[str, dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return {row["en"]: row for row in csv.DictReader(f)}


def _rename_refs(formula: str, renames: dict[str, str]) -> str:
    for old in sorted(renames, key=len, reverse=True):
        new = renames[old].replace("'", "''")
        formula = re.sub(rf"(?<![\w']){re.escape(old)}!|'{re.escape(old)}'!", f"'{new}'!", formula)
    return formula


def translate_template(src: Path | str, lang: str, dst: Path | str,
                       strings: dict | None = None) -> list[str]:
    """Write the `lang` version of `src` to `dst`. Returns untranslated strings."""
    strings = strings or load_strings()
    wb = load_workbook(src)
    renames = {ws.title: strings[ws.title][lang] for ws in wb.worksheets if ws.title in strings}
    missing: set[str] = set()
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if isinstance(v, str) and v.startswith("="):
                    c.value = _rename_refs(v, renames)
                elif isinstance(v, str) and v.strip():
                    if v in strings and strings[v].get(lang):
                        c.value = strings[v][lang]
                    elif not re.fullmatch(r"[\d.\-]+", v):
                        missing.add(v)
    for ws in wb.worksheets:
        if ws.title in renames:
            ws.title = renames[ws.title][:31]
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    wb.save(dst)
    return sorted(missing)
