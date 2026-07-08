# Brazilian Housing Credit Data Pipeline

Reproducible collection of Brazilian public data on housing credit and the
MCMV (Minha Casa Minha Vida) federal housing program: Central Bank (BCB/SGS)
monthly series on mortgage delinquency, the Selic policy rate, IPCA
inflation and directed credit stock, plus MCMV subsidy microdata files
(FGTS/OGU) and the federal subsidy budget (OSU).

## Design: snapshots, hashes, vintages

The core idea is that collection and analysis never touch. Every pull is
saved as an immutable snapshot with a SHA-256 hash, a timestamp and a
manifest row; a vintage log accumulates the history of every pull. The
analysis panel is assembled exclusively from snapshots (`--build`), never
from the live API. Anyone can therefore replicate an analysis against the
exact bytes it was built on, and any silent revision by the data provider
becomes visible as a hash change between vintages.

## Non-obvious data facts encoded here

- BCB SGS rejects large date windows for daily series with an HTML error
  page instead of an HTTP error; the collector detects this and subdivides
  the window recursively.
- Selic: series 4390 (monthly, accumulated in the month) is used instead
  of 432 (daily target). 4390 comes in % per month and is annualized by
  compounding, validated against known policy targets.
- There is no monthly, MCMV-specific subsidy series available via any API.
  The Portal da Transparência endpoints either ignore the month filter or
  only aggregate annually, and the agency-level endpoint would mislabel
  the entire Ministry of Cities budget as MCMV subsidy. The freshest
  subsidy figure comes from the FGTS synthetic open-data file (~quarterly
  publication); the OSU provides the long annual history. This dead end is
  documented in the code so nobody re-derives it.
- MCMV file URLs on gov.br change filename on each publication; the
  collector fails loudly with the source page to re-check.

## Running

pip install requests pandas
python collect.py           # collect everything, print freshness report
python collect.py --build   # assemble the monthly panel from snapshots

Outputs: `snapshots/` (raw immutable pulls), `manifest.csv` and
`downloads_manifest.csv` (current state), `vintage_log.csv` (pull history),
`painel_analise.csv` (monthly panel: delinquency, annualized Selic, 12m
IPCA, real rate).

## Provenance

Built for an investment research workflow analyzing Brazilian real estate
credit funds, where reproducibility and data vintage control were
requirements for independent replication by a second analyst. This public
version uses only public data sources and contains no client information.

## Sources

- Banco Central do Brasil, SGS (Sistema Gerenciador de Séries Temporais)
- Ministério das Cidades, MCMV open data (FGTS/OGU)
- Ministério do Planejamento, Orçamento de Subsídios da União (OSU)
