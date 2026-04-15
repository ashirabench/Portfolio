* Filename: regressions.do
* OLS regressions: what explains the gender care gap?
* Authors: Ashira Benchimol, Amiera Saanan, Lillian Davidson

*-------------------------------------------------

* ---- Part 1: Individual-level regressions (ATUS) ----

use "CleanData/atus_clean.dta", clear

* Base: gender gap in care time
reg care_total female [pw = wt06]

* Add marriage status
gen female_married = female * married
reg care_total female married female_married [pw=wt06]

* Add children
gen kids = (nchild > 0)
label var kids "Any children in HH (=1)"
gen female_kids = female * kids
reg care_total female kids female_kids [pw = wt06]

* Education interactions
reg care_total i.female##i.educ [pw=wt06]
margins female#educ

* ---- Regression table 1: Progressive specifications ----
eststo clear
eststo reg1: reg care_total female [pw = wt06]
eststo reg2: reg care_total female married female_married [pw = wt06]
eststo reg3: reg care_total female kids female_kids [pw = wt06]
esttab reg1 reg2 reg3 using "Results/Table_CareGap1.csv", ///
	label replace noconstant b(3) se(3) r2(3) fragment ///
	mtitle("Gender Only" "+Marriage Status" "+Kids")


* ---- Part 2: Housewife effect ----
* Housewives spend nearly double the care time of other women (~290 vs ~165 min/day).
* How much of the "gender gap" is really a labor force participation gap?

use "CleanData/atus_clean.dta", clear

* Quantify the housewife effect
reg care_total female housewife [pw=wt06]

* Interaction: how much extra care do housewives provide beyond gender + housewife status?
gen female_housewife = female * housewife
reg care_total female housewife female_housewife [pw=wt06]

* What happens to the gender gap if we exclude housewives?
* If the coefficient on female drops significantly, the gap is partly
* a labor force participation story, not purely a gender story.
reg care_total female [pw=wt06] if housewife==0


* ---- Part 3: Does unionization moderate the gender care gap? ----

* Collapse union stats to state-year
use "CleanData/union_clean.dta", clear
collapse (mean) membership_rate_num coverage_rate_num, by(statefip year)
save "CleanData/union_collapsed.dta", replace

* Merge into individual ATUS data
use "CleanData/atus_clean.dta", clear
merge m:1 statefip year using "CleanData/union_collapsed.dta"
drop if _merge == 2
drop _merge

* Test: does union membership moderate the gender care gap?
* Answer: No
reg care_total female##c.membership_rate_num i.statefip i.year [pw=wt06]
reg care_total female##c.coverage_rate_num i.statefip i.year [pw=wt06]


* ---- Part 4: Regression table 2 — Family and education effects ----
* Since union doesn't affect the gap, check what does

use "CleanData/atus_clean.dta", clear

eststo clear
eststo: reg care_total female, vce(robust)
eststo: reg care_total female i.spouse_present i.child_under5, vce(robust)
eststo: reg care_total female i.spouse_present i.child_under5 i.educ, vce(robust)
esttab using "Results/Table_CareGap2.csv", ///
	label replace order(female spouse_present child_under5) ///
	keep(female) noconstant b(3) se(3) r2(3) fragment ///
	mtitle("Gender Only" "+Family" "+Educ")
