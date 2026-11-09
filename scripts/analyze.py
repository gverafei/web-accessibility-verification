"""Recompute final case-level statistics without network access."""

import argparse
import csv
import json
from pathlib import Path

from core import ROOT, cases
from analysis_tools import report
from case_metadata import generator, preparation

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=ROOT / "analysis")
args = parser.parse_args()
rows = cases()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
(out / "comparison.json").write_text(json.dumps(report(rows), indent=2))
with (out / "case-comparison.csv").open("w", newline="") as stream:
    fields = [
        "number",
        "case_id",
        "review_id",
        "url",
        "category",
        "page_preparation",
        "generating_model",
        "method",
        "model",
        "r1",
        "r2",
        "decisions_label",
        "luna_label",
    ]
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(
        {
            **row,
            "page_preparation": preparation(row),
            "generating_model": generator(row),
        }
        for row in rows
    )
print(
    f"Recomputed {len(rows)} final cases and {2 * len(rows):,} human responses: {out}"
)
