"""End-to-end processing of a folder of submissions."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .extract import extract_folder
from .indicators import recalc_ger
from .report import country_status, write_country_report, write_index, write_qc_workbook
from .spec import TemplateSpec, load_rules
from .validate import validate

log = logging.getLogger("edupipe")


def run(indir: Path | str, outdir: Path | str, spec: TemplateSpec | None = None,
        rules: list[dict] | None = None) -> dict:
    spec, rules = spec or TemplateSpec.load(), rules or load_rules()
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    metas, data = extract_folder(indir)
    log.info("Extracted %d values from %d submissions", len(data), len(metas))
    issues = validate(data, metas, spec, rules)
    ger = recalc_ger(data)
    for iso, meta in metas.items():
        write_qc_workbook(iso, issues, rules, outdir / "qc" / f"{iso}_qc.xlsx")
        write_country_report(iso, meta, ger, issues, outdir / "reports" / f"{iso}_review.html")
    summary = write_index(metas, issues, outdir / "index.html")
    status = {iso: country_status(issues, iso) for iso in metas}
    data = data.assign(qc_status=data.country.map(status))
    data.to_csv(outdir / "consolidated_long.csv", index=False)
    ger.assign(qc_status=ger.country.map(status)).to_csv(outdir / "consolidated_indicators.csv", index=False)
    issues.to_csv(outdir / "qc_issues_all.csv", index=False)
    with pd.ExcelWriter(outdir / "qc_summary.xlsx", engine="openpyxl") as xw:
        summary.to_excel(xw, "Summary", index=False)
        issues.to_excel(xw, "All issues", index=False)
    log.info("Issues: %d errors, %d warnings", (issues.severity == "error").sum(),
             (issues.severity == "warning").sum())
    return {"metas": metas, "data": data, "issues": issues, "summary": summary}
