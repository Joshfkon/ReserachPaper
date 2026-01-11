# NSFH Wave 1 Replication Package (Turnkey)

This package contains a replication-ready analytic extract derived from NSFH Wave 1 (1987–88) and a script that reproduces the core cohort×sex tables.

## Files
- **NSFH_Wave1_analytic_replication_ready.xlsx**
  - Sheet: `analytic`
  - Only analytic variables + cohort construction (plus raw source variables used to derive them for auditability).
- **NSFH_Wave1_tables.xlsx**
  - `primary_all`: cohort×sex table for all primary cohorts in the age≤35 sample
  - `primary_present`: same table restricted to cohorts where both sexes have N≥200
  - `ever_partnered_gap`: female–male gap in P(ever partnered) for `primary_present`
- **replicate_nsfh_wave1.py**
  - End-to-end script: reads the raw TSV and produces both Excel outputs.

## Requirements
- Python 3.9+
- pandas, numpy, xlsxwriter

Install:
```bash
pip install pandas numpy xlsxwriter
```

## How to run
Ensure the raw data file is at:
`/mnt/data/06041-0001-Data.tsv`

Run:
```bash
python replicate_nsfh_wave1.py
```

Outputs:
- `/mnt/data/NSFH_Wave1_analytic_replication_ready.xlsx`
- `/mnt/data/NSFH_Wave1_tables.xlsx`

## Variable Definitions (analytic file)
- `age` = `M2BP01`
- `sex` = `M2DP01` (1=Male, 2=Female), plus `sex_label`
- `birth_year` = 1987 − age (Wave 1 is 1987–88; 1987 used for consistency)
- `num_marriages` = `M95` with 99 treated as missing
- `ever_married` = 1 if `num_marriages` ≥ 1
- `remarried_2plus` = 1 if `num_marriages` ≥ 2
- `num_cohab_partners` = `NUMCOHAB`
- `ever_cohabited` = 1 if `num_cohab_partners` ≥ 1
- `ever_partnered` = 1 if ever married OR ever cohabited
- `age_le_35` = 1 if age ≤ 35 (indicator only; the extract keeps all cases)

### Cohorts
- `birth_cohort_primary`: 1952–56, 1957–60, 1961–64, 1965–68, 1969–72 (tailored to the age≤35 observable window)
- `birth_cohort_macro`: ≤1949, 1950–59, 1960–69, 1970–79, ≥1980 (narrative framing)

## Auditability
The analytic file retains raw source variables used for derivations (`M2BP01`, `M2DP01`, `NUMCOHAB`, `M95`).
