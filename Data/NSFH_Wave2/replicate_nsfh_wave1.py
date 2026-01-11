#!/usr/bin/env python3
"""
Replicate NSFH Wave 1 analytic extract + cohort×sex tables.

Inputs:
  - /mnt/data/06041-0001-Data.tsv

Outputs:
  - /mnt/data/NSFH_Wave1_analytic_replication_ready.xlsx
  - /mnt/data/NSFH_Wave1_tables.xlsx
"""

from pathlib import Path
import numpy as np
import pandas as pd

RAW_TSV = Path("/mnt/data/06041-0001-Data.tsv")
OUT_XLSX = Path("/mnt/data/NSFH_Wave1_analytic_replication_ready.xlsx")
TABLES_XLSX = Path("/mnt/data/NSFH_Wave1_tables.xlsx")
MIN_N = 200

def main():
    df = pd.read_csv(RAW_TSV, sep="\t", low_memory=False)

    # Base vars
    df["age"] = df["M2BP01"]
    df["sex"] = df["M2DP01"]  # 1=Male, 2=Female
    df["sex_label"] = df["sex"].map({1: "Male", 2: "Female"})

    # Birth year approximation: interview mostly 1987
    df["birth_year"] = 1987 - df["age"]

    # Marriage (M95)
    df["num_marriages"] = df["M95"].replace({99: np.nan})
    df["ever_married"] = (df["num_marriages"].fillna(0) >= 1).astype(int)
    df["remarried_2plus"] = (df["num_marriages"] >= 2).astype(int)

    # Cohabitation
    df["num_cohab_partners"] = df["NUMCOHAB"]
    df["ever_cohabited"] = (df["num_cohab_partners"] >= 1).astype(int)

    # Ever partnered
    df["ever_partnered"] = ((df["ever_married"] == 1) | (df["ever_cohabited"] == 1)).astype(int)

    # Analysis indicator
    df["age_le_35"] = (df["age"] <= 35).astype(int)

    # Cohorts
    bins_primary = [1951.5, 1956.5, 1960.5, 1964.5, 1968.5, 1972.5]
    labels_primary = ["1952–56", "1957–60", "1961–64", "1965–68", "1969–72"]
    df["birth_cohort_primary"] = pd.cut(df["birth_year"], bins=bins_primary, labels=labels_primary, include_lowest=True)

    bins_macro = [-np.inf, 1949.5, 1959.5, 1969.5, 1979.5, np.inf]
    labels_macro = ["≤1949", "1950–59", "1960–69", "1970–79", "≥1980"]
    df["birth_cohort_macro"] = pd.cut(df["birth_year"], bins=bins_macro, labels=labels_macro, include_lowest=True)

    analytic_cols = [
        "MCASEID",
        "age", "age_le_35",
        "sex", "sex_label",
        "birth_year",
        "birth_cohort_primary",
        "birth_cohort_macro",
        "num_cohab_partners", "ever_cohabited",
        "num_marriages", "ever_married", "remarried_2plus",
        "ever_partnered",
        # Raw sources for auditability
        "M2BP01", "M2DP01", "NUMCOHAB", "M95",
    ]
    analytic = df[analytic_cols].copy()

    engine_kwargs = {"options": {"constant_memory": True}}

    # Write analytic extract
    with pd.ExcelWriter(OUT_XLSX, engine="xlsxwriter", engine_kwargs=engine_kwargs) as writer:
        analytic.to_excel(writer, index=False, sheet_name="analytic")

    # Tables
    sub = analytic[analytic["age_le_35"] == 1].copy()

    def make_table(cohort_col: str) -> pd.DataFrame:
        rows = []
        cohorts = sorted([c for c in sub[cohort_col].dropna().unique()], key=lambda x: str(x))
        for cohort in cohorts:
            for sex in ["Female", "Male"]:
                d = sub[(sub[cohort_col] == cohort) & (sub["sex_label"] == sex)]
                if len(d) == 0:
                    continue
                partnered = d[d["ever_partnered"] == 1]
                rows.append({
                    "cohort_type": cohort_col,
                    "cohort": str(cohort),
                    "sex": sex,
                    "N (age≤35)": int(len(d)),
                    "P(ever partnered)": partnered.shape[0] / len(d) if len(d) else np.nan,
                    "Mean # cohab partners | partnered": partnered["num_cohab_partners"].mean(),
                    "Mean # marriages (M95) | partnered": partnered["num_marriages"].mean(),
                    "P(remarried 2+ | partnered)": partnered["remarried_2plus"].mean(),
                })
        return pd.DataFrame(rows)

    tab_primary = make_table("birth_cohort_primary")

    counts = tab_primary.pivot_table(index="cohort", columns="sex", values="N (age≤35)", aggfunc="first")
    valid = counts[(counts.get("Male", 0) >= MIN_N) & (counts.get("Female", 0) >= MIN_N)].index.tolist()
    tab_primary_present = tab_primary[tab_primary["cohort"].isin(valid)].copy()

    pivot = tab_primary_present.pivot(index="cohort", columns="sex", values="P(ever partnered)")
    gap = pivot.assign(Gap_Female_minus_Male=lambda x: x["Female"] - x["Male"]).reset_index()

    with pd.ExcelWriter(TABLES_XLSX, engine="xlsxwriter", engine_kwargs=engine_kwargs) as writer:
        tab_primary.to_excel(writer, index=False, sheet_name="primary_all")
        tab_primary_present.to_excel(writer, index=False, sheet_name="primary_present")
        gap.to_excel(writer, index=False, sheet_name="ever_partnered_gap")

    print("Wrote:", OUT_XLSX)
    print("Wrote:", TABLES_XLSX)

if __name__ == "__main__":
    main()
