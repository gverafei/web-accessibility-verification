"""Generate the verification-resource figure from final case records."""

import csv
import json
import os
import statistics
from pathlib import Path

from core import ROOT

os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "runtime/matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from chart_style import EDGES, FILL, apply, finish


def resource_summary(rows):
    """Summarize verification cost and median case duration by category."""
    summary = []
    for route, model in (
        ("decisions", "Luna Decisions"),
        ("luna", "Luna conventional"),
    ):
        for category in ("acquired", "patched", "generated"):
            selected = [row for row in rows if row["category"] == category]
            summary.append(
                {
                    "route": route,
                    "model": model,
                    "category": category,
                    "cases": len(selected),
                    "median_seconds": statistics.median(
                        row[route]["seconds"] for row in selected
                    ),
                    "cost_per_1000_usd": 1000
                    * statistics.mean(row[route]["usage"]["cost"] for row in selected),
                }
            )
    return summary


def draw_resource_figure(rows, output_dir):
    """Export Figure 11 with a centered shared legend and discreet value labels."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = resource_summary(rows)
    apply()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), layout="constrained")
    keys = ("median_seconds", "cost_per_1000_usd")
    limits = [max(row[key] for row in summary) * 1.23 for key in keys]
    for index, route in enumerate(("decisions", "luna")):
        selected = [row for row in summary if row["route"] == route]
        positions = np.arange(3) + (index - 0.5) * 0.25
        for axis, key, limit in zip(axes, keys, limits):
            values = [row[key] for row in selected]
            axis.barh(
                positions,
                values,
                height=0.18,
                color=FILL[index],
                edgecolor=EDGES[index],
                linewidth=0.7,
                label=selected[0]["model"],
            )
            for position, value in zip(positions, values):
                axis.text(
                    value + limit * 0.018,
                    position,
                    f"{value:.2f}",
                    va="center",
                    fontsize=6.5,
                )
    for axis, title, xlabel, limit in zip(
        axes,
        ("A  Verification time", "B  Inference cost"),
        ("Median seconds per case", "US$ per 1,000 cases at observed mean"),
        limits,
    ):
        axis.set_yticks(range(3), ("Acquired", "Patched", "Regenerated"))
        axis.invert_yaxis()
        axis.set_xlim(0, limit)
        axis.set_title(title, loc="left")
        finish(axis, xlabel)
    fig.legend(
        *axes[0].get_legend_handles_labels(),
        loc="outside lower center",
        ncol=2,
    )
    for extension in ("png",):
        fig.savefig(
            output_dir / f"method-resources.{extension}",
            dpi=1200,
            facecolor="white",
            bbox_inches="tight",
        )
    plt.close(fig)
    with (output_dir / "method-resources.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    return summary


if __name__ == "__main__":
    from publication_data import records

    print(json.dumps(draw_resource_figure(records(), ROOT / "analysis"), indent=2))
