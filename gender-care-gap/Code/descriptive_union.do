* Filename: descriptive_union.do
* EDA: union membership distributions and trends
* Authors: Ashira Benchimol, Amiera Saanan, Lillian Davidson

*-------------------------------------------------

use "CleanData/union_clean.dta", clear

tab state
tab year
summarize membership_rate_num coverage_rate_num

* Distribution of membership rates
histogram membership_rate_num, ///
	title("Distribution of Union Membership Rates") ///
	xtitle("Rate (decimal)") ytitle("Count")
graph export "Results/Histogram_UnionMembership.png", replace

* Union membership over time by state
twoway line membership_rate_num year, ///
	by(state, title("Union Membership Rate Over Time by State") ///
	note("Unit: share of employed workers who are union members") ///
	imargin(2 2 2 2)) ///
	xtitle("Year") ytitle("Union Membership Rate")
graph export "Results/UnionRate_ByState.png", replace

* National trend (unweighted mean)
collapse (mean) membership_rate_num, by(year)
twoway line membership_rate_num year, ///
	title("National Trend in Union Membership") ///
	xtitle("Year") ytitle("Average Membership Rate")
graph export "Results/NationalUnionTrend.png", replace
