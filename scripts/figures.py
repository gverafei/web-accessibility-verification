"""All new scientific charts originate from case-level receipts and human answers."""

import argparse, os, json, csv
from pathlib import Path
from core import ROOT, digest

os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "runtime/matplotlib"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from analysis_tools import report
from publication_data import records
from case_metadata import preparation, generator
from chart_style import apply, finish, FILL, EDGES

apply()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=ROOT / "analysis")
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
rows = records()
s = report(rows)
(out / "comparison.json").write_text(json.dumps(s, indent=2))
with (out / "case-comparison.csv").open("w") as f:
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
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(
        {**r, "page_preparation": preparation(r), "generating_model": generator(r)}
        for r in rows
    )


def save(fig, name):
    for ext in ["png"]:
        fig.savefig(
            out / (name + "." + ext), dpi=1000, facecolor="white", bbox_inches="tight"
        )
    plt.close(fig)


fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.35), layout="constrained")
for ax, scenario, title in zip(
    axs,
    ["acquired", "patched", "generated"],
    ["A  Acquired", "B  Patched", "C  Regenerated"],
):
    for j, (route, label) in enumerate(
        [("decisions", "Luna Decisions"), ("luna", "Luna conventional")]
    ):
        vals = [
            s["routes"][route][scenario]["pairs"][key]
            for key in ["automatic_r1", "automatic_r2"]
        ]
        for i, v in enumerate(vals):
            if v["agreement"] is None:
                continue
            x = v["agreement"] * 100
            y = i + (j - 0.5) * 0.22
            fill, edge = (
                ("#E1E5E9", "#758390")
                if route == "historical"
                else (
                    (FILL[0], EDGES[0]) if route == "decisions" else (FILL[1], EDGES[1])
                )
            )
            ax.barh(
                y,
                x,
                height=0.16,
                color=fill,
                edgecolor=edge,
                linewidth=0.7,
                label=label if i == 0 else None,
            )
            lo, hi = v["ci95"]
            ax.errorbar(
                x,
                y,
                xerr=[[max(0, x - lo)], [max(0, hi - x)]],
                color=edge,
                capsize=2,
                lw=0.65,
            )
            ax.text(102, y, f"{v['equal']}/{v['n']}", fontsize=6.5, va="center")
    ax.set_yticks([0, 1], ["R1", "R2"])
    ax.set_xlim(0, 122)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_title(title, loc="left")
    finish(ax, "Equal decisions (%)")
    ax.invert_yaxis()
fig.legend(*axs[0].get_legend_handles_labels(), loc="outside lower center", ncol=3)
save(fig, "model-comparison")
from resource_figure import draw_resource_figure

draw_resource_figure(rows, out)
fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.5), layout="constrained")
for ax, scenario, title in zip(
    axs,
    ["acquired", "patched", "generated"],
    ["A  Acquired", "B  Patched", "C  Regenerated"],
):
    for j, route in enumerate(["decisions", "luna"]):
        g = s["routes"][route][scenario]
        n = g["n"]
        left = 0
        for k, (key, label) in enumerate(
            [("accepted", "Admitted"), ("not_accepted", "Not admitted")]
        ):
            count = g["outcomes"].get(key, 0)
            v = 100 * count / n
            ax.barh(
                j,
                v,
                left=left,
                height=0.26,
                color=FILL[k],
                edgecolor=EDGES[k],
                lw=0.7,
                label=label if j == 0 else None,
            )
            if count:
                ax.text(
                    left + v / 2, j, str(count), ha="center", va="center", fontsize=6.5
                )
            left += v
    ax.set_yticks([0, 1], ["Luna Decisions", "Luna"])
    ax.set_xlim(0, 100)
    ax.set_title(title, loc="left")
    finish(ax, "Share of cases (%)")
fig.legend(*axs[0].get_legend_handles_labels(), loc="outside lower center", ncol=3)
save(fig, "decision-outcomes")
(out / "comparison-provenance.json").write_text(
    json.dumps(
        {
            "cases_sha256": digest(ROOT / "study/cases.json"),
            "scripts": {
                "scripts/" + p: digest(ROOT / "scripts" / p)
                for p in [
                    "figures.py",
                    "audit_figure.py",
                    "resource_figure.py",
                    "analysis_tools.py",
                    "chart_style.py",
                    "case_metadata.py",
                ]
            },
            "protocol_version": rows[0]["decisions"]["protocol"],
        },
        indent=2,
    )
)
# Figures 7–9 use exactly the same records and restrained palette.
from matplotlib.colors import LinearSegmentedColormap

cmap = LinearSegmentedColormap.from_list("restrained", ["#FFFFFF", FILL[0], EDGES[0]])
fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.2), layout="constrained")
for ax, key, title in zip(
    axs,
    ["automatic_r1", "automatic_r2", "r1_r2"],
    ["Decisions / R1", "Decisions / R2", "R1 / R2"],
):
    a = np.array(s["routes"]["decisions"]["acquired"]["pairs"][key]["matrix"])
    ax.imshow(a, cmap=cmap, vmin=0, vmax=max(a.max(), 1))
    for i in range(2):
        for j in range(2):
            ax.text(
                j,
                i,
                str(a[i, j]),
                ha="center",
                va="center",
                fontsize=7,
                color="#18354C" if a[i, j] < a.max() * 0.7 else "white",
            )
    ax.set_xticks([0, 1], ["Accept", "Reject"])
    ax.set_yticks([0, 1], ["Accept", "Reject"])
    ax.set_xlabel("Second assessor")
    ax.set_ylabel("First assessor")
    ax.set_title(title)
save(fig, "acquisition_validation")
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.7), layout="constrained")
names = list(s["strategies"])
y = np.arange(len(names))
for j, (route, label) in enumerate([("decisions", "Decisions"), ("luna", "Luna")]):
    for k, key in enumerate(["automatic_r1", "automatic_r2"]):
        vals = [
            100 * s["strategies"][n][route]["pairs"][key]["agreement"] for n in names
        ]
        axs[k].barh(
            y + (j - 0.5) * 0.24,
            vals,
            height=0.17,
            color=FILL[j],
            edgecolor=EDGES[j],
            linewidth=0.7,
            label=label,
        )
for ax, title in zip(
    axs, ["A  Agreement with Reviewer 1", "B  Agreement with Reviewer 2"]
):
    ax.set_yticks(
        y,
        [
            n.replace("Minimal + structural patches", "Minimal + structural\npatches")
            for n in names
        ],
    )
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_title(title, loc="left")
    finish(ax, "Equal decisions (%)")
fig.legend(*axs[0].get_legend_handles_labels(), loc="outside lower center", ncol=2)
save(fig, "remediation_validation")
from audit_figure import draw_audit_context

draw_audit_context(rows, out)
# Coverage report describes the active requests, including reconstructed/temporal views.
coverage_rows = rows
(out / "coverage.json").write_text(
    json.dumps(
        [
            {
                "case_id": c["case_id"],
                "number": c["number"],
                "review_id": c["review_id"],
                "category": c["category"],
                "protocol": c["decisions"]["protocol"],
                "complete": True,
                "current_images_evaluated": True,
                "roles": c["coverage_summaries"],
                "recorded_requests": c["input_coverage"],
            }
            for c in coverage_rows
        ],
        indent=2,
    )
)
print("Comparisons and six Python plots refreshed:", len(rows), "cases")
