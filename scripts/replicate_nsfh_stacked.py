#!/usr/bin/env python3
"""
replicate_nsfh_stacked.py

Stacks NSFH Wave 1/2/3 replication-ready analytic extracts into a single dataset,
then produces stacked tables with the same structure as wave-specific outputs.

Inputs (defaults; override via CLI):
- NSFH_Wave1_analytic_replication_ready.xlsx  (sheet: analytic)
- NSFH_Wave2_analytic_replication_ready.xlsx  (sheet: analytic)
- NSFH_Wave3_analytic_replication_ready.xlsx  (sheet: analytic)

Outputs:
- NSFH_stacked_analytic_replication_ready.xlsx (sheet: analytic)
- NSFH_stacked_tables.xlsx
    - stacked_primary_all
    - stacked_primary_present
    - stacked_ever_partnered_gap
    - stacked_primary_all_by_wave
    - stacked_primary_present_by_wave
    - stacked_ever_partnered_gap_by_wave

Notes:
- The script preserves *existing* variable definitions from each wave package.
- It does not attempt to "repair" instrument drift; it documents and carries through NA where appropriate.
- Cohort fields are standardized to:
    cohort_primary, cohort_macro
  by renaming wave-specific equivalents when needed.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def read_analytic(xlsx_path: Path, wave: str) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, sheet_name="analytic", engine="openpyxl")
    df["wave"] = wave

    # Standardize cohort columns across waves
    rename = {}
    if "primary_cohort" in df.columns and "cohort_primary" not in df.columns:
        rename["primary_cohort"] = "cohort_primary"
    if "macro_cohort" in df.columns and "cohort_macro" not in df.columns:
        rename["macro_cohort"] = "cohort_macro"
    df = df.rename(columns=rename)

    # Standardize sex_label if missing but sex exists
    if "sex_label" not in df.columns and "sex" in df.columns:
        df["sex_label"] = df["sex"].map({1: "Male", 2: "Female"})

    # Standardize age_le_35 if missing
    if "age_le_35" not in df.columns and "age" in df.columns:
        df["age_le_35"] = (pd.to_numeric(df["age"], errors="coerce") <= 35).astype("Int64")

    return df

def stack_align(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    # union of columns
    cols = sorted(set().union(*[set(d.columns) for d in dfs]))
    out = []
    for d in dfs:
        missing = [c for c in cols if c not in d.columns]
        for c in missing:
            d[c] = pd.NA
        out.append(d[cols])
    stacked = pd.concat(out, ignore_index=True)
    return stacked

def compute_tables(analytic: pd.DataFrame, n_threshold: int = 200, by_wave: bool = True) -> dict[str, pd.DataFrame]:
    # Ensure numeric
    a = analytic.copy()
    for c in ["age", "sex", "num_marriages", "num_cohab_partners", "ever_partnered", "remarried_2plus"]:
        if c in a.columns:
            a[c] = pd.to_numeric(a[c], errors="coerce")

    # Restrict for table stats
    a35 = a.loc[a["age_le_35"] == 1].copy()

    group_keys = ["cohort_primary", "sex_label"]
    if by_wave:
        group_keys = ["wave"] + group_keys

    def metric_frame(d: pd.DataFrame) -> pd.Series:
        p_partnered = d["ever_partnered"].mean()
        partnered = d.loc[d["ever_partnered"] == 1]
        return pd.Series({
            "N_age_le_35": len(d),
            "p_ever_partnered": p_partnered,
            "mean_cohab_partners_if_partnered": partnered["num_cohab_partners"].mean(),
            "mean_marriages_if_partnered": partnered["num_marriages"].mean(),
            "p_remarried_2plus_if_partnered": partnered["remarried_2plus"].mean(),
        })

    primary_all = a35.groupby(group_keys, dropna=False).apply(metric_frame).reset_index()

    # Determine "present" cohorts (both sexes >= threshold) within each wave if by_wave else pooled
    if by_wave:
        present_rows = []
        for w, sub in primary_all.groupby("wave", dropna=False):
            n_by = sub.pivot(index="cohort_primary", columns="sex_label", values="N_age_le_35")
            keep = n_by.dropna().loc[(n_by.get("Female", 0) >= n_threshold) & (n_by.get("Male", 0) >= n_threshold)].index
            present_rows.append(sub.loc[sub["cohort_primary"].isin(keep)])
        primary_present = pd.concat(present_rows, ignore_index=True) if present_rows else primary_all.iloc[0:0].copy()
    else:
        n_by = primary_all.pivot(index="cohort_primary", columns="sex_label", values="N_age_le_35")
        keep = n_by.dropna().loc[(n_by.get("Female", 0) >= n_threshold) & (n_by.get("Male", 0) >= n_threshold)].index
        primary_present = primary_all.loc[primary_all["cohort_primary"].isin(keep)].copy()

    # Gap table
    if by_wave:
        gap_rows = []
        for w, sub in primary_present.groupby("wave", dropna=False):
            p_by = sub.pivot(index="cohort_primary", columns="sex_label", values="p_ever_partnered")
            gap = (p_by.get("Female") - p_by.get("Male")).rename("female_minus_male_p_ever_partnered").reset_index()
            gap.insert(0, "wave", w)
            gap_rows.append(gap)
        ever_partnered_gap = pd.concat(gap_rows, ignore_index=True) if gap_rows else primary_present.iloc[0:0].copy()
    else:
        p_by = primary_present.pivot(index="cohort_primary", columns="sex_label", values="p_ever_partnered")
        ever_partnered_gap = (p_by.get("Female") - p_by.get("Male")).rename("female_minus_male_p_ever_partnered").reset_index()

    return {
        "primary_all": primary_all,
        "primary_present": primary_present,
        "ever_partnered_gap": ever_partnered_gap,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave1_xlsx", default="NSFH_Wave1_analytic_replication_ready.xlsx")
    ap.add_argument("--wave2_xlsx", default="NSFH_Wave2_analytic_replication_ready.xlsx")
    ap.add_argument("--wave3_xlsx", default="NSFH_Wave3_analytic_replication_ready.xlsx")
    ap.add_argument("--out_dir", default=".")
    ap.add_argument("--n_threshold", type=int, default=200)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    inputs = [
        ("wave1", Path(args.wave1_xlsx)),
        ("wave2", Path(args.wave2_xlsx)),
        ("wave3", Path(args.wave3_xlsx)),
    ]

    dfs = []
    present_inputs = []
    for wave, p in inputs:
        if p.exists():
            dfs.append(read_analytic(p, wave))
            present_inputs.append((wave, p.name))
        else:
            print(f"WARNING: missing {p} (skipping {wave})")

    if not dfs:
        raise FileNotFoundError("No input analytic files found. Provide at least one wave analytic xlsx.")

    stacked = stack_align(dfs)

    out_analytic = out_dir / "NSFH_stacked_analytic_replication_ready.xlsx"
    with pd.ExcelWriter(out_analytic, engine="openpyxl") as xw:
        stacked.to_excel(xw, sheet_name="analytic", index=False)

    # Pooled tables (across waves)
    pooled = compute_tables(stacked, n_threshold=args.n_threshold, by_wave=False)
    # By-wave tables
    bywave = compute_tables(stacked, n_threshold=args.n_threshold, by_wave=True)

    out_tables = out_dir / "NSFH_stacked_tables.xlsx"
    with pd.ExcelWriter(out_tables, engine="openpyxl") as xw:
        pooled["primary_all"].to_excel(xw, sheet_name="stacked_primary_all", index=False)
        pooled["primary_present"].to_excel(xw, sheet_name="stacked_primary_present", index=False)
        pooled["ever_partnered_gap"].to_excel(xw, sheet_name="stacked_ever_partnered_gap", index=False)

        bywave["primary_all"].to_excel(xw, sheet_name="stacked_primary_all_by_wave", index=False)
        bywave["primary_present"].to_excel(xw, sheet_name="stacked_primary_present_by_wave", index=False)
        bywave["ever_partnered_gap"].to_excel(xw, sheet_name="stacked_ever_partnered_gap_by_wave", index=False)

    print("Inputs used:")
    for wave, name in present_inputs:
        print(f" - {wave}: {name}")
    print("Wrote:")
    print(f" - {out_analytic}")
    print(f" - {out_tables}")

if __name__ == "__main__":
    main()
