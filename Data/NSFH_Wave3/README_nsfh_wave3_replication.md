# NSFH Wave 3 Replication Package (2001–2003)

This package replicates the **Wave 1 analytic pipeline** for **NSFH Wave 3** using the raw microdata TSVs and codebooks.

## Inputs (expected)

Place these files in the same folder as the script (or pass paths via CLI):

- `00171-0001-Data.tsv` — Main interview file (contains DOB fields + interview date fields + respondent TYPE)
- `00171-0002-Data.tsv` — Household roster file (NSFH FAQ: contains **respondent gender/sex** and **respondent marital status**)

> The NSFH FAQ explicitly notes that **gender** and **marital status** for the main respondents in NSFH3 are in the **household roster file**.

## Outputs

The script produces two Excel workbooks:

1. `NSFH_Wave3_analytic_replication_ready.xlsx`
   - Sheet: `analytic`
   - Contains ONLY: analytic variables + cohort variables + raw source variables used to derive them (auditability)
   - Does **not** filter the dataset; includes `age_le_35` as an indicator.

2. `NSFH_Wave3_tables.xlsx`
   - Sheets:
     - `primary_all`
     - `primary_present` (cohorts where both sexes have N≥200 among age≤35)
     - `ever_partnered_gap` (Female − Male in P(ever_partnered))

## Variable construction (Wave-1-compatible naming)

### Core
- `age` — computed from DOB (month/year) and interview date (year/month/day)
- `sex` — **expected from household roster** (standardized to 1=Male, 2=Female)
- `sex_label` — Male/Female
- `birth_year = interview_year_mode − age`
  - `interview_year_mode` defaults to **2002** (modal interview year in Wave 3 fieldwork)

### Marriage / partnering
- `ever_married = 1` if marital status indicates ever married (married/separated/divorced/widowed)
- `remarried_2plus = 1` if ever married AND roster indicates “married before” (when available)
- `num_marriages` — derived to preserve Wave-1-style variable:
  - 0 if never married
  - 1 if ever married and not remarried
  - 2 if remarried (2+)

### Cohabitation
- `num_cohab_partners` — **NA** under the Wave 3 file set used here unless an explicit lifetime count exists in your merged inputs.
- `ever_cohabited` — if a cohabitation-status variable exists, uses YES(1). (Note: in some rosters this is “currently living with a partner”.)

### Combined
- `ever_partnered = 1` if `ever_married` OR `ever_cohabited`
- `age_le_35 = 1` if age ≤ 35

## Cohorts

### Primary analytic cohorts
Default 10-year bins:
- ≤1939, 1940–49, 1950–59, 1960–69, 1970–79, 1980–89, 1990–99, ≥2000

### Macro cohorts
- ≤1949
- 1950–59
- 1960–69
- 1970–79
- ≥1980

## Notes / deviations vs Wave 1

1. **Sex + marital status source**  
   Wave 3 stores respondent gender and marital status in the household roster file (per NSFH FAQ). The script therefore merges `00171-0001` with `00171-0002`.

2. **Number of cohabiting partners**  
   Wave 3 does not reliably expose a clean lifetime count of cohabiting partners in the file set used here. The script outputs `num_cohab_partners = NA` unless an explicit count is added to the merge inputs.

## Run

```bash
python replicate_nsfh_wave3.py --out_dir .
```

Optional flags:

- `--wave3_main_tsv PATH`
- `--wave3_roster_tsv PATH`
- `--interview_year_mode 2002`
