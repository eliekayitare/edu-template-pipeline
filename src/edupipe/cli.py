"""Command-line interface: python -m edupipe <command> ..."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from . import pipeline
from .simulate import simulate
from .spec import TemplateSpec
from .template import build_template
from .translate import LANGS, translate_template
from .update import add_year


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="edupipe", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("build", help="build the blank template")
    s.add_argument("--out", default="templates/template_en.xlsx")
    s = sub.add_parser("add-year", help="roll a template forward by one year")
    s.add_argument("src"), s.add_argument("dst"), s.add_argument("--version")
    s = sub.add_parser("translate", help="generate FR/ES/PT/RU versions")
    s.add_argument("src"), s.add_argument("--outdir", default="templates")
    s = sub.add_parser("simulate", help="generate synthetic country submissions")
    s.add_argument("--outdir", default="data/submissions"), s.add_argument("--n", type=int, default=12)
    s = sub.add_parser("run", help="validate and consolidate a folder of submissions")
    s.add_argument("--indir", default="data/submissions"), s.add_argument("--outdir", default="output")
    sub.add_parser("demo", help="build, update, translate, simulate and run everything")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    spec = TemplateSpec.load()

    if a.cmd in ("build", "demo"):
        out = build_template(spec, getattr(a, "out", "templates/template_en.xlsx"))
        print(f"Template written: {out}")
    if a.cmd == "add-year":
        print(json.dumps(add_year(a.src, a.dst, a.version), indent=2))
    if a.cmd == "demo":
        log = add_year("templates/template_en.xlsx", "templates/template_en_next_year.xlsx", "2027.1")
        print("Added year:", json.dumps(log))
    if a.cmd in ("translate", "demo"):
        src = getattr(a, "src", "templates/template_en_next_year.xlsx")
        outdir = Path(getattr(a, "outdir", "templates") if a.cmd == "translate" else "templates")
        for lang in LANGS:
            dst = outdir / f"{Path(src).stem.replace('_en', '')}_{lang}.xlsx"
            missing = translate_template(src, lang, dst)
            print(f"{lang}: {dst}" + (f"  (untranslated: {missing})" if missing else ""))
    if a.cmd in ("simulate", "demo"):
        paths = simulate(spec, getattr(a, "outdir", "data/submissions") if a.cmd == "simulate"
                         else "data/submissions", getattr(a, "n", 12))
        print(f"{len(paths)} synthetic submissions written")
    if a.cmd in ("run", "demo"):
        res = pipeline.run(getattr(a, "indir", "data/submissions"), getattr(a, "outdir", "output"))
        print(res["summary"].to_string(index=False))


if __name__ == "__main__":
    main()
