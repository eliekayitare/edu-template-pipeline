from edupipe import pipeline


def test_pipeline_writes_all_outputs(submissions, tmp_path):
    res = pipeline.run(submissions, tmp_path)
    for f in ["consolidated_long.csv", "consolidated_indicators.csv", "qc_summary.xlsx", "index.html"]:
        assert (tmp_path / f).exists(), f
    assert len(list((tmp_path / "qc").glob("*_qc.xlsx"))) == 12
    assert len(list((tmp_path / "reports").glob("*_review.html"))) == 12
    assert set(res["summary"].status) == {"clean", "errors", "warnings"}
