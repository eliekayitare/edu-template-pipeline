"""Outputs: per-country QC workbook and review report, cross-country summary,
consolidated database."""
from __future__ import annotations

import base64
import html
import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from openpyxl.styles import Font, PatternFill  # noqa: E402

SEV_FILL = {"error": "F8CBAD", "warning": "FFE699"}


def country_status(issues: pd.DataFrame, iso: str) -> str:
    sev = set(issues.loc[issues.country == iso, "severity"])
    return "errors" if "error" in sev else "warnings" if "warning" in sev else "clean"


def write_qc_workbook(iso: str, issues: pd.DataFrame, rules: list[dict], path: Path) -> None:
    mine = issues[issues.country == iso].drop(columns=["country"])
    checklist = pd.DataFrame([{
        "Rule": r["id"], "Severity": r["severity"], "Description": r["description"],
        "Issues found": int((mine.rule_id == r["id"]).sum()),
        "Status": "PASS" if not (mine.rule_id == r["id"]).any() else "FAIL",
        "Resolved with country (Y/N)": "", "Comment": ""} for r in rules])
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        checklist.to_excel(xw, "Checklist", index=False)
        mine.to_excel(xw, "Issues", index=False)
        for ws in xw.book.worksheets:
            for c in ws[1]:
                c.font = Font(bold=True)
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(
                    60, max(10, *(len(str(c.value or "")) for c in col)) + 2)
        ws = xw.book["Issues"]
        sev_col = list(mine.columns).index("severity") + 1
        for row in ws.iter_rows(min_row=2):
            fill = SEV_FILL.get(row[sev_col - 1].value)
            if fill:
                for c in row:
                    c.fill = PatternFill("solid", fgColor=fill)


def _chart(ger: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=110)
    for lv, g in ger[ger.sex == "Total"].groupby("level", sort=False):
        ax.plot(g.year, g.ger_recalc, marker="o", label=lv)
    ax.set_ylabel("GER (%)")
    ax.set_xticks(sorted(ger.year.unique()))
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Gross enrolment ratio, both sexes (recalculated)", fontsize=10)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


CSS = """body{font-family:Segoe UI,Arial,sans-serif;margin:32px;color:#222;max-width:1000px}
h1{color:#1F4E79}table{border-collapse:collapse;font-size:13px;margin:8px 0 20px}
td,th{border:1px solid #ccc;padding:4px 8px;text-align:right}th{background:#DCE6F1}
td:first-child,th:first-child{text-align:left}.error{background:#F8CBAD}.warning{background:#FFE699}
.badge{padding:3px 10px;border-radius:10px;font-weight:600}.clean{background:#C6EFCE}
.note{color:#777;font-size:12px}"""


def write_country_report(iso: str, meta: dict, ger: pd.DataFrame, issues: pd.DataFrame, path: Path) -> None:
    g = ger[ger.country == iso]
    mine = issues[issues.country == iso]
    status = country_status(issues, iso)
    pivot = g.pivot_table(index=["level", "sex"], columns="year", values="ger_recalc", sort=False).round(1)
    rows = "".join(f"<tr><td>{html.escape(lv)} — {sex}</td>" + "".join(
        f"<td>{v:.1f}</td>" if pd.notna(v) else "<td>–</td>" for v in r) + "</tr>"
        for (lv, sex), r in pivot.iterrows())
    head = "".join(f"<th>{y}</th>" for y in pivot.columns)
    irows = "".join(f"<tr class='{r.severity}'><td>{r.rule_id}</td><td>{r.severity}</td>"
                    f"<td>{html.escape(str(r.cell or ''))}</td><td style='text-align:left'>"
                    f"{html.escape(r.message)}</td></tr>" for r in mine.itertuples()) \
        or "<tr><td colspan=4>No issues found.</td></tr>"
    doc = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{iso} indicator review</title>
<style>{CSS}</style></head><body>
<h1>Country indicator review: {html.escape(str(meta.get('Country name')))} ({iso})</h1>
<p>Reference year {meta.get('Reference year')} · Source: {html.escape(str(meta.get('Data source')))} ·
QC status: <span class="badge {status}">{status.upper()}</span></p>
<h2>Gross enrolment ratio (%)</h2>
<table><tr><th>Level — sex</th>{head}</tr>{rows}</table>
<img src="data:image/png;base64,{_chart(g)}" alt="GER chart">
<h2>Validation issues ({len(mine)})</h2>
<table><tr><th>Rule</th><th>Severity</th><th>Cell</th><th>Message</th></tr>{irows}</table>
<p class="note">Synthetic data generated for demonstration. Not official statistics.</p>
</body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")


def write_index(metas: dict, issues: pd.DataFrame, path: Path) -> pd.DataFrame:
    summ = pd.DataFrame([{
        "country": iso, "name": m.get("Country name"),
        "errors": int(((issues.country == iso) & (issues.severity == "error")).sum()),
        "warnings": int(((issues.country == iso) & (issues.severity == "warning")).sum()),
        "status": country_status(issues, iso)} for iso, m in metas.items()])
    rows = "".join(f"<tr><td><a href='reports/{r.country}_review.html'>{r.country}</a></td>"
                   f"<td>{html.escape(str(r.name))}</td><td>{r.errors}</td><td>{r.warnings}</td>"
                   f"<td><span class='badge {r.status}'>{r.status}</span></td></tr>"
                   for r in summ.itertuples())
    path.write_text(f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>QC summary</title>
<style>{CSS}</style></head><body><h1>Submission QC summary</h1>
<p>{len(summ)} submissions · {int((summ.status == 'clean').sum())} clean ·
{int((summ.status == 'errors').sum())} with errors</p>
<table><tr><th>Code</th><th>Country</th><th>Errors</th><th>Warnings</th><th>Status</th></tr>{rows}</table>
<p class="note">Synthetic data generated for demonstration. Not official statistics.</p></body></html>""",
                    encoding="utf-8")
    return summ
