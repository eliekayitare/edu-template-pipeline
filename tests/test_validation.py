import pandas as pd

from edupipe.extract import extract_folder
from edupipe.indicators import recalc_ger
from edupipe.simulate import INJECTED
from edupipe.validate import validate

EXPECTED_RULE = {
    "sex_total": "SEX_SUM", "missing_meta": "META_REQUIRED", "age_total": "AGE_SUM",
    "yoy_spike": "YOY_CHANGE", "ger_typo": "GER_RECALC", "negative": "NON_NEGATIVE",
    "cohort": "AGE_COHORT",
}


def _issues(submissions, spec, rules):
    metas, data = extract_folder(submissions)
    return metas, data, validate(data, metas, spec, rules)


def test_every_injected_error_is_found(submissions, spec, rules):
    _, _, issues = _issues(submissions, spec, rules)
    for iso, problem in INJECTED.items():
        found = set(issues.loc[issues.country == iso, "rule_id"])
        assert EXPECTED_RULE[problem] in found, (iso, problem, found)


def test_clean_submissions_have_no_issues(submissions, spec, rules):
    metas, _, issues = _issues(submissions, spec, rules)
    clean = set(metas) - set(INJECTED)
    assert clean and issues[issues.country.isin(clean)].empty


def test_issues_point_to_cells(submissions, spec, rules):
    _, _, issues = _issues(submissions, spec, rules)
    assert issues["cell"].notna().all()


def test_recalculated_ger_matches_reported_for_clean_data(submissions):
    _, data = extract_folder(submissions)
    g = recalc_ger(data)
    g = g[g.country == "XAU"]
    assert ((g.ger_reported - g.ger_recalc).abs() <= 0.06).all()


def test_extraction_is_complete(submissions, spec):
    metas, data = extract_folder(submissions)
    assert len(metas) == 12
    per_country = data.groupby("country").size()
    n_rows = len(spec.levels) * len(spec.sexes)
    expected = len(spec.years) * (3 * n_rows + len(spec.age_detail_ages) + 1)
    assert (per_country == expected).all()
    assert isinstance(data, pd.DataFrame)
