# LASSO Housing Price Prediction

Predicting home sale prices in Ames, Iowa using LASSO regression with cross-validated lambda selection. EC 242 at MSU.

## Overview

Applied LASSO regression to the Ames Housing dataset (n ≈ 1,094) to predict `SalePrice`. LASSO adds an L1 penalty to the OLS objective, automatically shrinking unimportant coefficients to exactly zero and performing variable selection in the process.

## Methods

- Data cleaning: removed columns with >40% missing values and zero-variance predictors
- Selected 16 predictors covering size, quality, condition, age, location, and home features
- Built a model matrix with 16 main effects and 5 interaction terms
- Tuned the penalty parameter lambda via 10-fold cross-validation using `cv.glmnet`
- Evaluated model fit using RMSE at the optimal lambda

## Key Finding

The optimal lambda (≈ 6.86) retains 63 of 69 columns with non-zero coefficients. The `OverallQual:Neighborhood` interaction terms vary substantially across neighborhoods, confirming that the price premium for quality is location-dependent.

## Files

- `ec242_lab12_lasso_housing.Rmd` — full analysis with code and interpretation

## Dependencies

```r
install.packages(c("tidyverse", "skimr", "glmnet"))
```
