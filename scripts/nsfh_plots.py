
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

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

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

        plt.figure(figsize=(8,5))
        for sex in ["Male", "Female"]:
            s = d[d["sex_label"] == sex].sort_values("cohort_primary")
            p = s["p_ever_partnered"]
            n = s["N_age_le_35"]
            lo, hi = add_ci(p, n)

            plt.plot(s["cohort_primary"], p, marker="o", label=sex)
            plt.errorbar(s["cohort_primary"], p, yerr=[p-lo, hi-p], fmt="none", capsize=3)

        plt.title(f"Ever partnered by age ≤35 — {wave}")
        plt.ylabel("Probability")
        plt.xlabel("Birth cohort")
        plt.ylim(0,1)
        plt.xticks(rotation=45, ha="right")
        plt.legend()
        plt.tight_layout()
        plt.savefig(OUTDIR / f"ever_partnered_{wave}.png", dpi=300)
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

        plt.figure(figsize=(8,5))
        plt.plot(d["cohort_primary"], d["gap"], marker="o")
        plt.errorbar(d["cohort_primary"], d["gap"],
                     yerr=[d["gap"]-d["lo"], d["hi"]-d["gap"]],
                     fmt="none", capsize=3)
        plt.axhline(0, linewidth=1)
        plt.title(f"Female − Male gap in ever partnered — {wave}")
        plt.ylabel("Gap")
        plt.xlabel("Birth cohort")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(OUTDIR / f"gap_ever_partnered_{wave}.png", dpi=300)
        plt.close()

def plot_marriages_and_remarriage():
    df = pd.read_excel(TABLES_XLSX, sheet_name="stacked_primary_all_by_wave")

    for wave, d in df.groupby("wave"):
        cohorts = sorted(d["cohort_primary"].dropna().unique(), key=cohort_sort_key)
        d["cohort_primary"] = pd.Categorical(d["cohort_primary"], categories=cohorts, ordered=True)

        # Mean marriages
        plt.figure(figsize=(8,5))
        for sex in ["Male","Female"]:
            s = d[d["sex_label"]==sex].sort_values("cohort_primary")
            plt.plot(s["cohort_primary"], s["mean_marriages_if_partnered"], marker="o", label=sex)
        plt.title(f"Mean marriages | ever partnered — {wave}")
        plt.ylabel("Mean marriages")
        plt.xlabel("Birth cohort")
        plt.xticks(rotation=45, ha="right")
        plt.legend()
        plt.tight_layout()
        plt.savefig(OUTDIR / f"mean_marriages_{wave}.png", dpi=300)
        plt.close()

        # Remarriage probability
        plt.figure(figsize=(8,5))
        for sex in ["Male","Female"]:
            s = d[d["sex_label"]==sex].sort_values("cohort_primary")
            plt.plot(s["cohort_primary"], s["p_remarried_2plus_if_partnered"], marker="o", label=sex)
        plt.title(f"P(remarried 2+ | partnered) — {wave}")
        plt.ylabel("Probability")
        plt.xlabel("Birth cohort")
        plt.ylim(0,1)
        plt.xticks(rotation=45, ha="right")
        plt.legend()
        plt.tight_layout()
        plt.savefig(OUTDIR / f"p_remarried2plus_{wave}.png", dpi=300)
        plt.close()

if __name__ == "__main__":
    plot_ever_partnered_by_wave()
    plot_gap_by_wave()
    plot_marriages_and_remarriage()
