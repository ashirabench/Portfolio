* Filename: README.do
* Description: Master script — runs all code to build dataset and replicate results
* Research question: What explains the "gender care gap" in time use?
*   Do higher state unionization rates affect male-female gap in unpaid care minutes?
*   Does it differ by household structure?
* Course: EC 422 — Michigan State University
* Authors: Ashira Benchimol, Amiera Saanan, Lillian Davidson

* SET YOUR WORKING DIRECTORY HERE:
* cd "/your/path/to/gender-care-gap"

* BUILD DATASETS
do "Code/databuild_union.do"
do "Code/databuild_atus.do"

* GENERATE DESCRIPTIVE FIGURES
do "Code/descriptive_atus.do"
do "Code/descriptive_union.do"

* RUN REGRESSIONS
do "Code/regressions.do"
