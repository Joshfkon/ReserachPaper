
# nsfh_plots.py
# Publication-ready plotting code for NSFH stacked analysis
# Uses NSFH_stacked_tables.xlsx and NSFH_stacked_analytic_replication_ready.xlsx
# Figures generated:
#  - Ever partnered by age ≤35 (by wave)
#  - Female − Male gap in ever partnered (by wave)
#  - Mean marriages | partnered
#  - P(remarried 2+ | partnered)
#
# Designed for GitHub inclusion (no notebook state, deterministic outputs)
# Style: FT-inspired with clean, journal-appropriate colors

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from pathlib import Path

# =============================================================================
# FT-STYLE CONFIGURATION (Journal-appropriate colors)
# =============================================================================

# Color palette - muted, professional, colorblind-friendly
COLORS = {
    'male': '#2A6185',       # Deep teal-blue
    'female': '#D4654A',     # Muted coral/terracotta
    'single': '#3D5A6C',     # Slate blue-gray for single-series plots
    'reference': '#9EAEB8',  # Light gray for reference lines
    'grid': '#E8E8E8',       # Very light gray for gridlines
    'text': '#333333',       # Dark gray for text (not pure black)
    'spine': '#CCCCCC',      # Light gray for axis spines
}

# Figure styling
FIG_WIDTH = 7
FIG_HEIGHT = 4.5
DPI = 300

def setup_ft_style():
    """Configure matplotlib for FT-inspired journal style."""
    plt.rcParams.update({
        # Figure
        'figure.figsize': (FIG_WIDTH, FIG_HEIGHT),
        'figure.facecolor': 'white',
        'figure.dpi': 100,
        'savefig.dpi': DPI,
        'savefig.facecolor': 'white',
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.15,

        # Font - clean sans-serif
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans'],
        'font.size': 10,

        # Axes
        'axes.facecolor': 'white',
        'axes.edgecolor': COLORS['spine'],
        'axes.linewidth': 0.8,
        'axes.grid': True,
        'axes.axisbelow': True,
        'axes.titlesize': 12,
        'axes.titleweight': 'medium',
        'axes.titlepad': 12,
        'axes.labelsize': 10,
        'axes.labelcolor': COLORS['text'],
        'axes.labelpad': 8,
        'axes.spines.top': False,
        'axes.spines.right': False,

        # Grid
        'grid.color': COLORS['grid'],
        'grid.linewidth': 0.6,
        'grid.alpha': 1.0,

        # Ticks
        'xtick.color': COLORS['text'],
        'ytick.color': COLORS['text'],
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'xtick.major.width': 0.8,
        'ytick.major.width': 0.8,
        'xtick.major.size': 4,
        'ytick.major.size': 4,

        # Legend
        'legend.frameon': False,
        'legend.fontsize': 9,
        'legend.loc': 'best',

        # Lines
        'lines.linewidth': 2.0,
        'lines.markersize': 6,
    })

# Apply style on import
setup_ft_style()

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
TABLES_XLSX = PROJECT_ROOT / "Data" / "NSFH_WavesStacked" / "NSFH_stacked_tables.xlsx"
ANALYTIC_XLSX = PROJECT_ROOT / "Data" / "NSFH_WavesStacked" / "NSFH_stacked_analytic_replication_ready.xlsx"
OUTDIR = PROJECT_ROOT / "figures"
OUTDIR.mkdir(exist_ok=True)

def cohort_sort_key(s):
    s = str(s)
    if s.startswith("≤"):
        return -10000
    if s.startswith("≥"):
        nums = "".join([c for c in s if c.isdigit()])
        return int(nums) if nums else 10000
    nums = "".join([c if c.isdigit() else " " for c in s]).split()
    return int(nums[0]) if nums else 0

def add_ci(p, n):
    se = np.sqrt(p * (1 - p) / n)
    return p - 1.96 * se, p + 1.96 * se

def plot_ever_partnered_by_wave():
    df = pd.read_excel(TABLES_XLSX, sheet_name="stacked_primary_all_by_wave")

    for wave, d in df.groupby("wave"):
        cohorts = sorted(d["cohort_primary"].dropna().unique(), key=cohort_sort_key)
        d["cohort_primary"] = pd.Categorical(d["cohort_primary"], categories=cohorts, ordered=True)

        fig, ax = plt.subplots()
        sex_colors = {'Male': COLORS['male'], 'Female': COLORS['female']}

        for sex in ["Male", "Female"]:
            s = d[d["sex_label"] == sex].sort_values("cohort_primary")
            p = s["p_ever_partnered"]
            n = s["N_age_le_35"]
            lo, hi = add_ci(p, n)
            color = sex_colors[sex]

            ax.plot(s["cohort_primary"], p, marker="o", label=sex, color=color)
            ax.errorbar(s["cohort_primary"], p, yerr=[p-lo, hi-p],
                        fmt="none", capsize=3, color=color, alpha=0.7)

        ax.set_title(f"Ever partnered by age ≤35 — {wave}")
        ax.set_ylabel("Probability")
        ax.set_xlabel("Birth cohort")
        ax.set_ylim(0, 1)
        plt.xticks(rotation=45, ha="right")
        ax.legend()
        plt.tight_layout()
        plt.savefig(OUTDIR / f"ever_partnered_{wave}.png")
        plt.close()

def plot_gap_by_wave():
    df = pd.read_excel(TABLES_XLSX, sheet_name="stacked_primary_all_by_wave")

    out = []
    for wave, d in df.groupby("wave"):
        f = d[d["sex_label"]=="Female"][["cohort_primary","p_ever_partnered","N_age_le_35"]]
        m = d[d["sex_label"]=="Male"][["cohort_primary","p_ever_partnered","N_age_le_35"]]
        g = f.merge(m, on="cohort_primary", suffixes=("_F","_M"))
        g["gap"] = g["p_ever_partnered_F"] - g["p_ever_partnered_M"]
        g["se"] = np.sqrt(
            g["p_ever_partnered_F"]*(1-g["p_ever_partnered_F"])/g["N_age_le_35_F"] +
            g["p_ever_partnered_M"]*(1-g["p_ever_partnered_M"])/g["N_age_le_35_M"]
        )
        g["lo"] = g["gap"] - 1.96*g["se"]
        g["hi"] = g["gap"] + 1.96*g["se"]
        g["wave"] = wave
        out.append(g)

    gdf = pd.concat(out, ignore_index=True)

    for wave, d in gdf.groupby("wave"):
        cohorts = sorted(d["cohort_primary"].dropna().unique(), key=cohort_sort_key)
        d["cohort_primary"] = pd.Categorical(d["cohort_primary"], categories=cohorts, ordered=True)
        d = d.sort_values("cohort_primary")

        fig, ax = plt.subplots()
        ax.plot(d["cohort_primary"], d["gap"], marker="o", color=COLORS['single'])
        ax.errorbar(d["cohort_primary"], d["gap"],
                    yerr=[d["gap"]-d["lo"], d["hi"]-d["gap"]],
                    fmt="none", capsize=3, color=COLORS['single'], alpha=0.7)
        ax.axhline(0, linewidth=1, color=COLORS['reference'], linestyle='--')
        ax.set_title(f"Female − Male gap in ever partnered — {wave}")
        ax.set_ylabel("Gap")
        ax.set_xlabel("Birth cohort")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(OUTDIR / f"gap_ever_partnered_{wave}.png")
        plt.close()

def plot_marriages_and_remarriage():
    df = pd.read_excel(TABLES_XLSX, sheet_name="stacked_primary_all_by_wave")
    sex_colors = {'Male': COLORS['male'], 'Female': COLORS['female']}

    for wave, d in df.groupby("wave"):
        cohorts = sorted(d["cohort_primary"].dropna().unique(), key=cohort_sort_key)
        d["cohort_primary"] = pd.Categorical(d["cohort_primary"], categories=cohorts, ordered=True)

        # Mean marriages
        fig, ax = plt.subplots()
        for sex in ["Male", "Female"]:
            s = d[d["sex_label"]==sex].sort_values("cohort_primary")
            ax.plot(s["cohort_primary"], s["mean_marriages_if_partnered"],
                    marker="o", label=sex, color=sex_colors[sex])
        ax.set_title(f"Mean marriages | ever partnered — {wave}")
        ax.set_ylabel("Mean marriages")
        ax.set_xlabel("Birth cohort")
        plt.xticks(rotation=45, ha="right")
        ax.legend()
        plt.tight_layout()
        plt.savefig(OUTDIR / f"mean_marriages_{wave}.png")
        plt.close()

        # Remarriage probability
        fig, ax = plt.subplots()
        for sex in ["Male", "Female"]:
            s = d[d["sex_label"]==sex].sort_values("cohort_primary")
            ax.plot(s["cohort_primary"], s["p_remarried_2plus_if_partnered"],
                    marker="o", label=sex, color=sex_colors[sex])
        ax.set_title(f"P(remarried 2+ | partnered) — {wave}")
        ax.set_ylabel("Probability")
        ax.set_xlabel("Birth cohort")
        ax.set_ylim(0, 1)
        plt.xticks(rotation=45, ha="right")
        ax.legend()
        plt.tight_layout()
        plt.savefig(OUTDIR / f"p_remarried2plus_{wave}.png")
        plt.close()

if __name__ == "__main__":
    plot_ever_partnered_by_wave()
    plot_gap_by_wave()
    plot_marriages_and_remarriage()
