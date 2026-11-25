"""Independent recalculation of indicators from the raw data."""
from __future__ import annotations

import pandas as pd


def recalc_ger(data: pd.DataFrame) -> pd.DataFrame:
    """Gross enrolment ratio = enrolment / school-age population x 100, per country/level/sex/year."""
    keys = ["country", "level", "sex", "year"]
    enr = data[data.table == "enrolment"].set_index(keys)["value"]
    pop = data[data.table == "population"].set_index(keys)["value"]
    df = pd.concat({"enrolment": enr, "population": pop}, axis=1).reset_index()
    ok = df.population.notna() & (df.population > 0) & df.enrolment.notna()
    df["ger_recalc"] = None
    df.loc[ok, "ger_recalc"] = (df.loc[ok, "enrolment"] / df.loc[ok, "population"] * 100).round(2)
    rep = data[(data.table == "indicator") & (data.indicator == "GER")][keys + ["value", "cell"]]
    rep = rep.rename(columns={"value": "ger_reported", "cell": "ger_cell"})
    out = df.merge(rep, on=keys, how="left")
    out["ger_recalc"] = pd.to_numeric(out["ger_recalc"])
    return out
