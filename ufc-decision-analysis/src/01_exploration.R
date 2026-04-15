# ==============================================================================
# 01_exploration.R — EDA and Visualizations
# EC 423 — Michigan State University
# ==============================================================================
library(tidyverse)

ufc <- read.csv("data/UFC_full_data_silver.csv", check.names = FALSE)

cat("UFC dataset:", nrow(ufc), "fights,", ncol(ufc), "columns\n")

ufc_decisions <- ufc %>% filter(grepl("Decision", result))
cat("Decision fights:", nrow(ufc_decisions), "\n")


# Plot 1: Total Knockdowns by Round
# Knockdowns decrease across rounds — early rounds are more explosive

kd_cols <- grep("r[1-5]_knockdowns$", names(ufc), value = TRUE)

kd_totals <- ufc %>%
  summarise(across(all_of(kd_cols), ~ sum(.x, na.rm = TRUE))) %>%
  pivot_longer(everything(), names_to = "round", values_to = "knockdowns") %>%
  mutate(round = gsub(".*r([1-5])_knockdowns", "Round \\1", round)) %>%
  group_by(round) %>%
  summarise(knockdowns = sum(knockdowns), .groups = "drop")

ggplot(kd_totals, aes(x = round, y = knockdowns)) +
  geom_col(fill = "#E63946") +
  labs(title = "Total Knockdowns by Round",
       subtitle = "Knockdowns are most frequent in early rounds",
       x = "Round", y = "Knockdowns") +
  theme_minimal(base_size = 13)


# Plot 2: Total Strikes Landed by Round

strike_cols <- grep("_r\\d+_total_strikes_succ$", names(ufc), value = TRUE)
strike_totals <- colSums(ufc[strike_cols], na.rm = TRUE)

strike_df <- data.frame(
  col_name = names(strike_totals),
  strikes  = strike_totals
) %>%
  mutate(round = gsub(".*_r(\\d+)_total_strikes_succ", "Round \\1", col_name)) %>%
  group_by(round) %>%
  summarise(total_strikes = sum(strikes), .groups = "drop")

ggplot(strike_df, aes(x = round, y = total_strikes)) +
  geom_col(fill = "#F4A261") +
  labs(title = "Total Strikes Landed by Round",
       x = "Round", y = "Total Strikes") +
  theme_minimal(base_size = 13)


# Plot 3: KO/TKO Finishes per Round
# Round 1 produces the most stoppages

ko_tko_rounds <- ufc %>%
  filter(grepl("KO|TKO", result, ignore.case = TRUE)) %>%
  group_by(finish_round) %>%
  summarise(count = n(), .groups = "drop")

ggplot(ko_tko_rounds, aes(x = factor(finish_round), y = count)) +
  geom_col(fill = "#2A9D8F") +
  labs(title = "KO/TKO Finishes per Round",
       subtitle = "Round 1 produces the most stoppages",
       x = "Round", y = "Number of KO/TKO Finishes") +
  theme_minimal(base_size = 13)
