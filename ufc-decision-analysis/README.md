# Who Really Wins a Close Round? Modeling Judge Disagreement in UFC Fights

Statistical analysis of UFC decision outcomes to predict fight winners from performance metrics — and flag when judges get it wrong. Logistic regression for interpretable coefficients, decision tree for thresholds, random forest to confirm variable importance, GAM to test for nonlinear effects, then cross-validated.

**Course:** EC 423 (Econometrics) · Michigan State University

## Research Questions

1. Which performance metrics best predict who wins a UFC decision?
2. Can we detect "controversial" decisions where the statistical winner lost?
3. Are certain weight classes or fighters disproportionately involved?
4. Do performance-outcome relationships have nonlinear patterns?

## Key Findings

| Model | Accuracy | Kappa |
|---|---|---|
| Logistic Regression (Forward Stepwise) | **82.0%** | 0.61 |
| Decision Tree (CART) | 80.3% | 0.57 |
| GAM | CV error 0.1257 vs 0.1284 (logistic) | — |

- **Strike differential** is the strongest predictor (~3.5% higher odds per strike)
- **Knockdowns** are the most decisive single event (~2.35× higher odds each)
- **Control time** shows diminishing returns after ~500 seconds (GAM)
- **~19% of decisions** flagged as potential "robberies"
- Women's and lighter weight divisions had the highest controversy rates

## Data

- **UFC Fight Statistics** — 8,200+ fights from [Kaggle](https://www.kaggle.com/datasets/jerzyszocik/ufc-fight-forecast-complete-gold-modeling-dataset) with per-round breakdowns
- In kaggle I managed to bulk download UFC data
- Download and place as `data/UFC_full_data_silver.csv` (too large for GitHub)

## Repo Structure

```
src/
├── 01_exploration.R           # EDA and visualizations
├── 02_modeling.R              # Logistic regression, decision tree, RF, GAM
└── 03_robbery_detection.R     # Controversial fight flagging
data/
└── README.md                  # Source links and data dictionary
outputs/
└── controversial_fights.csv   # Generated controversial decisions
```

## Run

```r
install.packages(c("tidyverse", "caret", "rpart", "rpart.plot",
                    "MASS", "boot", "gam", "randomForest"))

source("src/01_exploration.R")
source("src/02_modeling.R")
source("src/03_robbery_detection.R")
```

## Limitations

- The original goal was to model individual judge tendencies, but available datasets don't track judge identities consistently across fights (judge1/judge2/judge3 are positional, not named), so the project pivoted to modeling fight outcomes instead
- Strike direction (head vs. body) and power strikes not in final models
- Submission attempts excluded
- "Octagon control" and perceived damage are subjective and unquantifiable

## Tools

`R` · `tidyverse` · `caret` · `ggplot2` · Logistic Regression · Decision Trees · Random Forests · GAMs · Cross-Validation
