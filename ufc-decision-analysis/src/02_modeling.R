# ==============================================================================
# 02_modeling.R — Logistic Regression, Decision Tree, Random Forest, GAM
# EC 423 — Michigan State University
# ==============================================================================

library(tidyverse)
library(caret)
library(rpart)
library(rpart.plot)
library(MASS)
library(boot)
library(gam)
library(randomForest)

ufc <- read.csv("data/UFC_full_data_silver.csv", check.names = FALSE)
ufc_decisions <- ufc %>% filter(grepl("Decision", result))

# ---- Feature Engineering ----
# Performance differentials between Fighter 1 and Fighter 2
model_data <- ufc_decisions %>%
  transmute(
    winner_f1    = ifelse(winner == f_1_name, 1, 0),
    diff_kd      = f_1_knockdowns - f_2_knockdowns,
    diff_ctrl    = f_1_ctrl_time_sec - f_2_ctrl_time_sec,
    diff_strikes = f_1_total_strikes_succ - f_2_total_strikes_succ
  ) %>%
  drop_na()

cat("Model dataset:", nrow(model_data), "decision fights\n")


# MODEL 1: Logistic Regression — Forward Stepwise Selection (AIC)

base_model <- glm(winner_f1 ~ 1, data = model_data, family = binomial)

step_model <- stepAIC(base_model,
  scope = list(lower = ~ 1, upper = ~ diff_kd + diff_ctrl + diff_strikes),
  direction = "forward"
)

cat("\n=== Forward Stepwise Logistic Regression ===\n")
summary(step_model)

# All three predictors selected. Coefficients:
#   Strike diff:  0.034 — each extra strike ≈ 3.5% higher odds
#   Control time: 0.004 — each extra second ≈ 0.4% higher odds
#   Knockdowns:   0.854 — each knockdown ≈ 2.35x higher odds
#
# Backward and bidirectional stepwise selection confirmed the same model
# (identical AIC), so only forward selection is shown here.

# ---- Confusion Matrix ----
preds <- predict(step_model, type = "response")
pred_labels <- ifelse(preds > 0.5, 1, 0)

cat("\n=== Logistic Regression Performance ===\n")
confusionMatrix(as.factor(pred_labels), as.factor(model_data$winner_f1))
# Accuracy: 82.0% | Kappa: 0.61 | Sensitivity: 71% | Specificity: 89%


# MODEL 2: Decision Tree (CART)

tree_model <- rpart(
  winner_f1 ~ diff_kd + diff_ctrl + diff_strikes,
  data    = model_data,
  method  = "class",
  control = rpart.control(cp = 0.01)
)

rpart.plot(tree_model, type = 2, extra = 104,
           main = "Decision Tree: Predicting UFC Fight Winner")

# Key splits:
#   1st: strike differential > 3 (most powerful)
#   2nd: control time > 126 seconds
# Striking matters more to judges than grappling in the initial evaluation.

cat("\n=== Decision Tree Performance ===\n")
tree_preds <- predict(tree_model, type = "class")
confusionMatrix(tree_preds, as.factor(model_data$winner_f1))
# Accuracy: 80.3% | Kappa: 0.572 — slightly less accurate, more interpretable


# MODEL 3: Random Forest — Variable Importance

set.seed(42)
rf_model <- randomForest(
  as.factor(winner_f1) ~ diff_kd + diff_ctrl + diff_strikes,
  data       = model_data,
  importance = TRUE,
  ntree      = 500
)

varImpPlot(rf_model, main = "Random Forest — Variable Importance")

# MeanDecreaseGini ranking:
#   1. diff_strikes (strongest)
#   2. diff_ctrl
#   3. diff_kd (lowest — knockdowns are rare/binary, less info for tree splits)


# MODEL 4: GAM — Nonlinear Effects

gam_model <- gam(
  winner_f1 ~ s(diff_kd) + s(diff_ctrl) + s(diff_strikes),
  data   = model_data,
  family = binomial
)

par(mfrow = c(1, 3))
plot(gam_model, se = TRUE, col = "blue", main = "GAM: Smoothed Effects")
par(mfrow = c(1, 1))

# Nonlinear findings:
#   Knockdowns: sharp threshold (rare but decisive)
#   Control time: diminishing returns after ~500 seconds
#   Strikes: small leads may be ignored; large differentials are decisive

# Cross-Validation Comparison

cv_logistic <- cv.glm(model_data, step_model, K = 10)
cv_gam      <- cv.glm(model_data, gam_model, K = 10)

cat("\n=== 10-Fold Cross-Validation ===\n")
cat("CV Error (Logistic):", round(cv_logistic$delta[1], 4), "\n")
cat("CV Error (GAM):     ", round(cv_gam$delta[1], 4), "\n")
# GAM marginally better (0.1257 vs 0.1284)
