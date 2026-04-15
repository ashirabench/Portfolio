* Filename: databuild_atus.do
* Clean ATUS microdata, create care variables, merge with union data
* Run databuild_union.do first!
* Authors: Ashira Benchimol, Amiera Saanan, Lillian Davidson

*-------------------------------------------------

clear all
set more off

use "RawData/atus_00003.dta", clear

* Drop empty/unnecessary columns
drop povertylevel poverty185 wt20 occ relate ind caseid serial strata pernum lineno

describe
label list STATEFIP FAMINCOME SEX MARST EDUC EMPSTAT OCC2 IND2 NCHILD NCHLT5

* ---- Generate key dummies and outcome variables ----

* Gender + marital status
gen female  = (sex == 2)
gen married = (marst == 1 | marst == 2)
label var female  "Female"
label var married "Married (spouse present or absent)"

* Housewife dummy
gen housewife = (female==1 & marst==1 & sploc>0 & empstat==5)
label var housewife "Housewife: Married female with spouse in HH, not in labor force"

* Spouse present dummy
gen spouse_present = (sploc > 0)
label var spouse_present "Spouse present in HH"

* Children under 5 dummy
gen child_under5 = (nchlt5 > 0)
label var child_under5 "Has a child under 5"

* Total unpaid care time in household
gen care_total = bls_carehh + bls_carenhh + bls_hhact
label var care_total "Total unpaid care time (min/day)"

save "CleanData/atus_clean.dta", replace

* ---- Prep state-year averages for merge ----

keep statefip year female care_total wt06
collapse (mean) care_total [pw = wt06], by(statefip year female)

* Reshape to wide: one row per state-year with male and female columns
reshape wide care_total, i(statefip year) j(female)
rename care_total0 care_male
rename care_total1 care_female

* Care ratio and gap
gen care_ratio = care_female / care_male
label var care_ratio "Female/Male care-time ratio"

gen care_gap = care_female - care_male
label var care_gap "Female-male unpaid care time gap (minutes per day)"

save "CleanData/atus_stateyear.dta", replace

* Merge with union data
sort statefip year
merge m:1 statefip year using "CleanData/union_clean.dta"
drop _merge

save "CleanData/atus_union_merged.dta", replace
