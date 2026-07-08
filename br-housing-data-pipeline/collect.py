"""
collect.py — ONE command collects all automatable sources up to the most
recent available date.

Run:
    python collect.py

What it collects (all via API or direct URL, with snapshot + hash + vintage):
  1. BCB/SGS (Brazilian Central Bank time series, monthly, ~1-2 month lag):
     mortgage delinquency, Selic policy rate, IPCA inflation, credit stock.
  2. MCMV housing program files (FGTS/OGU microdata) and the OSU federal
     subsidy budget, from direct URLs. The most recent MCMV subsidy figure
     comes FROM A FILE: mcmv_fgts_sintetico (the `_202512` in the filename
     is a publication label; the internal data_referencia is 2025-07-11).
     The OSU gives the long annual history. There is NO monthly MCMV
     subsidy series available via API.

At the end it prints a FRESHNESS REPORT: how recent each source is.

Run `python collect.py --build` to assemble the monthly analysis panel
(painel_analise.csv) from the snapshots — never from the live API.

Design principle: collection and analysis are separated by immutable,
hashed snapshots. Any analysis built on top is reproducible and auditable
against the exact bytes that were downloaded, with a vintage log recording
when each pull happened and what it contained.

Dependencies: requests, pandas   (pip install requests pandas)
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
import pandas as pd   # used only in --build (panel assembly)

SNAP_DIR = Path("snapshots")
API_MANIFEST = Path("manifest.csv")            # BCB series
DL_MANIFEST = Path("downloads_manifest.csv")   # files (MCMV/OSU)
VINTAGE_LOG = Path("vintage_log.csv")
PANEL_OUT = Path("painel_analise.csv")         # assembled monthly panel (--build)
UA = {"User-Agent": "br-housing-data-pipeline/1.0"}

# =========================================================================== #
# 1. BCB/SGS via API (monthly)
# =========================================================================== #
SERIES_BCB = {
    21149: "inad_direcionado_pf_imob_taxas_mercado",
    21151: "inad_direcionado_pf_imob_total",
    4390:  "selic_acum_mes_anualizada",
    433:   "ipca_mensal",
    20610: "saldo_direcionado_pf_imob_taxas_mercado",
}
SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"


def _iter_windows(start: str, end: str):
    d0 = dt.datetime.strptime(start, "%d/%m/%Y").date()
    d1 = dt.datetime.strptime(end, "%d/%m/%Y").date()
    while d0 <= d1:
        ce = min(d0.replace(year=d0.year + 9, month=12, day=31), d1)
        yield d0.strftime("%d/%m/%Y"), ce.strftime("%d/%m/%Y")
        d0 = ce + dt.timedelta(days=1)


def _sgs_window(code, ini, fim, depth=0):
    r = requests.get(SGS_URL.format(code=code),
                     params={"formato": "json", "dataInicial": ini, "dataFinal": fim},
                     timeout=120, headers=UA)
    r.raise_for_status()
    body = r.text.strip()
    if not body:
        return []
    if body[0] == "<":  # HTML error page (window too large for a daily series): subdivide
        d0 = dt.datetime.strptime(ini, "%d/%m/%Y").date()
        d1 = dt.datetime.strptime(fim, "%d/%m/%Y").date()
        if depth >= 8 or d0 >= d1:
            raise RuntimeError(f"SGS {code}: window {ini}..{fim} rejected")
        mid = d0 + (d1 - d0) // 2
        return (_sgs_window(code, ini, mid.strftime("%d/%m/%Y"), depth + 1) +
                _sgs_window(code, (mid + dt.timedelta(days=1)).strftime("%d/%m/%Y"), fim, depth + 1))
    return r.json()


def coletar_bcb() -> list[dict]:
    SNAP_DIR.mkdir(exist_ok=True)
    hoje = dt.date.today().strftime("%d/%m/%Y")
    metas = []
    for code, nome in SERIES_BCB.items():
        try:
            rows, seen = [], set()
            for ini, fim in _iter_windows("01/01/2004", hoje):
                for row in _sgs_window(code, ini, fim):
                    if row["data"] not in seen:
                        seen.add(row["data"]); rows.append(row)
            metas.append(_snap_serie(code, nome, rows))
            print(f"[BCB] {code} {nome}: {len(rows)} obs, through {metas[-1]['ultima_obs']}")
        except Exception as e:
            print(f"[BCB][FAIL] {code} {nome}: {e}", file=sys.stderr)
    if metas:
        _write_csv(API_MANIFEST, metas); _append_csv(VINTAGE_LOG, metas)
    return metas


def _snap_serie(code, nome, rows):
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()
    dia = dt.date.today().isoformat()
    (SNAP_DIR / f"{code}_{nome}_{dia}.json").write_bytes(raw)
    datas = sorted(dt.datetime.strptime(r["data"], "%d/%m/%Y").date() for r in rows) if rows else []
    f = lambda d: d.strftime("%d/%m/%Y")
    return {"codigo": code, "nome": nome,
            "url": SGS_URL.format(code=code) + "?formato=json",
            "arquivo": str(SNAP_DIR / f"{code}_{nome}_{dia}.json"),
            "pulled_at": dt.datetime.now().isoformat(timespec="seconds"),
            "sha256": hashlib.sha256(raw).hexdigest(), "n_obs": len(rows),
            "primeira_obs": f(datas[0]) if datas else "", "ultima_obs": f(datas[-1]) if datas else ""}


# =========================================================================== #
# Step 2 (monthly MCMV subsidy via Portal da Transparência): out of scope.
# Reason: the API does not deliver a MONTHLY, MCMV-SPECIFIC series in one
# call — mesLancamento is ignored in /despesas/por-orgao, and the 'acao'
# filter only exists in /despesas/por-funcional-programatica, which is
# ANNUAL. Caveat: collecting via por-orgao would bring the ENTIRE spending
# of agency 56000 (Ministry of Cities) under the label "MCMV subsidy" —
# misleading. The recent MCMV subsidy already comes from the file below
# (mcmv_fgts_sintetico) and the OSU provides the long annual history.
# A real MONTHLY route exists via /api-de-dados/despesas/documentos (by
# UG/gestão, mandatory phase, filtered by issue date); it was left out on
# effort/fragility grounds — a good starting point if monthly granularity
# is ever needed.
# =========================================================================== #


# =========================================================================== #
# 2. MCMV/OSU files (direct URL) — verified on 2026-07-06
# =========================================================================== #
FONTES_ARQ = [
    ("mcmv_fgts_sintetico",  # << the most recent MCMV subsidy on file (through Jul/2025)
     "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/habitacao/programa-minha-casa-minha-vida/arquivos/dados_abertos_FGTS_SINTETICO_202512.csv"),
    ("mcmv_ogu_empreendimentos",
     "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/habitacao/programa-minha-casa-minha-vida/arquivos/view_dados_abertos_ogu_202603201556.zip"),
    ("osu_subsidios",  # long history, but lagged (through ~2021)
     "https://www.gov.br/planejamento/pt-br/assuntos/avaliacao-de-politicas-publicas/subsidios/transparencia-de-subsidios-da-uniao/orcamento-de-subsidios-da-uniao-osu/osu_2022-anexo-estatistico-6a-edicao.xlsx/@@download/file"),
]


def _extensao(url, ct):
    ext = Path(urlparse(url).path).suffix.lower().lstrip(".")
    if ext:
        return ext
    return {"text/csv": "csv", "application/zip": "zip",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx"
            }.get(ct.split(";")[0].strip(), "bin")


def coletar_arquivos() -> list[dict]:
    SNAP_DIR.mkdir(exist_ok=True)
    metas = []
    for nome, url in FONTES_ARQ:
        try:
            r = requests.get(url, timeout=300, headers=UA); r.raise_for_status()
            c = r.content; ct = r.headers.get("Content-Type", "")
            if c[:64].lstrip().lower().startswith((b"<!doctype", b"<html")) or "text/html" in ct:
                raise RuntimeError("got HTML (page URL or 404?), not the file")
            dia = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
            arq = SNAP_DIR / f"{nome}_{dia}.{_extensao(url, ct)}"
            arq.write_bytes(c)
            meta = {"nome": nome, "url": url, "arquivo": str(arq),
                    "pulled_at": dt.datetime.now().isoformat(timespec="seconds"),
                    "sha256": hashlib.sha256(c).hexdigest(), "bytes": len(c), "content_type": ct}
            metas.append(meta)
            print(f"[FILE] {nome}: {len(c):,} bytes -> {arq.name}")
        except Exception as e:
            print(f"[FILE][FAIL] {nome}: {e}  (re-check the current filename on the source page)",
                  file=sys.stderr)
    if metas:
        _append_csv(DL_MANIFEST, metas)
    return metas


# =========================================================================== #
# 3. MONTHLY panel assembly from snapshots (--build), never from the live API.
# =========================================================================== #
def _latest_snapshot(code: int, name: str) -> Path:
    cands = sorted(SNAP_DIR.glob(f"{code}_{name}_*.json"))
    if not cands:
        raise FileNotFoundError(f"No snapshot for {code}_{name}. Run collection first.")
    return cands[-1]


def _load_series(code: int, name: str) -> "pd.Series":
    path = _latest_snapshot(code, name)
    rows = json.loads(path.read_text(encoding="utf-8"))
    df = pd.DataFrame(rows)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"].astype(str).str.replace(",", "."),
                                errors="coerce")
    return df.set_index("data")["valor"].rename(name).sort_index()


def build_panel() -> "pd.DataFrame":
    """Assembles the MONTHLY panel (not annual!). Preserves the original
    frequency. real_rate (% p.a.) = annualized Selic minus 12m IPCA, both
    in % p.a. SGS 4390 comes in % per MONTH (Selic accumulated IN the
    month, ~0.9 in 2024). Annualize by compounding:
    selic_aa = ((1+am/100)^12 - 1)*100. Checked against the known policy
    target (Aug/2020: 0.16%/mo -> 1.94%/yr ~ 2%; May/2024: 0.83 -> 10.43
    ~ 10.5). Uses 4390 (monthly) instead of 432 (daily): ~1 obs/month, no
    resampling. Does NOT collapse to annual means — keeping the panel
    monthly is what avoids throwing away ~90% of the variation."""
    inad = _load_series(21149, SERIES_BCB[21149])
    selic_am = _load_series(4390, SERIES_BCB[4390])   # % per month (accumulated in month)
    ipca_m = _load_series(433, SERIES_BCB[433])

    # Annualized Selic (% p.a.) by monthly compounding — same unit as 12m IPCA:
    selic_aa = (((1 + selic_am / 100) ** 12 - 1) * 100).rename("selic_aa")

    # 12-month cumulative IPCA (%), from the monthly series:
    fator = (1 + ipca_m / 100)
    ipca_12m = (fator.rolling(12).apply(lambda x: x.prod(), raw=True) - 1) * 100

    juro_real = (selic_aa - ipca_12m).rename("juro_real_aa")

    panel = pd.concat([inad.rename("inadimplencia"),
                       selic_aa,
                       ipca_12m.rename("ipca_12m"),
                       juro_real], axis=1)
    panel = panel.dropna(subset=["inadimplencia"])
    panel.index.name = "data"
    panel.to_csv(PANEL_OUT)
    print(f"[BUILD] monthly panel ({len(panel)} rows, "
          f"{panel.index.min().date()}..{panel.index.max().date()}) -> {PANEL_OUT}")
    return panel


# =========================================================================== #
# util + freshness report
# =========================================================================== #
def _write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def _append_csv(path, rows):
    novo = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if novo:
            w.writeheader()
        w.writerows(rows)


def relatorio_frescor(bcb, arqs):
    print("\n" + "=" * 68)
    print("FRESHNESS REPORT — how recent each source is")
    print("=" * 68)
    for m in bcb:
        print(f"  BCB {m['codigo']:>6} {m['nome'][:34]:34s} -> {m['ultima_obs']}")
    # MCMV subsidy: the FRESHEST source is the FGTS synthetic file, not the API.
    fgts = next((m for m in arqs if m["nome"] == "mcmv_fgts_sintetico"), None)
    if fgts:
        print(f"  MCMV SUBSIDY (FGTS synthetic, file)        -> {Path(fgts['arquivo']).name}")
    else:
        print(f"  MCMV SUBSIDY (FGTS synthetic, file)        -> FAILED (re-check the URL)")
    for m in arqs:
        print(f"  FILE {m['nome'][:33]:33s} -> {Path(m['arquivo']).name} ({m['bytes']:,} B)")
    print("=" * 68)
    print("Lag: BCB ~1-2 months | MCMV subsidy = FGTS synthetic file (~quarterly,")
    print("through Jul/2025) + OSU (annual, long history, ~2021). No monthly API exists.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Collects BCB/MCMV data and builds the panel.")
    ap.add_argument("--build", action="store_true",
                    help="assemble the monthly panel from snapshots (no collection)")
    args = ap.parse_args()
    if args.build:
        build_panel()
    else:
        print(">>> Collecting (BCB + MCMV/OSU files)...")
        bcb = coletar_bcb()
        arqs = coletar_arquivos()
        relatorio_frescor(bcb, arqs)


# =========================================================================== #
# DESIGN NOTES — read before reusing, to avoid common traps
# =========================================================================== #
# 1. OUTCOME CHOICE: series 21149 is SECTORAL delinquency for market-rate
#    residential mortgages, not the delinquency of any specific credit
#    portfolio. If the object of study is a specific portfolio, use its own
#    data as the outcome; if unavailable, 21149 can serve as a PROXY, but
#    only declared explicitly as such, with the level difference between
#    portfolio and sector treated as a source of uncertainty.
# 2. FREQUENCY: good practice is to keep the panel MONTHLY — collapsing to
#    ~11 annual points discards most of the variation.
# 3. SUBSIDIES: they do not enter the BCB panel because the source
#    (Treasury/SIAFI MCMV subventions, and MCMV microdata by municipality
#    and year) lives on a different portal; they are collected as files
#    (FGTS/OGU/OSU, see FONTES_ARQ) under the same snapshot+hash pattern.
#    The rich variation is in the municipality x year panel (4,800+
#    municipalities), not in the annual national series.
# 4. VALIDATION before any model: unit root tests (ADF/KPSS), and compare
#    the model against baselines (linear trend and AR(1)) in a rolling
#    out-of-sample backtest — in-sample R2 alone validates nothing.
# =========================================================================== #

