############################
Questrade ACB Calculator
############################

A Python tool for calculating Adjusted Cost Base (ACB), realized capital gains/losses, and other tax-related figures from brokerage transaction exports.

The project was built to automate the bookkeeping involved in tracking investment cost bases across multiple years and transactions, including purchases, sales, dividends, distributions, reverse splits, and cash-in-lieu transactions.

############################
Features
############################

- Imports transaction data from Excel brokerage exports
- Combines transactions from multiple files
- Tracks ACB and ACB per share for individual securities
- Calculates realized capital gains and losses from sales
- Accounts for transaction commissions and fees
- Converts USD transactions to CAD using historical exchange rates
- Handles several transaction types, including:
  - Buys
  - Sells
  - Dividends
  - Distributions
  - Reverse splits
  - Cash in lieu
- Produces yearly and total realized gain/loss summaries
- Produces ACB-per-share information for each security
- Tracks foreign-property holdings for **T1135** reporting
- Generates output containing figures used when preparing Canadian tax returns

############################
How It Works
############################

The calculator processes transactions chronologically and maintains a separate running state for each security.

For example, when a security is purchased, the purchase cost and associated commission are added to its ACB. When shares are sold, the calculator uses the security's current ACB per share to determine the cost base of the shares sold and calculates the resulting capital gain or loss.

USD transactions are converted to CAD using the historical exchange rate corresponding to the transaction date.

The program also maintains transaction history needed to determine the maximum amount of specified foreign property held during the year for T1135 purposes.

############################
Input
############################

The script requires two types of input:

1. **Questrade transaction exports**
   - One or more .xlsx files placed inside the "TradeData" folder.
   - The script automatically reads all ".xlsx" files in this folder and combines them.
   - Duplicate rows are removed during the data-cleaning process.

2. **USD/CAD historical exchange-rate data**
   - A CSV file named "USD_CAD Historical Data.csv".
   - The file must be located in the same directory as "Questrade_ACB_Calculator.py".
   - The dates in the CSV must cover all transaction dates for USD transactions being processed.

### Questrade Transaction Data

The script is designed around the format of transaction exports downloaded from Questrade.

The expected columns are:

Transaction Date
Settlement Date
Action
Symbol
Description
Quantity
Price
Gross Amount
Commission
Net Amount
Currency
Account #
Activity Type
Account Type

############################
Output
############################

The program generates a "Result.txt" file containing detailed information about the calculation.

The output includes:

- Transaction-by-transaction processing
- CAD conversions
- ACB changes
- ACB per share
- Realized gains/losses
- Yearly capital gains/losses
- Total capital gains/losses
- Foreign-property calculations for T1135 reporting

A shortened/anonymized example of the output is included in this repository.

############################
Example
############################

The repository's example output ("Result - Example.txt") uses fictionalized security names and transaction information rather than real financial data.

############################
Project Structure
############################


Questrade_ACB_Calculator/
│
├── Questrade_ACB_Calculator.py
├── USD_CAD Historical Data.csv
├── Result - Example.txt
│
└── TradeData/
    ├── 2021_Transactions.xlsx
    ├── 2022_Transactions.xlsx
    ├── 2023_Transactions.xlsx
    ├── 2024_Transactions.xlsx
    └── 2025_Transactions.xlsx


The main Python script contains the calculation engine, data-processing functions, account/security state tracking, and T1135 calculations.

############################
Requirements
############################

* Python 3
* pandas
* numpy
* openpyxl

Install the required Python packages with:

pip install pandas numpy openpyxl

############################
Usage
############################

Place the brokerage transaction exports and required exchange-rate data in the expected input locations, then run:

python Questrade_ACB_Calculator.py

The calculation results will be written to:

Result.txt

The exact input-file structure is dependent on the brokerage export format used by the script.

############################
Design
############################

The calculator uses several state objects to keep the calculation organized.

ACBTable:
Maintains the current total ACB and ACB per share for securities.

GainLoss:
Tracks realized gains and losses by security and tax year.

AccountState:
Groups the account's ACB and realized gain/loss information.

SecurityState:
Maintains the state of an individual security while its transactions are processed.

This approach allows each security to be processed independently while preserving its transaction history and running ACB.

############################
Limitations
############################

Important: This script was developed for personal use and is tailored to the author's specific Questrade transaction data. Depending on the format and contents of the raw data exported from Questrade, certain parts of the script may need to be customized. In particular, the prepData may require modification to match the securities and transaction descriptions in your own Questrade exports. All actions/transaction on a security must have the exact same value in the "Symbol" column.  The original conditions were deleted for author's privacy. 

This is a **personal tax/accounting automation tool**, rather than a general-purpose tax application.

Some limitations include:

* Input files must follow the expected brokerage export format.
* Some security-specific handling is based on the original account's transaction history.
* The program was developed around the author's own investment-account requirements.
* It has not been designed as a replacement for professional tax advice.
* The output should be reviewed before being used for tax filing.

############################
Background
############################

This project was created to automate a task that would otherwise require manually tracking adjusted cost bases across a large number of investment transactions.

The primary goal was accuracy and repeatability: given the same transaction history, the program can reproduce the same ACB and realized-gain calculations without manually maintaining spreadsheets.

############################
Disclaimer
############################

This software is provided for educational and personal-use purposes.

It is **not tax advice** and should not be relied upon as a substitute for advice from a qualified Canadian tax professional.

Always verify calculated figures against your brokerage records and applicable CRA guidance before using them for a tax return.




