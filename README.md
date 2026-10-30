# uk-macro-research
Reproducible analysis of UK macroeconomic indicators 
Data Sources
- Source: ONS
- Dataset name: CPI-CT percentage change over 12 months_all items-291026.csv
- Description: Dataset measures percentage change in inflation
- Frequency: Annually, Quarterly and Monthly
- Units: Percentage (%)
- Date range: Dec 2003 - Dec 2021
- Source link: https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/ead6/mm23
- File location: data/raw/uk_cpi.csv
data/raw refers to the unprocessed and unfiltered, full dataset, data/processed refers to the dataset after it has been cleaned.

## Cleaning the CPI data

Run `python src/process_cpi.py` from the project root to create
`data/processed/uk_cpi_clean.csv`. The script reads `data/raw/uk_cpi.csv`
without modifying it, excludes ONS metadata and annual/quarterly summary rows,
and retains the monthly CPI-CT observations. The output has a `date` column
(the first day of each observation month) and a numeric
`cpi_inflation_percent` column. Missing CPI values are omitted; the script does
not interpolate or otherwise create observations.