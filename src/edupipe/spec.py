"""Template specification: one place that describes the workbook layout."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"

# Sheet names and where the first year column sits on each sheet (1-based).
SHEET_META = "Metadata"
SHEET_ENROL = "Enrolment"
SHEET_POP = "Population"
SHEET_AGE = "Enrolment by age"
SHEET_IND = "Indicators"
HEADER_ROW = 3
FIRST_DATA_ROW = 4
FIRST_YEAR_COL = {SHEET_ENROL: 3, SHEET_POP: 3, SHEET_AGE: 2, SHEET_IND: 4}


@dataclass
class Level:
    code: str
    name: str
    ages: list[int]


@dataclass
class TemplateSpec:
    template_version: str
    years: list[int]
    sexes: list[str]
    levels: list[Level]
    age_detail_level: str
    age_detail_ages: list[int]
    metadata_fields: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | str = CONFIG / "template_spec.yaml") -> "TemplateSpec":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        raw["levels"] = [Level(**lv) for lv in raw["levels"]]
        return cls(**raw)

    def level(self, code: str) -> Level:
        return next(lv for lv in self.levels if lv.code == code)

    def level_by_name(self, name: str) -> Level:
        return next(lv for lv in self.levels if lv.name == name)


def load_rules(path: Path | str = CONFIG / "validation_rules.yaml") -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["rules"]
