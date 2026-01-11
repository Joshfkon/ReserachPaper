# nsfh_plots_improved.py
# Publication-ready plotting code for NSFH stacked analysis
# Improved styling for academic publication / Substack

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from pathlib import Path

TABLES_XLSX = Path("NSFH_stacked_tables.xlsx")
OUTDIR = Path("figures_improved")
OUTDIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Style configuration
# ─────────────────────────────────────────────────────────────────────────────

# Color palette - accessible and print-friendly
COLORS = {
    "Male": "#2166ac",      # Deep blue
    "Female": "#b2182b",    # Deep red
    "gap": "#4d4d4d",       # Dark gray for gap plots
    "ci_alpha": 0.20,       # CI band transparency
}

# Typography and layout
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.labelweight": "medium",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "legend.frameon": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.5,
    "lines.linewidth": 2.0,
    "lines.markersize": 7,
})


def cohort_sort_key(s):
    """Sort cohorts chronologically."""
    s = str(s)
    if s.startswith("≤") or s.startswith("â‰¤"):
        return -10000
    if s.startswith("≥") or s.startswith("â‰¥"):
        nums = "".join([c for c in s if c.isdigit()])
        return int(nums) if nums else 10000
    nums = "".join([c if c.isdigit() else " " for c in s]).split()
    return int(nums[0]) if nums else 0


def add_ci(p, n):
    """Calculate 95% CI for proportion."""
    p = np.asarray(p)
    n = np.asarray(n)
    se = np.sqrt(p * (1 - p) / n)
    return p - 1.96 * se, p + 1.96 * se


def format_cohort_label(s):
    """Clean up cohort labels for display."""
    s = str(s)
    # Normalize dash characters
    s = s.replace("–", "–").replace("-", "–")
    return s


def annotate_sample_sizes(ax, x_positions, n_values, y_offset=-0.08, fontsize=8):
    """Add sample size annotations below x-axis."""
    for x, n in zip(x_positions, n_values):
        ax.annotate(f"n={int(n)}", xy=(x, y_offset), xycoords=("data", "axes fraction"),
                    ha="center", va="top", fontsize=fontsize, color="#666666")


# ─────────────────────────────────────────────────────────────────────────────
# Plotting functions
# ─────────────────────────────────────────────────────────────────────────────

def plot_ever_partnered():
    """Ever partnered by age ≤35, by sex and cohort (wave2 only - sufficient data)."""
    df = pd.read_excel(TABLES_XLSX, sheet_name="stacked_primary_all_by_wave")
    
    # Focus on wave2 (wave3 has insufficient data)
    df = df[df["wave"] == "wave2"].copy()
    
    # Filter out small samples
    df = df[df["N_age_le_35"] >= 50]
    
    if df.empty:
        print("No sufficient data for ever_partnered plot")
        return
    
    cohorts = sorted(df["cohort_primary"].dropna().unique(), key=cohort_sort_key)
    cohort_labels = [format_cohort_label(c) for c in cohorts]
    x = np.arange(len(cohorts))
    
    fig, ax = plt.subplots(figsize=(8, 5.5))
    
    for sex in ["Male", "Female"]:
        s = df[df["sex_label"] == sex].copy()
        s["cohort_primary"] = pd.Categorical(s["cohort_primary"], categories=cohorts, ordered=True)
        s = s.sort_values("cohort_primary").reset_index(drop=True)
        
        p = s["p_ever_partnered"].values
        n = s["N_age_le_35"].values
        lo, hi = add_ci(p, n)
        
        # Plot CI band
        ax.fill_between(x[:len(p)], lo, hi, alpha=COLORS["ci_alpha"], 
                        color=COLORS[sex], linewidth=0)
        # Plot line and markers
        ax.plot(x[:len(p)], p, marker="o", color=COLORS[sex], label=sex,
                markerfacecolor="white", markeredgewidth=2)
    
    ax.set_xticks(x)
    ax.set_xticklabels(cohort_labels)
    ax.set_xlabel("Birth Cohort")
    ax.set_ylabel("Proportion Ever Partnered")
    ax.set_ylim(0.35, 0.85)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=0))
    
    ax.set_title("Ever Partnered by Age 35\nNSFH Wave 2 (1992–1994)")
    ax.legend(loc="lower right")
    
    # Add note about sample
    ax.text(0.02, 0.02, "Note: Cohorts with n < 50 excluded",
            transform=ax.transAxes, fontsize=8, color="#666666", style="italic")
    
    plt.tight_layout()
    plt.savefig(OUTDIR / "ever_partnered_by_cohort.png", dpi=300, bbox_inches="tight")
    plt.savefig(OUTDIR / "ever_partnered_by_cohort.pdf", bbox_inches="tight")
    plt.close()
    print("Saved: ever_partnered_by_cohort")


def plot_partnership_gap():
    """Female − Male gap in ever partnered (wave2)."""
    df = pd.read_excel(TABLES_XLSX, sheet_name="stacked_primary_all_by_wave")
    df = df[df["wave"] == "wave2"].copy()
    
    # Build gap dataframe
    f = df[df["sex_label"] == "Female"][["cohort_primary", "p_ever_partnered", "N_age_le_35"]].copy()
    m = df[df["sex_label"] == "Male"][["cohort_primary", "p_ever_partnered", "N_age_le_35"]].copy()
    g = f.merge(m, on="cohort_primary", suffixes=("_F", "_M"))
    
    # Filter small samples
    g = g[(g["N_age_le_35_F"] >= 50) & (g["N_age_le_35_M"] >= 50)]
    
    if g.empty:
        print("No sufficient data for gap plot")
        return
    
    g["gap"] = g["p_ever_partnered_F"] - g["p_ever_partnered_M"]
    g["se"] = np.sqrt(
        g["p_ever_partnered_F"] * (1 - g["p_ever_partnered_F"]) / g["N_age_le_35_F"] +
        g["p_ever_partnered_M"] * (1 - g["p_ever_partnered_M"]) / g["N_age_le_35_M"]
    )
    g["lo"] = g["gap"] - 1.96 * g["se"]
    g["hi"] = g["gap"] + 1.96 * g["se"]
    
    cohorts = sorted(g["cohort_primary"].unique(), key=cohort_sort_key)
    cohort_labels = [format_cohort_label(c) for c in cohorts]
    g["cohort_primary"] = pd.Categorical(g["cohort_primary"], categories=cohorts, ordered=True)
    g = g.sort_values("cohort_primary").reset_index(drop=True)
    
    x = np.arange(len(g))
    
    fig, ax = plt.subplots(figsize=(8, 5.5))
    
    # CI band
    ax.fill_between(x, g["lo"], g["hi"], alpha=COLORS["ci_alpha"], 
                    color=COLORS["gap"], linewidth=0)
    # Line and markers
    ax.plot(x, g["gap"], marker="o", color=COLORS["gap"],
            markerfacecolor="white", markeredgewidth=2)
    
    # Reference line at zero
    ax.axhline(0, color="#999999", linewidth=1, linestyle="--", zorder=1)
    
    ax.set_xticks(x)
    ax.set_xticklabels(cohort_labels)
    ax.set_xlabel("Birth Cohort")
    ax.set_ylabel("Gap (Female − Male)")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=0))
    
    # Annotate interpretation
    ax.text(0.98, 0.95, "↑ Women more likely partnered\n↓ Men more likely partnered",
            transform=ax.transAxes, fontsize=9, color="#666666",
            ha="right", va="top", linespacing=1.4)
    
    ax.set_title("Sex Gap in Partnership by Age 35\nNSFH Wave 2 (1992–1994)")
    
    plt.tight_layout()
    plt.savefig(OUTDIR / "partnership_gap_by_cohort.png", dpi=300, bbox_inches="tight")
    plt.savefig(OUTDIR / "partnership_gap_by_cohort.pdf", bbox_inches="tight")
    plt.close()
    print("Saved: partnership_gap_by_cohort")


def plot_marriages_remarriage():
    """Mean marriages and remarriage probability (wave2)."""
    df = pd.read_excel(TABLES_XLSX, sheet_name="stacked_primary_all_by_wave")
    df = df[df["wave"] == "wave2"].copy()
    df = df[df["N_age_le_35"] >= 50]
    
    if df.empty:
        print("No sufficient data for marriages plot")
        return
    
    cohorts = sorted(df["cohort_primary"].dropna().unique(), key=cohort_sort_key)
    cohort_labels = [format_cohort_label(c) for c in cohorts]
    x = np.arange(len(cohorts))
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # ─── Panel A: Mean marriages ───
    ax = axes[0]
    for sex in ["Male", "Female"]:
        s = df[df["sex_label"] == sex].copy()
        s["cohort_primary"] = pd.Categorical(s["cohort_primary"], categories=cohorts, ordered=True)
        s = s.sort_values("cohort_primary").reset_index(drop=True)
        
        y = s["mean_marriages_if_partnered"].values
        ax.plot(x[:len(y)], y, marker="o", color=COLORS[sex], label=sex,
                markerfacecolor="white", markeredgewidth=2)
    
    ax.set_xticks(x)
    ax.set_xticklabels(cohort_labels)
    ax.set_xlabel("Birth Cohort")
    ax.set_ylabel("Mean Number of Marriages")
    ax.set_ylim(0.98, 1.08)
    ax.set_title("A. Mean Marriages\n(among ever-partnered)")
    ax.legend(loc="upper left")
    
    # ─── Panel B: Remarriage probability ───
    ax = axes[1]
    for sex in ["Male", "Female"]:
        s = df[df["sex_label"] == sex].copy()
        s["cohort_primary"] = pd.Categorical(s["cohort_primary"], categories=cohorts, ordered=True)
        s = s.sort_values("cohort_primary").reset_index(drop=True)
        
        y = s["p_remarried_2plus_if_partnered"].values
        ax.plot(x[:len(y)], y, marker="o", color=COLORS[sex], label=sex,
                markerfacecolor="white", markeredgewidth=2)
    
    ax.set_xticks(x)
    ax.set_xticklabels(cohort_labels)
    ax.set_xlabel("Birth Cohort")
    ax.set_ylabel("Proportion Remarried (2+ marriages)")
    ax.set_ylim(-0.01, 0.12)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=0))
    ax.set_title("B. Remarriage Rate\n(among ever-partnered)")
    ax.legend(loc="upper left")
    
    fig.suptitle("Marriage Patterns by Birth Cohort — NSFH Wave 2 (1992–1994)",
                 fontsize=14, fontweight="bold", y=1.02)
    
    plt.tight_layout()
    plt.savefig(OUTDIR / "marriages_remarriage_panel.png", dpi=300, bbox_inches="tight")
    plt.savefig(OUTDIR / "marriages_remarriage_panel.pdf", bbox_inches="tight")
    plt.close()
    print("Saved: marriages_remarriage_panel")


def plot_combined_summary():
    """Single figure combining key findings."""
    df = pd.read_excel(TABLES_XLSX, sheet_name="stacked_primary_all_by_wave")
    df = df[df["wave"] == "wave2"].copy()
    df = df[df["N_age_le_35"] >= 50]
    
    if df.empty:
        print("No sufficient data for combined plot")
        return
    
    cohorts = sorted(df["cohort_primary"].dropna().unique(), key=cohort_sort_key)
    cohort_labels = [format_cohort_label(c) for c in cohorts]
    x = np.arange(len(cohorts))
    
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    
    # ─── Panel A: Ever partnered ───
    ax = axes[0, 0]
    for sex in ["Male", "Female"]:
        s = df[df["sex_label"] == sex].copy()
        s["cohort_primary"] = pd.Categorical(s["cohort_primary"], categories=cohorts, ordered=True)
        s = s.sort_values("cohort_primary").reset_index(drop=True)
        
        p = s["p_ever_partnered"].values
        n = s["N_age_le_35"].values
        lo, hi = add_ci(p, n)
        
        ax.fill_between(x[:len(p)], lo, hi, alpha=COLORS["ci_alpha"], 
                        color=COLORS[sex], linewidth=0)
        ax.plot(x[:len(p)], p, marker="o", color=COLORS[sex], label=sex,
                markerfacecolor="white", markeredgewidth=2)
    
    ax.set_xticks(x)
    ax.set_xticklabels(cohort_labels)
    ax.set_ylabel("Proportion")
    ax.set_ylim(0.35, 0.85)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=0))
    ax.set_title("A. Ever Partnered by Age 35")
    ax.legend(loc="lower right", fontsize=9)
    
    # ─── Panel B: Partnership gap ───
    ax = axes[0, 1]
    f = df[df["sex_label"] == "Female"][["cohort_primary", "p_ever_partnered", "N_age_le_35"]].copy()
    m = df[df["sex_label"] == "Male"][["cohort_primary", "p_ever_partnered", "N_age_le_35"]].copy()
    g = f.merge(m, on="cohort_primary", suffixes=("_F", "_M"))
    g = g[(g["N_age_le_35_F"] >= 50) & (g["N_age_le_35_M"] >= 50)]
    
    g["gap"] = g["p_ever_partnered_F"] - g["p_ever_partnered_M"]
    g["se"] = np.sqrt(
        g["p_ever_partnered_F"] * (1 - g["p_ever_partnered_F"]) / g["N_age_le_35_F"] +
        g["p_ever_partnered_M"] * (1 - g["p_ever_partnered_M"]) / g["N_age_le_35_M"]
    )
    g["lo"] = g["gap"] - 1.96 * g["se"]
    g["hi"] = g["gap"] + 1.96 * g["se"]
    
    gap_cohorts = sorted(g["cohort_primary"].unique(), key=cohort_sort_key)
    g["cohort_primary"] = pd.Categorical(g["cohort_primary"], categories=gap_cohorts, ordered=True)
    g = g.sort_values("cohort_primary").reset_index(drop=True)
    x_gap = np.arange(len(g))
    
    ax.fill_between(x_gap, g["lo"], g["hi"], alpha=COLORS["ci_alpha"], 
                    color=COLORS["gap"], linewidth=0)
    ax.plot(x_gap, g["gap"], marker="o", color=COLORS["gap"],
            markerfacecolor="white", markeredgewidth=2)
    ax.axhline(0, color="#999999", linewidth=1, linestyle="--", zorder=1)
    
    ax.set_xticks(x_gap)
    ax.set_xticklabels([format_cohort_label(c) for c in gap_cohorts])
    ax.set_ylabel("Gap (F − M)")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=0))
    ax.set_title("B. Sex Gap in Partnership")
    
    # ─── Panel C: Mean marriages ───
    ax = axes[1, 0]
    for sex in ["Male", "Female"]:
        s = df[df["sex_label"] == sex].copy()
        s["cohort_primary"] = pd.Categorical(s["cohort_primary"], categories=cohorts, ordered=True)
        s = s.sort_values("cohort_primary").reset_index(drop=True)
        
        y = s["mean_marriages_if_partnered"].values
        ax.plot(x[:len(y)], y, marker="o", color=COLORS[sex], label=sex,
                markerfacecolor="white", markeredgewidth=2)
    
    ax.set_xticks(x)
    ax.set_xticklabels(cohort_labels)
    ax.set_xlabel("Birth Cohort")
    ax.set_ylabel("Mean Marriages")
    ax.set_ylim(0.98, 1.08)
    ax.set_title("C. Mean Marriages (if partnered)")
    ax.legend(loc="upper left", fontsize=9)
    
    # ─── Panel D: Remarriage rate ───
    ax = axes[1, 1]
    for sex in ["Male", "Female"]:
        s = df[df["sex_label"] == sex].copy()
        s["cohort_primary"] = pd.Categorical(s["cohort_primary"], categories=cohorts, ordered=True)
        s = s.sort_values("cohort_primary").reset_index(drop=True)
        
        y = s["p_remarried_2plus_if_partnered"].values
        ax.plot(x[:len(y)], y, marker="o", color=COLORS[sex], label=sex,
                markerfacecolor="white", markeredgewidth=2)
    
    ax.set_xticks(x)
    ax.set_xticklabels(cohort_labels)
    ax.set_xlabel("Birth Cohort")
    ax.set_ylabel("Proportion")
    ax.set_ylim(-0.01, 0.12)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=0))
    ax.set_title("D. Remarriage Rate (if partnered)")
    ax.legend(loc="upper left", fontsize=9)
    
    fig.suptitle("Partnership and Marriage Patterns by Birth Cohort\nNSFH Wave 2 (1992–1994)",
                 fontsize=14, fontweight="bold")
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(OUTDIR / "nsfh_combined_summary.png", dpi=300, bbox_inches="tight")
    plt.savefig(OUTDIR / "nsfh_combined_summary.pdf", bbox_inches="tight")
    plt.close()
    print("Saved: nsfh_combined_summary")


if __name__ == "__main__":
    plot_ever_partnered()
    plot_partnership_gap()
    plot_marriages_remarriage()
    plot_combined_summary()
    print(f"\nAll figures saved to {OUTDIR}/")
