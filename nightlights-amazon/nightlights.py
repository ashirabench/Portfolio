"""
Nighttime Lights Urban Expansion Screening
==========================================

Screens municipalities in the Brazilian Western Amazon for urban expansion
using NOAA VIIRS DNB monthly nighttime radiance, retrieved through Google
Earth Engine.

Method, in order:
  1. Quality filtering: dry season months only (May to October), per image
     cloud free coverage thresholds.
  2. Panel level anomaly guard: rejects years with implausible simultaneous
     jumps across the whole panel,
     annualizing ratios across gaps so previously excluded years do not
     create false positives.
  3. Robust per municipality trend: Theil-Sen slope on log radiance to
     detect outlier years (Iglewicz-Hoaglin modified z score with MAD),
     then OLS on the cleaned series for the point estimate and its exact
     standard error.
  4. Empirical Bayes shrinkage (DerSimonian-Laird) to correct the winner's
     curse, since rankings over many noisy series systematically overstate the
     top entries.
  5. Sensitivity analysis: the ranking is recomputed with and without the
     excluded years. The intersection is reported as the robust core.

Setup:
    pip install -r requirements.txt
    earthengine authenticate
    export GEE_PROJECT="your-gcp-project-id"
    # download the IBGE municipal GDP CSV into data/ (see README)

Usage:
    python nightlights.py --fetch    # pull VIIRS series from GEE (slow, run once)
    python nightlights.py            # analysis from the local cache
"""
from __future__ import annotations
import argparse
import os
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats

# ----------------------------- configuration -----------------------------
VIIRS_COLLECTION = "NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG"
RAD_BAND, COV_BAND = "avg_rad", "cf_cvg"
MIN_CF_CVG_MEAN = 3      # min mean cloud free observations per image
MIN_VALID_FRAC  = 0.7    # min fraction of observed pixels in the AOI

# GAUL level 1 state names mapped to UF codes. If a state returns zero
# municipalities during fetch, check the exact ADM1_NAME spelling in GAUL.
STATES = {"Amazonas": "AM", "Roraima": "RR", "Rondonia": "RO", "Acre": "AC"}

ANO_INI         = 2019     # start of the estimation window
EXCLUIR_ANOS    = [2025]   # systemic panel anomaly, caught by the guard below
MIN_ANOS        = 5        # min valid years per municipality
LUM_BASE_MIN    = 1.0      # nW/cm2/sr floor, avoids inflated multiples on a near zero base
CONSIST_MIN     = 0.6      # min share of year over year increases
N_TOP           = 20
POP_MIN         = 15_000   # analysis floor for municipality size
ANOMALIA_LIMIAR = 1.25     # per year panel growth ratio above which a year is rejected

DATA_DIR = Path("data")
OUT_DIR  = Path("output")
CACHE    = DATA_DIR / "viirs_monthly.parquet"
PIB_PATH = DATA_DIR / "PIB_Municipios.csv"   # IBGE municipal GDP, see README

AZUL, ROSA, AZULC, CINZA = "#1F3A5F", "#C2185B", "#DCE6F8", "#8C8C8C"
FS = 17
plt.rcParams.update({"font.size": FS, "figure.facecolor": "white"})


# ------------------------------- ingestion -------------------------------
def fetch():
    """Pulls monthly VIIRS stats per municipality from GEE into a local
    parquet cache. Requires `earthengine authenticate` and GEE_PROJECT."""
    import ee
    from datetime import datetime

    project = os.environ.get("GEE_PROJECT")
    if not project:
        raise SystemExit("Set GEE_PROJECT to your Google Cloud project id.")
    ee.Initialize(project=project)
    DATA_DIR.mkdir(exist_ok=True)

    gaul = (ee.FeatureCollection("FAO/GAUL/2015/level2")
            .filter(ee.Filter.eq("ADM0_NAME", "Brazil"))
            .filter(ee.Filter.inList("ADM1_NAME", list(STATES))))
    adm1 = gaul.aggregate_array("ADM1_NAME").getInfo()
    adm2 = gaul.aggregate_array("ADM2_NAME").getInfo()
    munis = sorted(set(zip(adm1, adm2)))
    print(f"{len(munis)} municipalities in scope: "
          f"{ {s: sum(1 for a, _ in munis if a == s) for s in STATES} }")

    end_date = f"{datetime.now().year}-12-31"

    def get_viirs_city(state, name, aoi):
        col = (ee.ImageCollection(VIIRS_COLLECTION)
               .filterBounds(aoi)
               .filterDate("2014-01-01", end_date)
               .select([RAD_BAND, COV_BAND]))

        def add_stats(img):
            img = img.clip(aoi)
            obs_mask = img.select(COV_BAND).gt(0).rename("obs")
            rad = (img.select(RAD_BAND)
                      .updateMask(obs_mask)
                      .updateMask(img.select(RAD_BAND).gte(0)))
            rad_stats = rad.reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.median(), sharedInputs=True),
                geometry=aoi, scale=500, maxPixels=1e10, tileScale=4)
            valid_frac = obs_mask.toFloat().reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi, scale=500, maxPixels=1e10, tileScale=4).get("obs")
            cf_cvg_mean = img.select(COV_BAND).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi, scale=500, maxPixels=1e10, tileScale=4).get(COV_BAND)
            return ee.Feature(None, {
                "date":        img.date().format("YYYY-MM-dd"),
                "mean_rad":    rad_stats.get(f"{RAD_BAND}_mean"),
                "median_rad":  rad_stats.get(f"{RAD_BAND}_median"),
                "valid_frac":  valid_frac,
                "cf_cvg_mean": cf_cvg_mean})

        rows = ee.FeatureCollection(col.map(add_stats)).getInfo()["features"]
        d = pd.DataFrame([f["properties"] for f in rows])
        if d.empty:
            return d
        d["cidade"] = name
        d["uf"] = STATES[state]
        d["date"] = pd.to_datetime(d["date"])
        for c in ["mean_rad", "median_rad", "valid_frac", "cf_cvg_mean"]:
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d = d.dropna(subset=["mean_rad"]).sort_values("date").reset_index(drop=True)
        d["year"] = d["date"].dt.year
        d["month"] = d["date"].dt.month
        return d

    all_dfs = []
    for state, name in munis:
        try:
            aoi = (gaul.filter(ee.Filter.eq("ADM1_NAME", state))
                       .filter(ee.Filter.eq("ADM2_NAME", name))
                       .geometry())
            d = get_viirs_city(state, name, aoi)
            if not d.empty:
                all_dfs.append(d)
                print(f"ok   {name} ({STATES[state]}): {len(d)} months")
            else:
                print(f"skip {name} ({STATES[state]}): no data")
        except Exception as e:
            print(f"FAIL {name} ({STATES[state]}): {e}")

    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all["date"] = df_all["date"].astype(str)
    df_all.to_parquet(CACHE, index=False)
    print(f"cached {len(df_all)} rows -> {CACHE}")


# -------------------------------- analysis --------------------------------
def normaliza(s):
    s = str(s).lower().strip()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def analyze():
    OUT_DIR.mkdir(exist_ok=True)
    if not CACHE.exists():
        raise SystemExit("No cache found. Run with --fetch first.")
    df = pd.read_parquet(CACHE)
    df["low_cov"] = ((df["cf_cvg_mean"] < MIN_CF_CVG_MEAN) |
                     (df["valid_frac"] < MIN_VALID_FRAC))

    # Annual series: dry season only (May to October), median of monthly
    # medians, at least 3 valid months per year.
    anual = (df[(~df["low_cov"]) & (df["month"].between(5, 10))]
             .groupby(["cidade", "uf", "year"])
             .agg(rad=("median_rad", "median"), n_meses=("median_rad", "count"))
             .reset_index())
    anual = anual[anual["n_meses"] >= 3].copy()

    ANO_FIM = int(anual[~anual["year"].isin(EXCLUIR_ANOS)]["year"].max())
    ANO_ULT = int(anual["year"].max())

    # --- Systemic panel anomaly guard ---
    # Per city MAD cannot catch a simultaneous jump across the whole panel
    # (e.g. an instrument or calibration change). Compare panel medians of
    # consecutive non excluded years, annualizing the ratio by the real gap
    # so a 2 year gap around an excluded year does not trigger falsely.
    _med_painel = (anual[anual["year"] >= ANO_INI]
                   .groupby("year")["rad"].median().sort_index())
    _anos_validos = sorted(int(y) for y in _med_painel.index
                           if int(y) not in EXCLUIR_ANOS)
    for _i in range(1, len(_anos_validos)):
        _y, _y_prev = _anos_validos[_i], _anos_validos[_i - 1]
        _gap = _y - _y_prev
        _ratio_anual = (_med_painel[_y] / _med_painel[_y_prev]) ** (1.0 / _gap)
        assert _ratio_anual < ANOMALIA_LIMIAR, (
            f"SYSTEMIC ANOMALY: year {_y} grew {(_ratio_anual-1)*100:.1f}%/yr "
            f"vs {_y_prev} (threshold {(ANOMALIA_LIMIAR-1)*100:.0f}%/yr). "
            f"Add {_y} to EXCLUIR_ANOS or investigate before publishing.")
    print(f"anomaly guard OK, years checked: {_anos_validos}")

    # --- IBGE municipal GDP: population proxy and market size context ---
    df_pib_raw = pd.read_csv(PIB_PATH)
    df_pib = df_pib_raw[[
        "Ano", "Código do Município", "Nome do Município",
        "Sigla da Unidade da Federação",
        "Produto Interno Bruto, \na preços correntes\n(R$ 1.000)",
        "Produto Interno Bruto per capita, \na preços correntes\n(R$ 1,00)"]].copy()
    df_pib.columns = ["ano", "codigo_ibge", "nome_municipio", "uf",
                      "pib_mil_reais", "pib_per_capita"]
    df_pib["ano"] = pd.to_numeric(df_pib["ano"], errors="coerce").astype(int)
    for c in ["pib_mil_reais", "pib_per_capita"]:
        df_pib[c] = pd.to_numeric(
            df_pib[c].astype(str).str.replace(",", "", regex=False).str.strip(),
            errors="coerce")
    df_pib["nome_norm"] = df_pib["nome_municipio"].apply(normaliza)

    ULTIMO_ANO_PIB = int(df_pib["ano"].max())
    anual["nome_norm"] = anual["cidade"].apply(normaliza)
    pib_snap = (df_pib[df_pib["ano"] == ULTIMO_ANO_PIB]
                .merge(anual[["cidade", "uf", "nome_norm"]].drop_duplicates(),
                       on=["nome_norm", "uf"], how="inner")
                [["cidade", "uf", "pib_mil_reais", "pib_per_capita"]])
    pib_snap["pop"] = pib_snap["pib_mil_reais"] * 1000 / pib_snap["pib_per_capita"]
    unmatched = sorted(set(anual["cidade"]) - set(pib_snap["cidade"]))
    if unmatched:
        print(f"no IBGE match, dropped: {unmatched}")
    pib_snap = pib_snap[pib_snap["pop"] >= POP_MIN].copy()

    # --- Estimation: Theil-Sen detects outlier years, OLS estimates ---
    def crescimento_ols(g, excluir_anos=EXCLUIR_ANOS):
        g = g[(g["year"] >= ANO_INI) & (~g["year"].isin(excluir_anos)) &
              (g["rad"] > 0)].sort_values("year")
        if len(g) < MIN_ANOS:
            return None
        x = g["year"].values.astype(float)
        y = np.log(g["rad"].values)

        ts_slope, ts_int, _, _ = stats.theilslopes(y, x)
        resid = y - (ts_int + ts_slope * x)
        mad = np.median(np.abs(resid - np.median(resid)))
        z_mod = 0.6745 * (resid - np.median(resid)) / (mad if mad > 0 else 1e-9)
        atipico = np.abs(z_mod) > 3.5           # Iglewicz-Hoaglin rule
        if atipico.any() and (~atipico).sum() < MIN_ANOS:
            atipico = np.zeros(len(x), bool)
        xc, yc = x[~atipico], y[~atipico]

        ols = stats.linregress(xc, yc)
        n = len(xc)
        ts_clean, _, _, _ = stats.theilslopes(yc, xc)
        yy = np.diff(yc)
        return pd.Series({
            "beta": ols.slope, "s": ols.stderr,
            "cagr": np.expm1(ols.slope) * 100,
            "beta_ts": ts_clean,
            "consistencia": (yy > 0).mean() if len(yy) else np.nan,
            "n_anos": n,
            "anos_atipicos": ",".join(str(int(a)) for a in x[atipico]) or "-",
            "luz_base": float(np.exp(yc[-2:].mean()))})

    rb = (anual.groupby(["cidade", "uf"]).apply(crescimento_ols)
          .dropna(how="all").reset_index()
          .merge(pib_snap, on=["cidade", "uf"], how="inner"))
    rb = rb[rb["s"] > 0].copy()

    dif = np.abs(np.expm1(rb["beta"]) - np.expm1(rb["beta_ts"])) * 100
    print(f"OLS vs Theil-Sen convergence (p.p.): median {dif.median():.2f} | "
          f"p90 {dif.quantile(0.9):.2f} | max {dif.max():.2f}")
    assert dif.median() <= 2, "High divergence: review cleaning before ranking"

    # --- Empirical Bayes shrinkage (DerSimonian-Laird) ---
    w = 1 / rb["s"]**2
    mu_fixo = np.sum(w * rb["beta"]) / np.sum(w)
    Q = np.sum(w * (rb["beta"] - mu_fixo)**2)
    k = len(rb)
    tau2 = max(0.0, (Q - (k - 1)) / (np.sum(w) - np.sum(w**2) / np.sum(w)))
    assert tau2 > 0, "tau2 = 0: complete pooling, ranking is meaningless"
    w_re = 1 / (rb["s"]**2 + tau2)
    mu = np.sum(w_re * rb["beta"]) / np.sum(w_re)
    print(f"panel: {k} municipalities | mu {np.expm1(mu)*100:.1f}%/yr | "
          f"tau {np.sqrt(tau2)*100:.1f} p.p.")

    B = rb["s"]**2 / (rb["s"]**2 + tau2)
    rb["beta_post"] = (1 - B) * rb["beta"] + B * mu
    rb["sd_post"] = np.sqrt((rb["s"]**2 * tau2) / (rb["s"]**2 + tau2))
    rb["shrink_pct"] = B * 100
    rb["cagr_eb"] = np.expm1(rb["beta_post"]) * 100
    # 95% CI with Student t per city (df_i = n_i - 2), honest for short series
    rb["t_mult"] = rb["n_anos"].apply(lambda n: stats.t.ppf(0.975, df=n - 2))
    rb["cagr_eb_lo"] = np.expm1(rb["beta_post"] - rb["t_mult"] * rb["sd_post"]) * 100
    rb["cagr_eb_hi"] = np.expm1(rb["beta_post"] + rb["t_mult"] * rb["sd_post"]) * 100

    # --- Sensitivity: ranking with vs without the excluded years ---
    def ranking_eb(excluir_anos):
        r = (anual.groupby(["cidade", "uf"])
             .apply(lambda g: crescimento_ols(g, excluir_anos))
             .dropna(how="all").reset_index()
             .merge(pib_snap, on=["cidade", "uf"], how="inner"))
        r = r[r["s"] > 0].copy()
        w = 1 / r["s"]**2
        mu_f = np.sum(w * r["beta"]) / np.sum(w)
        Q = np.sum(w * (r["beta"] - mu_f)**2)
        kk = len(r)
        t2 = max(0.0, (Q - (kk - 1)) / (np.sum(w) - np.sum(w**2) / np.sum(w)))
        if t2 == 0:
            r["cagr_eb"] = np.expm1(r["beta"]) * 100
        else:
            Bb = r["s"]**2 / (r["s"]**2 + t2)
            mu_re = (np.sum((1 / (r["s"]**2 + t2)) * r["beta"]) /
                     np.sum(1 / (r["s"]**2 + t2)))
            r["cagr_eb"] = np.expm1((1 - Bb) * r["beta"] + Bb * mu_re) * 100
        e = r[(r["luz_base"] >= LUM_BASE_MIN) & (r["consistencia"] >= CONSIST_MIN)]
        return set(e.nlargest(N_TOP, "cagr_eb")["cidade"])

    top_all = ranking_eb([])
    top_excl = ranking_eb(EXCLUIR_ANOS)
    NUCLEO = top_all & top_excl
    print(f"robust core: {len(NUCLEO)}/{N_TOP} in both rankings -> {sorted(NUCLEO)}")

    # --- Final ranking and outputs ---
    eleg = rb[(rb["luz_base"] >= LUM_BASE_MIN) & (rb["consistencia"] >= CONSIST_MIN)]
    top = eleg.nlargest(N_TOP, "cagr_eb").reset_index(drop=True)

    ANOS_JANELA = ANO_FIM - ANO_INI
    top["expansao"] = (1 + top["cagr_eb"] / 100) ** ANOS_JANELA
    top["expansao_lo"] = (1 + top["cagr_eb_lo"] / 100) ** ANOS_JANELA
    top["expansao_hi"] = (1 + top["cagr_eb_hi"] / 100) ** ANOS_JANELA
    top = top.sort_values("cagr_eb", ascending=False).reset_index(drop=True)
    assert ((top["expansao"] >= top["expansao_lo"]) &
            (top["expansao"] <= top["expansao_hi"])).all()

    rb.sort_values("cagr_eb", ascending=False).to_csv(
        OUT_DIR / "results.csv", index=False)

    # Table figure
    tab = top[["cidade", "uf"]].copy()
    tab.insert(0, "#", range(1, len(tab) + 1))
    tab["exp"] = top["expansao"].map(lambda v: f"{v:.1f}x")
    tab["ci"] = top.apply(lambda r: f"{r['expansao_lo']:.1f} to {r['expansao_hi']:.1f}x", axis=1)
    tab["shr"] = top["shrink_pct"].map(lambda v: f"{v:.0f}%")
    tab["rate"] = top["cagr_eb"].map(lambda v: f"+{v:.1f}%")
    tab["pop"] = top["pop"].map(lambda v: f"{v:,.0f}")
    tab["pibpc"] = top["pib_per_capita"].map(lambda v: f"R$ {v:,.0f}")
    tab.columns = ["#", "Municipality", "State",
                   f"Adjusted expansion\n{ANO_INI}-{ANO_FIM}", "95% CI",
                   "Shrinkage\n(B_i)", "Adjusted rate\n(%/yr)",
                   f"Population\n(IBGE {ULTIMO_ANO_PIB})",
                   f"GDP per capita\n({ULTIMO_ANO_PIB})"]

    fig, ax = plt.subplots(figsize=(16, 0.55 * len(tab) + 1.8))
    ax.axis("off")
    t = ax.table(cellText=tab.values, colLabels=tab.columns,
                 cellLoc="center", loc="center")
    t.auto_set_font_size(False)
    t.set_fontsize(FS - 4)
    t.scale(1, 2.0)
    t.auto_set_column_width(col=list(range(len(tab.columns))))
    for j in range(len(tab.columns)):
        c = t[0, j]
        c.set_facecolor(AZUL)
        c.set_text_props(color="white", fontweight="bold")
        c.set_height(c.get_height() * 1.4)
    for i in range(1, len(tab) + 1):
        estavel = top.iloc[i - 1]["cidade"] in NUCLEO
        for j in range(len(tab.columns)):
            t[i, j].set_facecolor(AZULC if estavel else
                                  ("#F4F6FA" if i % 2 == 0 else "white"))
    glossario = (
        "How to read. Adjusted expansion: how many times nighttime radiance grew over the window, "
        "from the Empirical Bayes adjusted rate. 95% CI: Student t interval on the EB posterior; "
        "it is a floor, since outlier removal uncertainty is not propagated. "
        "Shrinkage (B_i): how much the raw estimate was pulled toward the panel mean; higher means noisier series. "
        "Blue rows: municipalities present in the top list both with and without the excluded years (robust core). "
        "The set is more reliable than the exact order within it.")
    fig.text(0.5, 0.02, glossario, ha="center", fontsize=FS - 5,
             fontstyle="italic", color=CINZA, wrap=True)
    plt.savefig(OUT_DIR / "table_eb.png", dpi=200, bbox_inches="tight")
    plt.close()

    # Line panels for the top list
    ncols = 5
    nrows = int(np.ceil(len(top) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(22, 4.2 * nrows))
    axes = np.atleast_2d(axes)
    for i, (_, r) in enumerate(top.iterrows()):
        ax = axes[i // ncols, i % ncols]
        g = (anual[(anual["cidade"] == r["cidade"]) & (anual["year"] >= ANO_INI)]
             .sort_values("year"))
        atip = set(int(a) for a in r["anos_atipicos"].split(",") if a not in ("-", ""))
        fora = atip | set(EXCLUIR_ANOS)
        g_ok, g_out = g[~g["year"].isin(fora)], g[g["year"].isin(fora)]
        ax.plot(g_ok["year"], g_ok["rad"], marker="o", ms=6, lw=2.2, color=AZUL)
        if not g_out.empty:
            ax.scatter(g_out["year"], g_out["rad"], s=55, facecolors="none",
                       edgecolors=CINZA, lw=1.5, zorder=3)
        xs = np.array([g_ok["year"].min(), g_ok["year"].max()], float)
        sl = np.log1p(r["cagr_eb"] / 100)
        y0 = np.log(g_ok["rad"]).mean() - sl * (g_ok["year"].mean() - xs[0])
        ax.plot(xs, np.exp(y0 + sl * (xs - xs[0])), ls="--", lw=1.8,
                color=ROSA, zorder=2)
        ax.set_title(f"{i+1}. {r['cidade']} ({r['uf']})", fontsize=FS - 2,
                     fontweight="bold", color=AZUL, loc="left")
        ax.text(0.03, 0.92, f"{r['cagr_eb']:+.0f}%/yr (adjusted)".replace("-0%", "0%"),
                transform=ax.transAxes, fontsize=FS - 5,
                color=ROSA, fontweight="bold", va="top")
        ax.xaxis.set_major_locator(mticker.MaxNLocator(4, integer=True))
        ax.tick_params(labelsize=FS - 5)
        ax.grid(alpha=0.25)
        ax.set_ylim(bottom=0)
    for j in range(len(top), nrows * ncols):
        axes[j // ncols, j % ncols].axis("off")
    fig.suptitle(f"Nighttime radiance by municipality, {ANO_INI}-{ANO_ULT} "
                 f"(open circles: years excluded from the fit)",
                 fontsize=FS + 3, fontweight="bold", color=AZUL,
                 x=0.01, ha="left", y=1.0)
    fig.text(0.01, -0.03,
             "Solid blue: measured annual radiance (dry season median). "
             "Dashed line: EB adjusted trend after removing outlier years. "
             "Open circles: excluded years (panel anomaly or per city outliers).",
             fontsize=FS - 4, fontstyle="italic", color=CINZA)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "lines_top.png", dpi=200, bbox_inches="tight")
    plt.close()
    print(f"done: {OUT_DIR}/table_eb.png, {OUT_DIR}/lines_top.png, {OUT_DIR}/results.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="VIIRS nighttime lights screening")
    ap.add_argument("--fetch", action="store_true",
                    help="pull VIIRS series from GEE into the local cache first")
    args = ap.parse_args()
    if args.fetch:
        fetch()
    analyze()
