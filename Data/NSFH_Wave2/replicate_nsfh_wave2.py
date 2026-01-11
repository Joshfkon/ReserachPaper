#!/usr/bin/env python3
"""
replicate_nsfh_wave2.py

End-to-end replication script for NSFH Wave 2 (1992–94) main respondent file (DS0001).

Reads the raw Wave 2 TSV and writes:
- NSFH_Wave2_analytic_replication_ready.xlsx (sheet: analytic)
- NSFH_Wave2_tables.xlsx (sheets: primary_all, primary_present, ever_partnered_gap)

IMPORTANT (Wave-2-specific forced deviations):
- Wave 2 instrument provides "times married since NSFH1" (MI41), not lifetime number of marriages (Wave1 M95).
- Wave 2 instrument provides "number of co-residential partners since last marriage ended" (MI140),
  not lifetime number of cohabiting partners (Wave1 NUMCOHAB).
See README_nsfh_wave2_replication.md for details.
"""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

COMMON_MISS = {7,8,9,97,98,99,997,998,999,9997,9998,9999,99997,99998,99999}

def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")

def recode_missing_numeric(x: pd.Series, miss_codes) -> pd.Series:
    x = to_num(x)
    for c in miss_codes:
        x = x.mask(x == c)
    return x

def macro_bin(by):
    if pd.isna(by): return np.nan
    by=int(by)
    if by <= 1949: return "≤1949"
    if 1950 <= by <= 1959: return "1950–59"
    if 1960 <= by <= 1969: return "1960–69"
    if 1970 <= by <= 1979: return "1970–79"
    return "≥1980"

def cohort_sex_table(df_a: pd.DataFrame, cohort_col: str, only_present: bool, min_n: int) -> pd.DataFrame:
    d = df_a.copy()
    d = d[d["age_le_35"]==1]
    if only_present:
        d = d[d[cohort_col].notna()]

    grouped = d.groupby([cohort_col, "sex_label"], dropna=False)
    out = grouped.size().rename("N").reset_index()

    out = out.merge(grouped["ever_partnered"].mean().rename("P_ever_partnered").reset_index(),
                    on=[cohort_col, "sex_label"], how="left")

    partnered = d[d["ever_partnered"]==1]
    g2 = partnered.groupby([cohort_col, "sex_label"], dropna=False)

    out = out.merge(g2["num_cohab_partners"].mean().rename("Mean_num_cohab_partners_if_partnered").reset_index(),
                    on=[cohort_col, "sex_label"], how="left")
    out = out.merge(g2["num_marriages"].mean().rename("Mean_num_marriages_if_partnered").reset_index(),
                    on=[cohort_col, "sex_label"], how="left")
    out = out.merge(g2["remarried_2plus"].mean().rename("P_remarried_2plus_if_partnered").reset_index(),
                    on=[cohort_col, "sex_label"], how="left")

    pivotN = out.pivot(index=cohort_col, columns="sex_label", values="N")
    keep = pivotN.dropna().index[(pivotN.dropna()>=min_n).all(axis=1)]
    return out[out[cohort_col].isin(keep)].copy()

def gap_table(tab: pd.DataFrame, cohort_col: str) -> pd.DataFrame:
    pvt = tab.pivot(index=cohort_col, columns="sex_label", values="P_ever_partnered")
    gap = (pvt.get("Female") - pvt.get("Male")).rename("Female_minus_Male_P_ever_partnered")
    return gap.reset_index()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw_tsv", required=True, help="Path to Wave2 DS0001 main respondent raw TSV.")
    ap.add_argument("--out_dir", default=".", help="Output directory.")
    ap.add_argument("--interview_year", type=int, default=1993, help="Interview year used to compute birth_year.")
    ap.add_argument("--min_n", type=int, default=200, help="Minimum N per sex within cohort for inclusion.")
    args = ap.parse_args()

    raw_path = Path(args.raw_tsv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(raw_path, sep="\t", low_memory=False)

    age_src = "MA8"
    sex_src = "MA7"
    marriages_src = "MI41"
    cohab_n_src = "MI140"
    married_since_src = "MI40"
    cohab_since_src = "MI42"

    for v in [age_src, sex_src, marriages_src, cohab_n_src, married_since_src, cohab_since_src]:
        if v not in df.columns:
            raise ValueError(f"Expected variable {v} not found in {raw_path.name}")

    age = recode_missing_numeric(df[age_src], COMMON_MISS)
    sex = recode_missing_numeric(df[sex_src], COMMON_MISS)
    birth_year = args.interview_year - age

    num_marriages = recode_missing_numeric(df[marriages_src], COMMON_MISS)
    num_cohab_partners = recode_missing_numeric(df[cohab_n_src], COMMON_MISS)

    mi40 = recode_missing_numeric(df[married_since_src], COMMON_MISS)
    mi42 = recode_missing_numeric(df[cohab_since_src], COMMON_MISS)

    ever_married = np.where((num_marriages >= 1) | (mi40 == 1), 1, np.where(mi40.isna() & num_marriages.isna(), np.nan, 0))
    remarried_2plus = np.where(num_marriages >= 2, 1, np.where(num_marriages.isna(), np.nan, 0))
    ever_cohabited = np.where((num_cohab_partners >= 1) | (mi42 == 1), 1, np.where(mi42.isna() & num_cohab_partners.isna(), np.nan, 0))
    ever_partnered = np.where((ever_married == 1) | (ever_cohabited == 1), 1,
                              np.where((pd.isna(ever_married)) & (pd.isna(ever_cohabited)), np.nan, 0))
    age_le_35 = np.where(age <= 35, 1, np.where(age.isna(), np.nan, 0))

    sex_label = np.where(sex==1, "Male", np.where(sex==2, "Female", np.nan))

    # primary cohorts: 5-year bins from observed birth_year among age<=35
    birth_year_le35 = birth_year[age_le_35 == 1].dropna().astype(int)
    min_by, max_by = birth_year_le35.min(), birth_year_le35.max()
    start = (min_by // 5) * 5
    end = ((max_by // 5) * 5) + 4
    bins = list(range(start, end+2, 5))
    labels = [f"{b}-{b+4}" for b in bins[:-1]]
    primary_cohort = pd.cut(birth_year, bins=bins, right=False, labels=labels, include_lowest=True)

    macro_cohort = birth_year.apply(macro_bin)

    analytic = pd.DataFrame({
        "age": age,
        "sex": sex,
        "sex_label": sex_label,
        "birth_year": birth_year,
        "num_marriages": num_marriages,
        "ever_married": ever_married,
        "remarried_2plus": remarried_2plus,
        "num_cohab_partners": num_cohab_partners,
        "ever_cohabited": ever_cohabited,
        "ever_partnered": ever_partnered,
        "age_le_35": age_le_35,
        "cohort_primary": primary_cohort,
        "cohort_macro": macro_cohort,
        "src_age_var": df[age_src],
        "src_sex_var": df[sex_src],
        "src_MI40_married_since": df[married_since_src],
        "src_MI41_times_married_since": df[marriages_src],
        "src_MI42_cohab_since": df[cohab_since_src],
        "src_MI140_num_cohab_partners": df[cohab_n_src],
    })

    out_analytic = out_dir / "NSFH_Wave2_analytic_replication_ready.xlsx"
    out_tables = out_dir / "NSFH_Wave2_tables.xlsx"

    with pd.ExcelWriter(out_analytic, engine="openpyxl") as writer:
        analytic.to_excel(writer, sheet_name="analytic", index=False)

    tab_all = cohort_sex_table(analytic, "cohort_primary", only_present=False, min_n=args.min_n)
    tab_present = cohort_sex_table(analytic, "cohort_primary", only_present=True, min_n=args.min_n)
    gap = gap_table(tab_present, "cohort_primary")

    with pd.ExcelWriter(out_tables, engine="openpyxl") as writer:
        tab_all.to_excel(writer, sheet_name="primary_all", index=False)
        tab_present.to_excel(writer, sheet_name="primary_present", index=False)
        gap.to_excel(writer, sheet_name="ever_partnered_gap", index=False)

    print(f"Wrote: {out_analytic}")
    print(f"Wrote: {out_tables}")

if __name__ == "__main__":
    main()
