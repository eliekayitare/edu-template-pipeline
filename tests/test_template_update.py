from openpyxl import load_workbook

from edupipe.spec import HEADER_ROW
from edupipe.update import add_year


def test_add_year_extends_headers_and_formulas(template, tmp_path, spec):
    out = tmp_path / "next.xlsx"
    log = add_year(template, out, new_version="2027.1")
    wb = load_workbook(out)
    enr = wb["Enrolment"]
    new_col = 3 + len(spec.years)                        # one column after the last year
    assert enr.cell(HEADER_ROW, new_col).value == spec.years[-1] + 1
    assert enr["H6"].value == "=H4+H5"                    # Total = Female + Male, shifted
    ind = wb["Indicators"]
    assert ind["I4"].value == '=IF(Population!H4=0,"",Enrolment!H4/Population!H4*100)'
    assert log["Indicators"]["formulas_added"] == 9


def test_add_year_extends_data_validation(template, tmp_path):
    out = tmp_path / "next.xlsx"
    add_year(template, out)
    dv = load_workbook(out)["Enrolment"].data_validations.dataValidation[0]
    assert "H4" in dv.sqref and "H6" not in dv.sqref     # inputs only, not the Total row


def test_add_year_updates_version(template, tmp_path):
    out = tmp_path / "next.xlsx"
    add_year(template, out, new_version="2027.1")
    meta = load_workbook(out)["Metadata"]
    assert "2027.1" in [c.value for c in meta["B"]]
