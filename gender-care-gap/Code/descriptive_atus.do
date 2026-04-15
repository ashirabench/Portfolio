* Filename: descriptive_atus.do
* EDA: care time distributions, gender trends, income analysis, industry breakdown
* Authors: Ashira Benchimol, Amiera Saanan, Lillian Davidson

*-------------------------------------------------

clear all
set more off

* ---- Basic summaries ----
use "CleanData/atus_clean.dta", clear

summarize
tab statefip
tab year

summarize care_total if care_total < 1000
summarize care_total if female == 1
summarize care_total if female == 0

* Distribution of total care time
histogram care_total if care_total < 1000, width(30) ///
	title("Distribution of Total Unpaid Care Time") ///
	xtitle("Minutes per day") ytitle("Number of respondents")
graph export "Results/Graph_Histogram_CareTotal.png", replace


* ---- Average unpaid care time by gender over time ----
use "CleanData/atus_clean.dta", clear

collapse (mean) care_total [pw=wt06], by(year female)
twoway ///
	(line care_total year if female==1, lcolor(pink)) ///
	(line care_total year if female==0, lcolor(blue)), ///
	legend(label(1 "Women") label(2 "Men")) ///
	title("Average Unpaid Care Time by Gender, 2003-2022") ///
	xtitle("Year") ytitle("Minutes per day") 
graph export "Results/Graph_Line_CareTime_Gender_Individual.png", replace


* ---- Housewives vs other women ----
use "CleanData/atus_clean.dta", clear

keep if female==1
graph bar care_total [pw=wt06], over(housewife) ///
	title("Care Time: Housewives(1) vs Other Women (0)") ///
	ytitle("Weighted mean minutes per day")
graph export "Results/Graph_Housewife_vs_OtherWomen.png", replace


* ---- Care by children/no children and gender ----
graph bar care_total [pw=wt06], ///
	over(child_under5, relabel(1 "Men" 2 "Women")) ///
	over(female, relabel(1 "No children under five" 2 "Children under five")) ///
	asyvars bar(1, color(blue)) bar(2, color(pink)) ///
	title("Care Time among Parents of Kids < 5 years") ///
	ytitle("Weighted mean minutes per day")
graph export "Results/Graph_Line_Kids_ornot.png", replace


* ---- Parents of children under 5: mothers vs fathers ----
use "CleanData/atus_clean.dta", clear

keep if child_under5 == 1
graph bar care_total [pw=wt06], over(female) ///
	title("Care Time among Parents of Kids < 5 years, 0 = Man, 1= Women") ///
	ytitle("Weighted mean minutes per day") 
graph export "Results/Graph_Parents_Under5.png", replace


* ---- Care gap over time by state (all states) ----
* Already weighted: collapse used [pw = wt06] in databuild
use "CleanData/atus_union_merged.dta", clear
keep if year >= 2003 & year <= 2024
sort statefip year
twoway line care_gap year, xtitle("Year") ytitle("Minutes per day") by(statefip)
graph export "Results/caregap_by_state_all.png", replace


* ---- Care gap: selected states with cleaner trends ----
use "CleanData/atus_union_merged.dta", clear
keep if year >= 2003 & year <= 2024
keep if inlist(statefip, 6, 8, 12, 17, 26, 36, 48, 51)

preserve
keep if statefip == 6
twoway line care_gap year, title("Care Gap Over Time: California") xtitle("Year") ytitle("Minutes per Day")
graph export "Results/caregap_california.png", replace
restore

preserve
keep if statefip == 8
twoway line care_gap year, title("Care Gap Over Time: Colorado") xtitle("Year") ytitle("Minutes per Day")
graph export "Results/caregap_colorado.png", replace
restore

preserve
keep if statefip == 12
twoway line care_gap year, title("Care Gap Over Time: Florida") xtitle("Year") ytitle("Minutes per Day")
graph export "Results/caregap_florida.png", replace
restore

preserve
keep if statefip == 17
twoway line care_gap year, title("Care Gap Over Time: Illinois") xtitle("Year") ytitle("Minutes per Day")
graph export "Results/caregap_illinois.png", replace
restore

preserve
keep if statefip == 26
twoway line care_gap year, title("Care Gap Over Time: Michigan") xtitle("Year") ytitle("Minutes per Day")
graph export "Results/caregap_michigan.png", replace
restore

preserve
keep if statefip == 36
twoway line care_gap year, title("Care Gap Over Time: New York") xtitle("Year") ytitle("Minutes per Day")
graph export "Results/caregap_newyork.png", replace
restore

preserve
keep if statefip == 48
twoway line care_gap year, title("Care Gap Over Time: Texas") xtitle("Year") ytitle("Minutes per Day")
graph export "Results/caregap_texas.png", replace
restore

preserve
keep if statefip == 51
twoway line care_gap year, title("Care Gap Over Time: Virginia") xtitle("Year") ytitle("Minutes per Day")
graph export "Results/caregap_virginia.png", replace
restore


* ==============================================================================
* EXPLORATORY: Income and care time (married people only)
* Not used in final presentation but shows interesting patterns
* ==============================================================================

use "CleanData/atus_clean.dta", clear

keep if married == 1

* Drop income nonresponses
drop if famincome >= 996 

* Create midpoint of income brackets
gen faminc_mid = .
replace faminc_mid =  2500   if famincome == 1
replace faminc_mid =  6250   if famincome == 2
replace faminc_mid =  8750   if famincome == 3
replace faminc_mid = 11250   if famincome == 4
replace faminc_mid = 13750   if famincome == 5
replace faminc_mid = 17500   if famincome == 6
replace faminc_mid = 22500   if famincome == 7
replace faminc_mid = 27500   if famincome == 8
replace faminc_mid = 32500   if famincome == 9
replace faminc_mid = 37500   if famincome == 10
replace faminc_mid = 45000   if famincome == 11
replace faminc_mid = 55000   if famincome == 12
replace faminc_mid = 67500   if famincome == 13
replace faminc_mid = 87500   if famincome == 14
replace faminc_mid = 125000  if famincome == 15
replace faminc_mid = 200000  if famincome == 16   
* Assuming 200k for 150k+ bracket (round number)
label var faminc_mid "Family Income Midpoint ($)"

* Scatterplot with polynomial fit
* All married because marriage changes household specialization
twoway ///
	(scatter care_total faminc_mid if female==0, msymbol(o) mcolor(blue) msize(small)) ///
	(scatter care_total faminc_mid if female==1, msymbol(x) mcolor(red) msize(small)) ///
	(lpoly care_total faminc_mid if female==0, lcolor(blue)) ///
	(lpoly care_total faminc_mid if female==1, lcolor(red) lpattern(dash)), ///
	title("Care Time vs Family Income (Married Only)") ///
	xtitle("Family Income (Midpoint, $)") ytitle("Unpaid Care Minutes per Day") ///
	legend(order(1 "Men" 2 "Women" 3 "Fit: Men" 4 "Fit: Women"))

* Collapsed mean version (cleaner for presentations)
preserve
collapse (mean) care_total, by(faminc_mid female)
twoway ///
	(scatter care_total faminc_mid if female==0, msymbol(o) mcolor(blue)) ///
	(scatter care_total faminc_mid if female==1, msymbol(x) mcolor(red)) ///
	(line care_total faminc_mid if female==0, lcolor(blue)) ///
	(line care_total faminc_mid if female==1, lcolor(red) lpattern(dash)), ///
	title("Mean Care Time vs Family Income (Married Only)") ///
	xtitle("Family Income (Midpoint, $)") ytitle("Mean Unpaid Care Minutes per Day") ///
	legend(order(1 "Men" 2 "Women" 3 "Men (mean)" 4 "Women (mean)"))
graph export "Results/care_faminc_mid.png", replace
restore


* ==============================================================================
* EXPLORATORY: Care gap by industry
* Not used in final presentation because industry choice can be both
* explanatory and outcome variable. Still interesting to explore.
* ==============================================================================

use "CleanData/atus_clean.dta", clear
keep if care_total < 1000

* Convert numeric industry codes to readable short labels
decode ind2, gen(ind2_str)
gen ind_short = ""

* Manufacturing
replace ind_short = "Mfg: Nonmetal"            if strpos(ind2_str,"nonmetallic")>0
replace ind_short = "Mfg: Metals"              if strpos(ind2_str,"primary metals")>0
replace ind_short = "Mfg: Machinery"           if strpos(ind2_str,"machinery")>0
replace ind_short = "Mfg: Electronics"         if strpos(ind2_str,"electronic")>0
replace ind_short = "Mfg: Electrical"          if strpos(ind2_str,"electrical")>0
replace ind_short = "Mfg: Transport Equip"     if strpos(ind2_str,"transportation equipment")>0
replace ind_short = "Mfg: Wood"                if strpos(ind2_str,"wood product")>0
replace ind_short = "Mfg: Furniture"           if strpos(ind2_str,"furniture")>0
replace ind_short = "Mfg: Misc"                if strpos(ind2_str,"miscellaneous")>0
replace ind_short = "Mfg: Food"                if strpos(ind2_str,"food manufacturing")>0
replace ind_short = "Mfg: Beverage/Tobacco"    if strpos(ind2_str,"beverage and tobacco")>0
replace ind_short = "Mfg: Textile"             if strpos(ind2_str,"textile, apparel")>0
replace ind_short = "Mfg: Paper"               if strpos(ind2_str,"paper manufacturing")>0
replace ind_short = "Mfg: Petroleum/Coal"      if strpos(ind2_str,"petroleum and coal")>0
replace ind_short = "Mfg: Chemical"            if strpos(ind2_str,"chemical manufacturing")>0
replace ind_short = "Mfg: Plastics/Rubber"     if strpos(ind2_str,"plastics and rubber")>0

* Trade and transportation
replace ind_short = "Wholesale"                if ind2_str=="wholesale trade"
replace ind_short = "Retail"                   if ind2_str=="retail trade"
replace ind_short = "Transportation"           if ind2_str=="transportation and warehousing"
replace ind_short = "Utilities"                if ind2_str=="utilities"

* Information
replace ind_short = "Publishing"               if strpos(ind2_str,"publishing industries")>0
replace ind_short = "Motion Picture"           if strpos(ind2_str,"motion picture")>0
replace ind_short = "Broadcasting"             if strpos(ind2_str,"broadcasting (except internet)")>0
replace ind_short = "Internet Publishing"      if strpos(ind2_str,"internet publishing")>0
replace ind_short = "Telecom"                  if ind2_str=="telecommunications"
replace ind_short = "Data Services"            if strpos(ind2_str,"internet svc providers")>0
replace ind_short = "Other Info"               if ind2_str=="other information services"

* Finance / Insurance / Real Estate
replace ind_short = "Finance"                  if ind2_str=="finance"
replace ind_short = "Insurance"                if ind2_str=="insurance"
replace ind_short = "Real Estate"              if ind2_str=="real estate"
replace ind_short = "Rental/Leasing"           if ind2_str=="rental and leasing services"

* Professional / Admin
replace ind_short = "Professional Services"    if strpos(ind2_str,"professional, scientific")>0
replace ind_short = "Management"               if strpos(ind2_str,"management of companies")>0
replace ind_short = "Admin Support"            if strpos(ind2_str,"administrative and support")>0
replace ind_short = "Waste Mgmt"               if strpos(ind2_str,"waste management")>0

* Education / Health
replace ind_short = "Education"                if ind2_str=="educational services"
replace ind_short = "Hospitals"                if ind2_str=="hospitals"
replace ind_short = "Health Care"              if strpos(ind2_str,"health care services")>0
replace ind_short = "Social Assistance"        if ind2_str=="social assistance"

* Services
replace ind_short = "Arts/Recreation"          if strpos(ind2_str,"arts, entertainment")>0
replace ind_short = "Accommodation"            if ind2_str=="traveler accommodation"
replace ind_short = "Food Service"             if ind2_str=="food services and drinking places"
replace ind_short = "Private Households"       if ind2_str=="private households"
replace ind_short = "Repair/Maintenance"       if ind2_str=="repair and maintenance"
replace ind_short = "Personal Services"        if ind2_str=="personal and laundry services"
replace ind_short = "Membership Orgs"          if strpos(ind2_str,"membership associations")>0

* Public admin
replace ind_short = "Public Admin"             if ind2_str=="public administration"

* Catch-all
replace ind_short = "NIU"   if ind2_str=="niu (not in universe)"
replace ind_short = "Other" if ind_short==""

collapse (mean) care_total [pw=wt06], by(ind_short female)
reshape wide care_total, i(ind_short) j(female)
rename care_total0 care_male
rename care_total1 care_female
gen care_gap = care_female - care_male

graph hbar care_gap, over(ind_short, sort(1) label(labsize(vsmall))) ///
	title("Care Gap by Industry Category") ysize(8)


* ---- Education and gender care gap ----
use "CleanData/atus_clean.dta", clear

graph hbar (mean) care_total, over(female) over(educ) asyvars ///
	bar(1, color(blue)) bar(2, color(pink)) ///
	title("Gender Care Gap by Levels of Education") ///
	legend(label(1 "Men") label(2 "Women"))
graph export "Results/Gender_Gap_Education_Effects.png", replace
