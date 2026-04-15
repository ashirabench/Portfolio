# Bank Subscription Classification

Predicting term deposit subscriptions from a Portuguese bank marketing campaign using logistic regression. EC 242 at MSU.

## Overview

Applied logistic regression to a bank marketing dataset (n = 4,521) to predict whether a client subscribed to a term deposit following a phone campaign. The dataset is heavily imbalanced (~11.5% subscription rate), making sensitivity and specificity more informative metrics than accuracy alone.

## Methods

- Converted character response to binary (1 = subscribed, 0 = not)
- 80/20 train/test split with set seed for reproducibility
- Fit four models of increasing complexity, starting with call duration alone
- Evaluated each model using confusion matrices, accuracy, sensitivity, and specificity
- Compared train and test performance to check for overfitting

## Key Finding

Accuracy is stable at ~88–89% across all models, but sensitivity is only ~14–15% due to class imbalance. Call duration alone captures most of the available signal — additional predictors provide only marginal improvement.

## Files

- `ec242_lab13_logistic_bank.Rmd` — full analysis with code and interpretation

## Dependencies

```r
install.packages(c("tidyverse", "caret"))
```
