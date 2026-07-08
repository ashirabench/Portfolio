# Nighttime Lights Urban Expansion Screening

Screens ~150 municipalities in the Brazilian Western Amazon (AM, RR, RO, AC)
for urban expansion using NOAA VIIRS DNB monthly nighttime radiance, pulled
through Google Earth Engine. The output is a ranked shortlist of
municipalities whose nighttime light grew fastest since 2019, with honest
uncertainty and a robustness core.

## Why the statistics matter here

Each municipality has one observation per year, so a naive trend fit is
fragile and a naive ranking is biased. The pipeline addresses both:

1. **Quality filtering.** Only dry season months (May to October) enter the
   annual series; cloud cover during the Amazon wet season degrades the
   sensor reading. Each image must also pass coverage thresholds.
2. **Systemic panel anomaly guard.** A per city outlier filter cannot catch
   a simultaneous jump across the whole panel, which signals an instrument
   or calibration change rather than real growth. The guard compares panel
   medians of consecutive valid years, annualized across gaps, and rejects
   any year growing above 25% per year. In this data it flags 2025 (+32%).
3. **Robust trend estimation.** Theil-Sen fits the direction of the log
   series without being dragged by extreme years, which allows outlier
   detection via the Iglewicz-Hoaglin modified z score (MAD based). OLS on
   the cleaned series then provides the point estimate and its exact
   standard error.
4. **Empirical Bayes shrinkage.** Ranking many noisy growth rates suffers
   from the winner's curse: the top entries are partly the ones whose noise
   was favorable. A hierarchical normal model with DerSimonian-Laird
   estimation of the between city variance shrinks each rate toward the
   panel mean in proportion to its noise. The ranking uses the posterior
   mean, and the shrinkage factor B_i is reported as an uncertainty column.
5. **Sensitivity analysis.** The full ranking is recomputed with and
   without the excluded year. The intersection of the two top lists is the
   robust core, highlighted in the output table. The set of municipalities
   is more reliable than the exact order within it.

## Interpretation and limits

Nighttime light growth is a working hypothesis for urban expansion,
supported by the remote sensing literature (Henderson, Storeygard and Weil,
2012), not a law. Light can also come from mining, gas flaring or industry.
The reported 95% CI is a floor: it does not propagate the uncertainty of
the outlier removal step. A temporal validation test showed past growth
does not predict next year growth (mild mean reversion), so the ranking is
a screening tool that points where to investigate, not a forecast.

## Running
pip install -r requirements.txt
earthengine authenticate
export GEE_PROJECT="your-gcp-project-id"
python nightlights.py --fetch   # once, slow (~150 municipalities)
python nightlights.py           # analysis from local cache

Data requirement: download the IBGE municipal GDP table (PIB dos
Municípios) as CSV into `data/PIB_Municipios.csv`, keeping the original
column headers. Source:
https://www.ibge.gov.br/estatisticas/economicas/contas-nacionais/9088-produto-interno-bruto-dos-municipios.html

Outputs in `output/`: `table_eb.png` (ranked table with CIs and robust
core), `lines_top.png` (per municipality series with excluded years
marked), `results.csv` (full panel estimates).

## Provenance

A production version of this pipeline was developed during my Digital
Trainee role at Bemol S.A. (retail, Western Amazon), where it ran on
Databricks with custom drawn areas of interest and automated report
distribution. This repository is a sanitized standalone reimplementation
using only public data sources (NOAA VIIRS via GEE, FAO GAUL boundaries,
IBGE GDP), with no internal data, credentials or business logic.

## References

- Henderson, Storeygard, Weil (2012), Measuring Economic Growth from Outer
  Space, American Economic Review.
- Iglewicz, Hoaglin (1993), How to Detect and Handle Outliers.
- DerSimonian, Laird (1986), Meta-analysis in Clinical Trials.
- Efron, Morris (1975), Data Analysis Using Stein's Estimator.
