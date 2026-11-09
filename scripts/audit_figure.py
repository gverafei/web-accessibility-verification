"""Plot interface judgments conditional on audit scores and word retention."""

import csv
import json
import os
from pathlib import Path

from core import ROOT

os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "runtime/matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from chart_style import EDGES, FILL, apply, finish


def audit_context_counts(rows):
    """Count decisions in the declared nested descriptive subsets."""
    favorable = [
        row
        for row in rows
        if row["category"] != "acquired"
        and row.get("metrics", {}).get("axe", float("inf")) <= 5
        and row.get("metrics", {}).get("lighthouse", 0) >= 95
    ]
    low_retention = [
        row for row in favorable if row.get("metrics", {}).get("text_percent", 100) < 80
    ]
    summaries = []
    for name, selected, outcome in (
        ("favorable_audits", favorable, "not_accepted"),
        ("favorable_audits_low_word_retention", low_retention, "accepted"),
    ):
        for field, assessor in (
            ("decisions_label", "Luna Decisions"),
            ("r1", "Reviewer 1"),
            ("r2", "Reviewer 2"),
        ):
            count = sum(row[field] == outcome for row in selected)
            summaries.append(
                {
                    "subset": name,
                    "assessor": assessor,
                    "outcome": outcome,
                    "count": count,
                    "denominator": len(selected),
                    "percent": 100 * count / len(selected) if selected else 0,
                }
            )
    return summaries


def draw_audit_context(rows, output_dir):
    """Export Figure 9 and the six data rows used to generate it."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = audit_context_counts(rows)
    apply()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.3), layout="constrained")
    for axis, selected, title, subtitle, xlabel, ticks in (
        (
            axes[0],
            summaries[:3],
            "A  Rejected despite favorable audits",
            "Axe ≤ 5 and Lighthouse ≥ 95",
            "Rejected pages (n)",
            [0, 10, 20, 30, 40],
        ),
        (
            axes[1],
            summaries[3:],
            "B  Admitted despite low word retention",
            "Same audit limits; word retention <80%",
            "Admitted pages (n)",
            [0, 50, 100, 150],
        ),
    ):
        maximum = max(row["count"] for row in selected)
        limit = max(1, maximum * 1.43)
        for position, row in enumerate(selected):
            axis.barh(
                position,
                row["count"],
                height=0.36,
                color=FILL[position],
                edgecolor=EDGES[position],
                linewidth=0.7,
            )
            axis.text(
                row["count"] + limit * 0.025,
                position,
                f"{row['count']} · {row['percent']:.1f}%",
                va="center",
                fontsize=6.5,
            )
        axis.set_yticks(range(3), [row["assessor"] for row in selected])
        axis.set_ylim(2.5, -0.7)
        axis.set_xlim(0, limit)
        axis.set_xticks(ticks)
        axis.set_title(title, loc="left", fontsize=8, pad=28)
        axis.text(
            0,
            1.035,
            f"{subtitle}\nn = {selected[0]['denominator']}",
            transform=axis.transAxes,
            fontsize=6.7,
            va="bottom",
            color="#526777",
        )
        finish(axis, xlabel)
    for extension in ("png",):
        fig.savefig(
            output_dir / f"audit_interface_comparison.{extension}",
            dpi=1200,
            facecolor="white",
            bbox_inches="tight",
        )
    plt.close(fig)
    with (output_dir / "audit_interface_comparison.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    return summaries


if __name__ == "__main__":
    from publication_data import records

    print(json.dumps(draw_audit_context(records(), ROOT / "analysis"), indent=2))
