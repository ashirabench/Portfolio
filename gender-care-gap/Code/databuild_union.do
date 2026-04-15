* Filename: databuild_union.do
* Clean and prep state-level union membership data (1983-2024)
* Source: unionstats.com (Hirsch, Macpherson & Even)
* Authors: Ashira Benchimol, Amiera Saanan, Lillian Davidson

*-------------------------------------------------

import delimited "RawData/state_1983_2024.csv", clear

* Drop header rows and unnecessary columns
drop in 1/2 
drop v3 v4 v5 v7 v8

* Rename and label
rename v1 year
rename v2 state
rename v6 employment_1000s 
rename v9 membership_rate
rename v10 coverage_rate
label var membership_rate "Union membership rate (%)"
label var coverage_rate "Union coverage rate (%)"
label var employment_1000s "Employment (in 1000s)"

* Convert rates from string to numeric (remove % signs)
replace membership_rate = subinstr(membership_rate, "%", "", .)
destring membership_rate, gen(membership_rate_num) force
replace membership_rate_num = membership_rate_num / 100
label var membership_rate_num "Union membership rate, decimal"

replace coverage_rate = subinstr(coverage_rate, "%", "", .)
destring coverage_rate, gen(coverage_rate_num) force
replace coverage_rate_num = coverage_rate_num / 100
label var coverage_rate_num "Union coverage rate (decimal)"

destring employment_1000s, gen(employment_1000s_num) force
label var employment_1000s_num "Employment, in 1000s"

* Clean year variable
replace year = strtrim(year)
replace year = subinstr(year, "Year", "", .)
replace year = subinstr(year, "year", "", .)
replace year = subinstr(year, "STATE", "", .)
replace year = subinstr(year, "State", "", .)

destring year, gen(year_int) force
drop if missing(year_int)

* Keep only ATUS years (2003+)
drop if year_int < 2003
sort year_int

* Create state FIPS codes for merging with ATUS
gen statefip = .
replace statefip = 1  if state=="Alabama"
replace statefip = 2  if state=="Alaska"
replace statefip = 4  if state=="Arizona"
replace statefip = 5  if state=="Arkansas"
replace statefip = 6  if state=="California"
replace statefip = 8  if state=="Colorado"
replace statefip = 9  if state=="Connecticut"
replace statefip = 10 if state=="Delaware"
replace statefip = 11 if state=="District of Columbia"
replace statefip = 12 if state=="Florida"
replace statefip = 13 if state=="Georgia"
replace statefip = 15 if state=="Hawaii"
replace statefip = 16 if state=="Idaho"
replace statefip = 17 if state=="Illinois"
replace statefip = 18 if state=="Indiana"
replace statefip = 19 if state=="Iowa"
replace statefip = 20 if state=="Kansas"
replace statefip = 21 if state=="Kentucky"
replace statefip = 22 if state=="Louisiana"
replace statefip = 23 if state=="Maine"
replace statefip = 24 if state=="Maryland"
replace statefip = 25 if state=="Massachusetts"
replace statefip = 26 if state=="Michigan"
replace statefip = 27 if state=="Minnesota"
replace statefip = 28 if state=="Mississippi"
replace statefip = 29 if state=="Missouri"
replace statefip = 30 if state=="Montana"
replace statefip = 31 if state=="Nebraska"
replace statefip = 32 if state=="Nevada"
replace statefip = 33 if state=="New Hampshire"
replace statefip = 34 if state=="New Jersey"
replace statefip = 35 if state=="New Mexico"
replace statefip = 36 if state=="New York"
replace statefip = 37 if state=="North Carolina"
replace statefip = 38 if state=="North Dakota"
replace statefip = 39 if state=="Ohio"
replace statefip = 40 if state=="Oklahoma"
replace statefip = 41 if state=="Oregon"
replace statefip = 42 if state=="Pennsylvania"
replace statefip = 44 if state=="Rhode Island"
replace statefip = 45 if state=="South Carolina"
replace statefip = 46 if state=="South Dakota"
replace statefip = 47 if state=="Tennessee"
replace statefip = 48 if state=="Texas"
replace statefip = 49 if state=="Utah"
replace statefip = 50 if state=="Vermont"
replace statefip = 51 if state=="Virginia"
replace statefip = 53 if state=="Washington"
replace statefip = 54 if state=="West Virginia"
replace statefip = 55 if state=="Wisconsin"
replace statefip = 56 if state=="Wyoming"

label var statefip "State FIP code"
order statefip year state

* Create national averages (employment-weighted)
preserve 
gen members_1000s = membership_rate_num * employment_1000s_num
collapse (sum) members_1000s employment_1000s_num, by(year_int)
gen nat_member_rate = members_1000s / employment_1000s_num
label var nat_member_rate "National union membership rate (employment weighted)"
save "CleanData/union_national.dta", replace
restore

sort year_int
merge m:1 year_int using "CleanData/union_national.dta"
drop _merge

drop year
rename year_int year

* Collapse to one row per state-year (removes sector-level duplication)
collapse (mean) membership_rate_num coverage_rate_num employment_1000s_num nat_member_rate, by(statefip year)

save "CleanData/union_clean.dta", replace

* Citation: Copyright 2024 by Barry T. Hirsch, David A. Macpherson, and William Even
