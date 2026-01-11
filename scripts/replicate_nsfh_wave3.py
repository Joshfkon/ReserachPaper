#!/usr/bin/env python3
"""
replicate_nsfh_wave3.py

Replicates the NSFH Wave 1/2 analytic pipeline for NSFH Wave 3 (2001–2003).
Designed to produce stacking-ready outputs with identical variable names.

Expected inputs (TSV):
- 00171-0001-Data.tsv  (Main respondent interview file; contains DOB + interview date fields and TYPE)
- 00171-0002-Data.tsv  (Household roster; contains respondent gender/sex and respondent marital status per NSFH FAQ)

Outputs:
- NSFH_Wave3_analytic_replication_ready.xlsx  (sheet: analytic)
- NSFH_Wave3_tables.xlsx                     (sheets: primary_all, primary_present, ever_partnered_gap)
"""

from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

# ----------------------------
# Helpers
# ----------------------------

def _clean_str(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().replace({"": np.nan, ".": np.nan})

def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(_clean_str(s), errors="coerce")

def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols_upper = {c.upper(): c for c in df.columns}
    for cand in candidates:
        if cand.upper() in cols_upper:
            return cols_upper[cand.upper()]
    # fall back to contains
    for cand in candidates:
        for c in df.columns:
            if cand.upper() == c.upper():
                return c
    return None

def compute_age(dob_year2: pd.Series, dob_month: pd.Series, int_year: pd.Series, int_month: pd.Series, int_day: pd.Series) -> pd.Series:
    """
    DOBY in DS0001 is 2-digit year. We map it to 1900+DOBY by default.
    Age is computed using interview date and (month, year) DOB; day is assumed 15 (mid-month) since DOB day isn't provided.
    """
    y2 = _to_num(dob_year2)
    m = _to_num(dob_month)
    iy = _to_num(int_year)
    im = _to_num(int_month)
    iday = _to_num(int_day)

    # Map DOBY to 4-digit: assume 1900s by default.
    by = 1900 + y2

    # Construct dates
    # Day-of-birth not present; assume 15th.
    dob = pd.to_datetime(dict(year=by, month=m.fillna(6).astype(int), day=15), errors="coerce")
    iv = pd.to_datetime(dict(year=iy.astype(int), month=im.fillna(6).astype(int), day=iday.fillna(15).astype(int)), errors="coerce")

    age = np.floor((iv - dob).dt.days / 365.25)
    return age

def sex_label_from_code(sex: pd.Series) -> pd.Series:
    return sex.map({1: "Male", 2: "Female"})

def make_primary_cohort(birth_year: pd.Series) -> pd.Categorical:
    """
    Start with Wave-1-like 10-year bins; adjust only if sample support forces it.
    Here we implement 1940-49, 1950-59, 1960-69, 1970-79, 1980-89, 1990-99 (as needed).
    """
    bins = [-np.inf, 1939, 1949, 1959, 1969, 1979, 1989, 1999, np.inf]
    labels = ["≤1939","1940–49","1950–59","1960–69","1970–79","1980–89","1990–99","≥2000"]
    return pd.cut(birth_year, bins=bins, labels=labels, right=True, ordered=True)

def make_macro_cohort(birth_year: pd.Series) -> pd.Categorical:
    bins = [-np.inf, 1949, 1959, 1969, 1979, 1979, 1979, 1979, np.inf]  # placeholder; overwritten below
    # Use required macro cohorts:
    # ≤1949, 1950–59, 1960–69, 1970–79, ≥1980
    bins = [-np.inf, 1949, 1959, 1969, 1979, np.inf]
    labels = ["≤1949","1950–59","1960–69","1970–79","≥1980"]
    return pd.cut(birth_year, bins=bins, labels=labels, right=True, ordered=True)

# ----------------------------
# Main
# ----------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave3_main_tsv", type=str, default="00171-0001-Data.tsv")
    ap.add_argument("--wave3_roster_tsv", type=str, default="00171-0002-Data.tsv")
    ap.add_argument("--out_dir", type=str, default=".")
    ap.add_argument("--interview_year_mode", type=int, default=2002, help="Use modal Wave 3 interview year for birth_year construction (default 2002).")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    main_path = Path(args.wave3_main_tsv)
    roster_path = Path(args.wave3_roster_tsv)

    if not main_path.exists():
        raise FileNotFoundError(f"Missing main TSV: {main_path}")
    if not roster_path.exists():
        raise FileNotFoundError(
            f"Missing household roster TSV: {roster_path}\n"
            "NSFH FAQ indicates respondent gender and marital status in Wave 3 are in the household roster file."
        )

    # Load
    df_main = pd.read_csv(main_path, sep="\t", low_memory=False, dtype=str)
    df_roster = pd.read_csv(roster_path, sep="\t", low_memory=False, dtype=str)

    # Keep main respondents only (TYPE == 'R') to match Wave 1/2 respondent universe.
    if "TYPE" in df_main.columns:
        df_main = df_main[df_main["TYPE"].astype(str).str.strip().eq("R")].copy()

    # Merge on CASENUM (numeric case id) if possible, else CASEID
    key_main = "CASENUM" if "CASENUM" in df_main.columns else ("CASEID" if "CASEID" in df_main.columns else None)
    key_roster = "CASENUM" if "CASENUM" in df_roster.columns else ("CASEID" if "CASEID" in df_roster.columns else None)
    if key_main is None or key_roster is None:
        raise ValueError("Could not find a merge key in both files (CASENUM or CASEID).")
    df = df_main.merge(df_roster, left_on=key_main, right_on=key_roster, how="left", suffixes=("", "_roster"))

    # Identify required columns
    dobm = find_col(df, ["DOBM"])
    doby = find_col(df, ["DOBY"])
    idatyy = find_col(df, ["IDATYY", "INTYY", "INTERVIEW_YEAR"])
    idatmm = find_col(df, ["IDATMM", "INTMM"])
    idatdd = find_col(df, ["IDATDD", "INTDD"])

    # respondent sex + marital status are expected in roster
    sex_col = find_col(df, ["SEX_A", "SEXA", "RSEX", "SEX"])
    ms_col = find_col(df, ["MS_A", "MSA", "RMS", "MARSTAT", "MS"])
    mb_col = find_col(df, ["MB_A", "MBA", "MB"])  # first marriage vs married before
    coh_col = find_col(df, ["COH_A", "COHA", "COH"])  # cohab status (may be present)

    missing_cols = [name for name,val in {
        "DOBM": dobm, "DOBY": doby, "IDATYY": idatyy, "IDATMM": idatmm, "IDATDD": idatdd,
        "SEX": sex_col, "MS": ms_col
    }.items() if val is None]
    if missing_cols:
        raise ValueError(
            f"Missing required columns after merge: {missing_cols}\n"
            f"Found columns in roster: {list(df_roster.columns)[:50]} ...\n"
            "If the roster variable names differ, add them to the candidate lists in find_col()."
        )

    # Construct age from DOB + interview date
    age = compute_age(df[doby], df[dobm], df[idatyy], df[idatmm], df[idatdd])

    sex = _to_num(df[sex_col])
    # Standardize to 1=Male,2=Female if codebook uses that; otherwise user must adjust mapping.
    sex_label = sex_label_from_code(sex)

    interview_year = args.interview_year_mode
    birth_year = interview_year - age

    # Marriages: infer from marital status (ever married) and "first marriage" flag where available.
    ms = _to_num(df[ms_col])
    mb = _to_num(df[mb_col]) if mb_col else pd.Series(np.nan, index=df.index)

    # Expect ms codes: 1 married, 2 separated, 3 divorced, 4 widowed, 5 never married.
    ever_married = ms.isin([1,2,3,4]).astype(float)
    # remarried indicator only meaningful among currently/ever married; use mb==2 ("married before") when available.
    remarried_2plus = ((ever_married == 1) & (mb == 2)).astype(float)

    # Build num_marriages to match Wave 1 variable structure; when only indicator info exists, set to {0,1,2}
    num_marriages = pd.Series(np.nan, index=df.index, dtype="float")
    num_marriages.loc[ever_married==0] = 0
    num_marriages.loc[(ever_married==1) & (remarried_2plus==0)] = 1
    num_marriages.loc[remarried_2plus==1] = 2

    # Cohabitation partners: Wave 3 does not reliably include a lifetime count in the respondent file set used here.
    # Provide NA for num_cohab_partners unless an explicit count is present.
    num_cohab_partners = pd.Series(np.nan, index=df.index, dtype="float")

    # ever_cohabited: if a cohab status variable exists, use YES(1) as indicator (this is "currently living with a partner" in some rosters)
    if coh_col:
        coh = _to_num(df[coh_col])
        ever_cohabited = coh.eq(1).astype(float)
    else:
        ever_cohabited = pd.Series(np.nan, index=df.index, dtype="float")

    ever_partnered = ((ever_married==1) | (ever_cohabited==1)).astype(float)

    age_le_35 = age.le(35).astype(float)

    primary_cohort = make_primary_cohort(birth_year)
    macro_cohort = make_macro_cohort(birth_year)

    analytic = pd.DataFrame({
        "caseid": df[key_main].astype(str).str.strip(),
        "interview_year_mode": interview_year,
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
        "primary_cohort": primary_cohort.astype(str),
        "macro_cohort": macro_cohort.astype(str),
        # raw audit columns
        "raw_DOBM": _to_num(df[dobm]),
        "raw_DOBY": _to_num(df[doby]),
        "raw_IDATYY": _to_num(df[idatyy]),
        "raw_IDATMM": _to_num(df[idatmm]),
        "raw_IDATDD": _to_num(df[idatdd]),
        f"raw_{sex_col}": _to_num(df[sex_col]),
        f"raw_{ms_col}": _to_num(df[ms_col]),
        f"raw_{mb_col}": _to_num(df[mb_col]) if mb_col else np.nan,
        f"raw_{coh_col}": _to_num(df[coh_col]) if coh_col else np.nan,
    })

    # ----------------------------
    # Tables (age <= 35, cohort x sex)
    # ----------------------------
    a35 = analytic[analytic["age_le_35"]==1].copy()

    def cohort_table(data: pd.DataFrame) -> pd.DataFrame:
        # partnered denominator
        partnered = data[data["ever_partnered"]==1].copy()

        gN = data.groupby(["primary_cohort","sex"], dropna=False).size().rename("N").reset_index()

        # P(ever partnered)
        p_partnered = data.groupby(["primary_cohort","sex"])["ever_partnered"].mean().rename("p_ever_partnered").reset_index()

        # Mean # cohab partners | partnered (will be NA in Wave 3 under this file set)
        mean_coh = partnered.groupby(["primary_cohort","sex"])["num_cohab_partners"].mean().rename("mean_num_cohab_partners_given_partnered").reset_index()

        # Mean # marriages | partnered
        mean_mar = partnered.groupby(["primary_cohort","sex"])["num_marriages"].mean().rename("mean_num_marriages_given_partnered").reset_index()

        # P(remarried 2+ | partnered)
        p_rem2 = partnered.groupby(["primary_cohort","sex"])["remarried_2plus"].mean().rename("p_remarried_2plus_given_partnered").reset_index()

        out = gN.merge(p_partnered, on=["primary_cohort","sex"], how="left") \
                .merge(mean_coh, on=["primary_cohort","sex"], how="left") \
                .merge(mean_mar, on=["primary_cohort","sex"], how="left") \
                .merge(p_rem2, on=["primary_cohort","sex"], how="left")

        out["sex_label"] = out["sex"].map({1:"Male",2:"Female"})
        return out.sort_values(["primary_cohort","sex"])

    primary_all = cohort_table(a35)

    # primary_present: keep cohorts where both sexes have N>=200 (threshold can be adjusted)
    thresh = 200
    counts = primary_all.pivot_table(index="primary_cohort", columns="sex", values="N", aggfunc="first")
    keep = counts.dropna().loc[(counts[1]>=thresh) & (counts[2]>=thresh)].index.tolist()
    primary_present = primary_all[primary_all["primary_cohort"].isin(keep)].copy()

    # ever_partnered_gap: Female - Male gap in P(ever_partnered)
    gap = primary_all.pivot_table(index="primary_cohort", columns="sex", values="p_ever_partnered", aggfunc="first")
    gap = (gap[2] - gap[1]).rename("female_minus_male_gap_p_ever_partnered").reset_index()

    # Write Excel outputs
    analytic_xlsx = out_dir / "NSFH_Wave3_analytic_replication_ready.xlsx"
    tables_xlsx = out_dir / "NSFH_Wave3_tables.xlsx"

    with pd.ExcelWriter(analytic_xlsx, engine="openpyxl") as xw:
        analytic.to_excel(xw, sheet_name="analytic", index=False)

    with pd.ExcelWriter(tables_xlsx, engine="openpyxl") as xw:
        primary_all.to_excel(xw, sheet_name="primary_all", index=False)
        primary_present.to_excel(xw, sheet_name="primary_present", index=False)
        gap.to_excel(xw, sheet_name="ever_partnered_gap", index=False)

    print(f"Wrote: {analytic_xlsx}")
    print(f"Wrote: {tables_xlsx}")

if __name__ == "__main__":
    main()
