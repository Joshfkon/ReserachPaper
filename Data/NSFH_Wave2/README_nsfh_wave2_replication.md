# NSFH Wave 2 (1992–94) Replication Package

This folder contains a replication-ready extract and tables for NSFH Wave 2 (1992–94), designed to mirror the Wave 1 analytic package **as closely as the Wave 2 instrument allows**, while preserving naming conventions so outputs can be stacked mechanically.

## Inputs

- Raw microdata (TSV): DS0001 main respondent file used here
  - `06906-0001-Data.tsv`

## Outputs

1) **NSFH_Wave2_analytic_replication_ready.xlsx**
- Sheet: `analytic`
- Contains only:
  - Analytic variables
  - Cohort variables
  - Raw source variables used to derive them (for auditability)
- No filtering is applied; `age_le_35` is provided as an indicator.

2) **NSFH_Wave2_tables.xlsx**
- Sheets:
  - `primary_all`
  - `primary_present`
  - `ever_partnered_gap`

## Variable definitions (analytic sheet)

### Core
- `age` = `MA8` (missing codes recoded to NA)
- `sex` = `MA7` (1=Male, 2=Female)
- `sex_label` = "Male"/"Female"
- `birth_year` = `1993` − `age`
- `age_le_35` = 1 if `age` ≤ 35 else 0

### Partnering / unions (Wave-2-specific deviations)

Wave 1 used:
- `num_marriages` from lifetime number of marriages (Wave1 `M95`)
- `num_cohab_partners` from lifetime number of cohabiting partners (Wave1 `NUMCOHAB`)

**Wave 2 does not contain direct lifetime equivalents in DS0001.** The closest instrument-provided items are:

- `num_marriages` = `MI41` (**times married since NSFH1**, range 1–3+, with 7/8/9 as missing)
- `num_cohab_partners` = `MI140` (**number of co-residential partners since last marriage ended**, top-coded at 6+; 7/8/9 missing)

Derived indicators:
- `ever_married` = 1 if (`MI40`==1) or (`MI41` ≥ 1)
- `remarried_2plus` = 1 if `MI41` ≥ 2
- `ever_cohabited` = 1 if (`MI42`==1) or (`MI140` ≥ 1)
- `ever_partnered` = 1 if ever_married OR ever_cohabited

These are documented here because they are **forced by Wave 2 instrument structure**; they are not intended to “improve” or reinterpret concepts.

## Cohorts

### Primary analytic cohorts (`cohort_primary`)
- Constructed from `birth_year`
- 5-year bins automatically derived from the observed `birth_year` range among respondents with `age_le_35==1`
- Labels: `YYYY-YYYY+4`

### Macro cohorts (`cohort_macro`)
- ≤1949
- 1950–59
- 1960–69
- 1970–79
- ≥1980

## Tables (NSFH_Wave2_tables.xlsx)

All table Ns are among `age_le_35==1`.

Metrics per cohort × sex:
- `N`
- `P_ever_partnered`
- `Mean_num_cohab_partners_if_partnered`
- `Mean_num_marriages_if_partnered`
- `P_remarried_2plus_if_partnered`

Cohort inclusion rule for `primary_present`:
- Keep cohorts where both sexes have N ≥ 200 (configurable via `--min_n`).

`ever_partnered_gap`:
- Female − Male gap in `P_ever_partnered` by cohort.

## Reproduction

Run:

```bash
python replicate_nsfh_wave2.py --raw_tsv 06906-0001-Data.tsv --out_dir .
```

Options:
- `--interview_year` (default 1993)
- `--min_n` (default 200)

