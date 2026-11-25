"""Point-and-click front end: upload filled templates, see QC results, download outputs.

Run with:  pip install -e .[app]  &&  streamlit run app/streamlit_app.py
"""
import io
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from edupipe.extract import extract_folder
from edupipe.indicators import recalc_ger
from edupipe.report import country_status
from edupipe.spec import TemplateSpec, load_rules
from edupipe.validate import validate

st.set_page_config(page_title="Template QC", layout="wide")
st.title("Education survey template QC")
st.caption("Upload filled templates (.xlsx). Synthetic demonstration tool; not an official UNESCO/UIS system.")

files = st.file_uploader("Country submissions", type="xlsx", accept_multiple_files=True)
if files:
    with tempfile.TemporaryDirectory() as tmp:
        for f in files:
            Path(tmp, Path(f.name).name).write_bytes(f.getbuffer())
        metas, data = extract_folder(tmp)
    spec, rules = TemplateSpec.load(), load_rules()
    issues = validate(data, metas, spec, rules)
    summary = pd.DataFrame([{"country": iso, "name": m.get("Country name"),
                             "errors": int(((issues.country == iso) & (issues.severity == "error")).sum()),
                             "warnings": int(((issues.country == iso) & (issues.severity == "warning")).sum()),
                             "status": country_status(issues, iso)} for iso, m in metas.items()])
    c1, c2, c3 = st.columns(3)
    c1.metric("Submissions", len(summary))
    c2.metric("With errors", int((summary.status == "errors").sum()))
    c3.metric("Clean", int((summary.status == "clean").sum()))
    st.subheader("Summary")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    iso = st.selectbox("Country", list(metas))
    st.subheader(f"Issues: {iso}")
    st.dataframe(issues[issues.country == iso].drop(columns="country"), use_container_width=True,
                 hide_index=True)
    ger = recalc_ger(data)
    g = ger[(ger.country == iso) & (ger.sex == "Total")].pivot(index="year", columns="level",
                                                                values="ger_recalc")
    st.subheader("Gross enrolment ratio, both sexes (recalculated)")
    st.line_chart(g)

    buf = io.StringIO()
    data.to_csv(buf, index=False)
    st.download_button("Download consolidated data (CSV)", buf.getvalue(), "consolidated_long.csv")
    buf = io.StringIO()
    issues.to_csv(buf, index=False)
    st.download_button("Download all issues (CSV)", buf.getvalue(), "qc_issues_all.csv")
