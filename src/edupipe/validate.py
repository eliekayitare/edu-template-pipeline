"""Rule-based validation. Each rule type is one small function; rules and
thresholds come from config/validation_rules.yaml."""
from __future__ import annotations

from typing import Callable

import pandas as pd

from .indicators import recalc_ger
from .spec import TemplateSpec

ISSUE_COLS = ["country", "rule_id", "severity", "cell", "level", "sex", "age", "year",
              "value", "expected", "message"]
CHECKS: dict[str, Callable] = {}


def check(kind: str):
    def deco(fn):
        CHECKS[kind] = fn
        return fn
    return deco


def _issue(rule, msg, **kw) -> dict:
    d = {c: None for c in ISSUE_COLS}
    d.update(rule_id=rule["id"], severity=rule["severity"], message=msg, **kw)
    return d


@check("metadata_required")
def _meta(rule, data, metas, spec):
    for iso, meta in metas.items():
        for f in spec.metadata_fields:
            if meta.get(f) in (None, ""):
                yield _issue(rule, f"Metadata field '{f}' is empty.", country=iso, cell="Metadata")


@check("non_negative")
def _nonneg(rule, data, metas, spec):
    d = data[data.table.isin(["enrolment", "population", "age"]) & (data.value < 0)]
    for r in d.itertuples():
        yield _issue(rule, f"Negative {r.table} value.", country=r.country, cell=r.cell, level=r.level,
                     sex=r.sex, age=r.age, year=r.year, value=r.value)


@check("sex_total")
def _sex(rule, data, metas, spec):
    tol = rule.get("tolerance", 0)
    for table in ("enrolment", "population"):
        d = data[data.table == table]
        w = d.pivot_table(index=["country", "level", "year"], columns="sex", values="value", aggfunc="first")
        cells = d[d.sex == "Total"].set_index(["country", "level", "year"])["cell"]
        bad = w[(w["Total"] - (w["Female"] + w["Male"])).abs() > tol]
        for (iso, lv, y), r in bad.iterrows():
            yield _issue(rule, f"{table.title()} total ({r.Total:,.0f}) is not Female + Male "
                         f"({r.Female + r.Male:,.0f}).", country=iso, cell=cells.get((iso, lv, y)),
                         level=lv, sex="Total", year=y, value=r.Total, expected=r.Female + r.Male)


@check("age_total")
def _age(rule, data, metas, spec):
    tol = rule.get("tolerance", 0)
    lvname = spec.level(spec.age_detail_level).name
    ages = data[(data.table == "age") & data.age.isin(spec.age_detail_ages)]
    sums = ages.groupby(["country", "year"])["value"].sum()
    tot = data[(data.table == "enrolment") & (data.level == lvname) & (data.sex == "Total")]
    for r in tot.itertuples():
        s = sums.get((r.country, r.year))
        if s is not None and abs(s - r.value) > tol:
            yield _issue(rule, f"Single-age primary enrolment sums to {s:,.0f} but total primary "
                         f"enrolment is {r.value:,.0f}.", country=r.country, cell=r.cell, level=lvname,
                         sex="Total", year=r.year, value=s, expected=r.value)


@check("year_on_year")
def _yoy(rule, data, metas, spec):
    lim = rule["max_relative_change"]
    d = data[data.table == "enrolment"].sort_values("year")
    for (iso, lv, sex), g in d.groupby(["country", "level", "sex"]):
        prev = None
        for r in g.itertuples():
            if prev is not None and prev.value and r.value is not None:
                ch = r.value / prev.value - 1
                if abs(ch) > lim:
                    yield _issue(rule, f"Enrolment changed by {ch:+.0%} from {prev.year} to {r.year}.",
                                 country=iso, cell=r.cell, level=lv, sex=sex, year=r.year,
                                 value=r.value, expected=prev.value)
            prev = r


@check("age_cohort")
def _cohort(rule, data, metas, spec):
    official = spec.level(spec.age_detail_level).ages
    d = data[(data.table == "age")].set_index(["country", "age", "year"])
    for (iso, age, year), r in d.iterrows():
        if age not in official[:-1] or (iso, age + 1, year + 1) not in d.index:
            continue
        nxt = d.loc[(iso, age + 1, year + 1)]
        if r.value and nxt.value is not None:
            ratio = nxt.value / r.value
            if not rule["min_ratio"] <= ratio <= rule["max_ratio"]:
                yield _issue(rule, f"Cohort ratio {ratio:.2f}: age {age} in {year} ({r.value:,.0f}) vs "
                             f"age {age + 1} in {year + 1} ({nxt.value:,.0f}).", country=iso,
                             cell=nxt.cell, age=age + 1, year=year + 1, value=nxt.value, expected=r.value)


@check("indicator_range")
def _range(rule, data, metas, spec):
    g = recalc_ger(data)
    bad = g[(g.ger_reported < rule["min"]) | (g.ger_reported > rule["max"])]
    for r in bad.itertuples():
        yield _issue(rule, f"Reported GER {r.ger_reported:.1f} is outside {rule['min']}-{rule['max']}.",
                     country=r.country, cell=r.ger_cell, level=r.level, sex=r.sex, year=r.year,
                     value=r.ger_reported)


@check("indicator_recalc")
def _recalc(rule, data, metas, spec):
    g = recalc_ger(data).dropna(subset=["ger_reported", "ger_recalc"])
    bad = g[(g.ger_reported - g.ger_recalc).abs() > rule["tolerance"]]
    for r in bad.itertuples():
        yield _issue(rule, f"Reported GER {r.ger_reported:.1f} but recalculated GER is {r.ger_recalc:.1f}.",
                     country=r.country, cell=r.ger_cell, level=r.level, sex=r.sex, year=r.year,
                     value=r.ger_reported, expected=r.ger_recalc)


def validate(data: pd.DataFrame, metas: dict, spec: TemplateSpec, rules: list[dict]) -> pd.DataFrame:
    issues = []
    for rule in rules:
        if rule["type"] not in CHECKS:
            raise ValueError(f"Unknown rule type {rule['type']!r} in rule {rule['id']}")
        issues.extend(CHECKS[rule["type"]](rule, data, metas, spec))
    return pd.DataFrame(issues, columns=ISSUE_COLS)
