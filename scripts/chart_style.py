"""Shared Harness²-inspired editorial palette for Python plots and PDF exports."""

import matplotlib.pyplot as plt

INK = "#243746"
BLUE = "#3979A6"
PURPLE = "#8268A9"
TEAL = "#338A86"
FILL = ["#C6DDEC", "#DCD0EA", "#C6E3DF"]
EDGES = [BLUE, PURPLE, TEAL]


def apply():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.titleweight": "bold",
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "text.color": INK,
            "axes.labelcolor": INK,
            "axes.edgecolor": "#8796A3",
            "axes.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
            "legend.frameon": False,
            "legend.fontsize": 7,
        }
    )


def finish(ax, xlabel):
    ax.set_xlabel(xlabel)
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="#E8EDF2", lw=0.5)
    ax.tick_params(axis="y", length=0)
