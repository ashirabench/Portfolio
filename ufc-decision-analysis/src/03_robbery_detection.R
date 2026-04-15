# ==============================================================================
# 03_robbery_detection.R — Flag controversial decisions
# EC 423 — Michigan State University
# ==============================================================================

library(tidyverse)

ufc <- read.csv("data/UFC_full_data_silver.csv", check.names = FALSE)
ufc_decisions <- ufc %>% filter(grepl("Decision", result))


# Performance Score (from logistic regression coefficients in 02_modeling.R)
#   Knockdowns:   0.8536
#   Control time: 0.00391
#   Strikes:      0.03398

robbery_df <- ufc_decisions %>%
  filter(!is.na(winner), winner != "Draw") %>%
  mutate(
    f1_perf = 0.8536 * f_1_knockdowns +
              0.00391 * f_1_ctrl_time_sec +
              0.03398 * f_1_total_strikes_succ,
    f2_perf = 0.8536 * f_2_knockdowns +
              0.00391 * f_2_ctrl_time_sec +
              0.03398 * f_2_total_strikes_succ
  ) %>%
  filter(!is.na(f1_perf), !is.na(f2_perf)) %>%
  mutate(
    expected = ifelse(f1_perf > f2_perf, f_1_name, f_2_name),
    robbery  = (expected != winner)
  )

# Overall Rate
robbery_rate <- mean(robbery_df$robbery)
cat("Robbery Rate:", round(robbery_rate * 100, 2), "%\n")

# Controversial Fights
controversial_fights <- robbery_df %>%
  filter(robbery == TRUE) %>%
  select(event_date, event_name, f_1_name, f_2_name,
         winner, expected, weight_class, finish_round) %>%
  arrange(desc(event_date))

cat("\nMost recent controversial decisions:\n")
print(head(controversial_fights, 10))

write.csv(controversial_fights, "outputs/controversial_fights.csv",
          row_names = FALSE)
cat("\nSaved", nrow(controversial_fights), "controversial fights to outputs/\n")

# By Weight Class
cat("\n=== Robbery Rate by Weight Class ===\n")
robbery_df %>%
  group_by(weight_class) %>%
  summarise(
    n_fights     = n(),
    robbery_rate = round(mean(robbery) * 100, 1),
    .groups      = "drop"
  ) %>%
  arrange(desc(robbery_rate)) %>%
  print()

# Most "Robbed" Fighters
cat("\n=== Fighters Most Often on the Wrong Side ===\n")
robbery_df %>%
  filter(robbery == TRUE) %>%
  count(expected, sort = TRUE) %>%
  head(10) %>%
  print()
