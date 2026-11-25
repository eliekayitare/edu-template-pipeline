import pytest
from openpyxl import load_workbook

from edupipe.translate import LANGS, translate_template


@pytest.mark.parametrize("lang", LANGS)
def test_every_string_translated(template, tmp_path, lang):
    missing = translate_template(template, lang, tmp_path / f"t_{lang}.xlsx")
    assert missing == []


def test_formulas_follow_renamed_sheets(template, tmp_path):
    out = tmp_path / "t_fr.xlsx"
    translate_template(template, "fr", out)
    wb = load_workbook(out)
    assert wb.sheetnames == ["Métadonnées", "Effectifs", "Population", "Effectifs par âge", "Indicateurs"]
    f = wb["Indicateurs"]["D4"].value
    assert "'Effectifs'!C4" in f and "'Population'!C4" in f
