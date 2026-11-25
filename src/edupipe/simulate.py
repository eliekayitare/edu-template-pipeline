"""Generate synthetic 'country submissions' (filled templates) for testing.

Countries are fictional. A few submissions contain deliberately injected
errors so the validation pipeline has something to find. Submitted files
store values (as a saved, filled-in workbook does), not formulas.
"""
from __future__ import annotations

import random
from pathlib import Path

from openpyxl import load_workbook

from .spec import (FIRST_DATA_ROW, FIRST_YEAR_COL, SHEET_AGE, SHEET_ENROL, SHEET_IND,
                   SHEET_META, SHEET_POP, TemplateSpec)
from .template import build_template, level_sex_rows

COUNTRIES = [
    ("XAU", "Aurelia"), ("XBR", "Borovia"), ("XCA", "Calderra"), ("XDE", "Delmora"),
    ("XEV", "Evandor"), ("XFA", "Farlands"), ("XGR", "Granholm"), ("XHE", "Hesperia"),
    ("XIS", "Islavia"), ("XJO", "Jorvik Isles"), ("XKA", "Karanta"), ("XLU", "Lumeria"),
]
GER_RANGE = {"L1": (0.97, 1.08), "L2": (0.70, 0.90), "L3": (0.40, 0.65)}
# Injected problems: country code -> problem key (see _inject)
INJECTED = {
    "XBR": "sex_total", "XCA": "missing_meta", "XDE": "age_total", "XEV": "yoy_spike",
    "XFA": "ger_typo", "XGR": "negative", "XHE": "cohort",
}


def _country_data(spec: TemplateSpec, rng: random.Random) -> dict:
    """Return pop[(level,sex,year)], enr[(level,sex,year)], age[(age,year)]."""
    pop, enr, age = {}, {}, {}
    growth = rng.uniform(1.005, 1.03)
    for lv in spec.levels:
        base = rng.randint(80_000, 900_000) * len(lv.ages) // 6
        ger = rng.uniform(*GER_RANGE[lv.code])
        fshare = rng.uniform(0.47, 0.51)
        for k, y in enumerate(spec.years):
            p_total = base * growth ** k
            g = ger * (1 + rng.uniform(-0.01, 0.015) * k)
            pf, pm = round(p_total * fshare), round(p_total * (1 - fshare))
            ef = round(pf * g * rng.uniform(0.98, 1.02))
            em = round(pm * g * rng.uniform(0.98, 1.02))
            pop.update({(lv.name, "Female", y): pf, (lv.name, "Male", y): pm,
                        (lv.name, "Total", y): pf + pm})
            enr.update({(lv.name, "Female", y): ef, (lv.name, "Male", y): em,
                        (lv.name, "Total", y): ef + em})
    # single-age primary enrolment: roughly flat across official ages, small under/over-age
    lv = spec.level(spec.age_detail_level)
    weights = {a: (0.02 if a < lv.ages[0] else 1.0 - 0.01 * (a - lv.ages[0]) if a in lv.ages
                   else 0.04 / (a - lv.ages[-1])) for a in spec.age_detail_ages}
    wsum = sum(weights.values())
    for y in spec.years:
        total = enr[(lv.name, "Total", y)]
        vals = {a: int(total * w / wsum) for a, w in weights.items()}
        vals[lv.ages[0]] += total - sum(vals.values())  # make the sum exact
        for a, v in vals.items():
            age[(a, y)] = v
    return {"pop": pop, "enr": enr, "age": age}


def _inject(problem: str, d: dict, meta: dict, spec: TemplateSpec) -> None:
    y = spec.years
    if problem == "sex_total":
        d["enr"][("Lower secondary", "Total", y[2])] += 1_250
    elif problem == "missing_meta":
        meta["Contact email"] = None
    elif problem == "age_total":
        d["age"][(9, y[3])] += 3_400
    elif problem == "yoy_spike":
        inc = int(d["enr"][("Upper secondary", "Female", y[3])] * 0.6)
        for s in ("Female", "Total"):
            d["enr"][("Upper secondary", s, y[3])] += inc
    elif problem == "negative":
        d["pop"][("Upper secondary", "Male", y[1])] *= -1
    elif problem == "cohort":   # move pupils between ages: totals stay right, cohort breaks
        moved = int(d["age"][(8, y[2])] * 0.35)
        d["age"][(8, y[2])] -= moved
        d["age"][(10, y[2])] += moved


def simulate(spec: TemplateSpec, outdir: Path | str, n: int = 12, seed: int = 2027) -> list[Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    blank = build_template(spec, outdir / "_blank.xlsx")
    rows = level_sex_rows(spec)
    paths = []
    for iso, name in COUNTRIES[:n]:
        rng = random.Random(f"{seed}-{iso}")
        d = _country_data(spec, rng)
        meta = {"Country code": iso, "Country name": name, "Reference year": spec.years[-1],
                "Reporting institution": f"Ministry of Education of {name}",
                "Contact email": f"stats@moe.{iso.lower()}.example", "Data source": "Annual school census"}
        if iso in INJECTED:
            _inject(INJECTED[iso], d, meta, spec)
        wb = load_workbook(blank)
        ws = wb[SHEET_META]
        for r in range(FIRST_DATA_ROW, ws.max_row + 1):
            if ws.cell(r, 1).value in meta:
                ws.cell(r, 2).value = meta[ws.cell(r, 1).value]
        for sheet, key in ((SHEET_ENROL, "enr"), (SHEET_POP, "pop")):
            ws = wb[sheet]
            for lv_name, sex, r in rows:
                for j, y in enumerate(spec.years):
                    ws.cell(r, FIRST_YEAR_COL[sheet] + j).value = d[key][(lv_name, sex, y)]
        ws = wb[SHEET_AGE]
        for i, a in enumerate(spec.age_detail_ages):
            for j, y in enumerate(spec.years):
                ws.cell(FIRST_DATA_ROW + i, FIRST_YEAR_COL[SHEET_AGE] + j).value = d["age"][(a, y)]
        tr = FIRST_DATA_ROW + len(spec.age_detail_ages)
        for j, y in enumerate(spec.years):   # value the country's workbook would have computed
            ws.cell(tr, FIRST_YEAR_COL[SHEET_AGE] + j).value = d["enr"][(spec.level(spec.age_detail_level).name, "Total", y)]
        ws = wb[SHEET_IND]
        for lv_name, sex, r in rows:
            for j, y in enumerate(spec.years):
                p = d["pop"][(lv_name, sex, y)]
                v = round(d["enr"][(lv_name, sex, y)] / p * 100, 1) if p else None
                if INJECTED.get(iso) == "ger_typo" and (lv_name, sex, y) == ("Primary", "Total", spec.years[-1]):
                    v = round(v * 10, 1)  # decimal-point slip
                ws.cell(r, FIRST_YEAR_COL[SHEET_IND] + j).value = v
        p = outdir / f"{iso}_submission_{spec.years[-1]}.xlsx"
        wb.save(p)
        paths.append(p)
    blank.unlink()
    return paths
