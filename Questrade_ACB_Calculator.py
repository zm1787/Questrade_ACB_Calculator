import pandas as pd
import tabulate
import re
import os
from collections import defaultdict

pd.options.mode.chained_assignment = None
pd.set_option('display.max_rows', None)

# Append a line of text to the calculation log file.
def writeToFile(text):
    with open("Result.txt", "a") as myfile:
        text = text + "\n"
        myfile.write(text)

def printLog(text):
    writeToFile(text)

def printLogDF(df):
    text = str(df.round(2))
    writeToFile(text)

# Stores the current total adjusted cost base (ACB) and ACB per share
# for every security in the account.
class ACBTable:
    def __init__(self, security_list):
        self.totalAcb = pd.DataFrame(0.0, index=["Total ACB"], columns=security_list, dtype=float)
        self.acbPerShare = pd.DataFrame(0.0, index=["ACB/Share"], columns=security_list, dtype=float)

    def setAcb(self, ticker, value, perShare=False):
        if perShare:
            if value == "Sold":
                self.acbPerShare[ticker] = self.acbPerShare[ticker].astype(object)
            self.acbPerShare.loc["ACB/Share", ticker] = value
        else:
            if value == "Sold":
                self.totalAcb[ticker] = self.totalAcb[ticker].astype(object)
            self.totalAcb.loc["Total ACB", ticker] = value

    def printTotalAcb(self):
        printLog("------------------")
        printLog("Total ACB:")
        printLog("------------------")
        printLogDF(self.totalAcb)
        printLog("\n")

    def printAcbPerShare(self):
        printLog("------------------")
        printLog("ACB Per Share:")
        printLog("------------------")
        printLogDF(self.acbPerShare)
        printLog("\n")

# Stores realized gains and losses separately by year and security.
class GainLoss:
    def __init__(self, year_list, security_list):
        self.gain = pd.DataFrame(0.0, index=year_list, columns=security_list, dtype=float)
        self.loss = pd.DataFrame(0.0, index=year_list, columns=security_list, dtype=float)

    def printTotal(self):
        totalDF = self.gain.add(self.loss, fill_value=0)
        printLog("------------------")
        printLog("Realized Gain\\Loss Total:")
        printLog("------------------")
        printLogDF(totalDF)
        printLog("Total: " + str("%.2f" % totalDF.sum().sum()))
        printLog("\n")

    def printGain(self):
        printLog("------------------")
        printLog("Realized Gains Only:")
        printLog("------------------")
        printLogDF(self.gain)
        printLog("Total: " + str("%.2f" % self.gain.sum().sum()))
        printLog("\n")

    def printLoss(self):
        printLog("------------------")
        printLog("Realized Losses Only:")
        printLog("------------------")
        printLogDF(self.loss)
        printLog("Total: " + str("%.2f" % self.loss.sum().sum()))
        printLog("\n")

    def getTotal(self):
        return self.gain.add(self.loss, fill_value=0)

# Groups the account's ACB and realized gain/loss information together.
class AccountState:
    def __init__(self, year_list, security_list):
        self.PnL = GainLoss(year_list, security_list)
        self.Acb = ACBTable(security_list)

    def printGainLossTables(self):
        self.PnL.printGain()
        self.PnL.printLoss()
        self.PnL.printTotal()

    def printTotalPnL(self):
        totalPnL = round(self.PnL.loss.sum().sum() + self.PnL.gain.sum().sum(), 2)
        printLog(str(totalPnL))

    def printAcb(self):
        self.Acb.printAcbPerShare()
        self.Acb.printTotalAcb()

    def setAcb(self, ticker, value, perShare=False):
        self.Acb.setAcb(ticker, value, perShare)

    def setSecurityPnL(self, ticker, year, value):
        if value < 0:
            self.PnL.loss.loc[year, ticker] = float(value)
        else:
            self.PnL.gain.loc[year, ticker] = float(value)

# Tracks the running state of one security while its transactions are processed.
class SecurityState:
    def __init__(self, name):
        self.name = name
        self.total_ACB = 0
        self.ACB_per_share = 0
        self.previous_total_ACB = 0
        self.share_amount = 0
        self.previous_share_amount = 0
        self.capital_gain_this_year = 0
        self.capital_loss_this_year = 0
        self.capital_gainLoss_this_year = 0
        self.acb_history = []          # NEW: for T1135 "at any time" tracking
        self.is_foreign = False        # NEW: set after creation

def printActionResult(security):
    totalACB = security.total_ACB
    ACBPerShare = security.ACB_per_share
    if isinstance(totalACB, float):
        totalACB = round(totalACB, 4)
    if isinstance(ACBPerShare, float):
        ACBPerShare = round(ACBPerShare, 4)
    printLog("\nTotal ACB: " + str(totalACB))
    printLog("ACB per Share: " + str(ACBPerShare))
    printLog("Share Amount: " + str(security.share_amount))
    printLog("Capital Gain (or loss): " + str(security.capital_gain_this_year) + "\n")

# Convert a USD transaction amount to CAD using the exchange rate for its date.
def toCAD(amount, date):
    CER = currencyExchangeRates
    CER = CER[CER['Date'] == date]
    rate = CER['Rate'].values[0]
    printLog("\nChanging $" + str(amount) + " USD to CAD:")
    printLog(str(CER))
    value = round(amount * rate, 2)
    printLog("\nValue in CAD: $" + str(value) + "\n")
    return amount * rate

def printReverseSplitRatio(searchString):
    pattern = r"\d+:\d+"
    split_ratio = re.search(pattern, searchString)

    ratio_value = None

    if split_ratio:
        ratio_str = split_ratio.group()  # "1:10"
        printLog(f"Reverse split ratio is {ratio_str}")
        
        # Convert the split ratio to a numeric multiplier.
        num, denom = map(int, ratio_str.split(":"))
        ratio_value = num / denom

    return

# Load the historical USD/CAD rates and normalize the date/rate columns
# so they can be looked up during transaction processing.
def currencyExchangeFileToDataFrame(fileName):
    currencyExchangeRates = pd.read_csv(fileName)
    currencyExchangeRates = currencyExchangeRates[['Date', 'Price']]
    currencyExchangeRates = currencyExchangeRates.rename(columns={"Price": "Rate"})
    printLog("Currency Exchange Rates Table Head(10):")
    currencyExchangeRates['Date'] = pd.to_datetime(currencyExchangeRates.Date)
    currencyExchangeRates['Date'] = currencyExchangeRates['Date'].dt.strftime('%Y-%-m%d')
    for i in range(len(currencyExchangeRates)):
        currencyExchangeRates.loc[i, "Date"] = currencyExchangeRates["Date"][i][0:10]
    printLog(str(currencyExchangeRates.head(10)))
    return currencyExchangeRates

# Read every Excel transaction export and combine them into one transaction table.
def allXlsxToDataFrame(folder_path):
    all_dfs = []

    # Read all Excel transaction exports in the folder.
    for file in os.listdir(folder_path):
        if file.endswith(".xlsx"):
            full_path = os.path.join(folder_path, file)
            printLog("Reading file: " + str(full_path))
            df = pd.read_excel(full_path)
            all_dfs.append(df)

    # Combine all transaction files into a single DataFrame.
    combined_df = pd.concat(all_dfs, ignore_index=True)

    # Remove duplicate transactions that may appear across exports.
    combined_df = combined_df.drop_duplicates()

    # Normalize the index after combining and filtering the data.
    combined_df = combined_df.reset_index(drop=True)

    return combined_df

# Clean and normalize the brokerage exports before ACB calculations begin.
def prepData(folderName):
    df = allXlsxToDataFrame(folderName)
    printLog("\n#####################################################################################################################################")
    printLog("All Trades Dirty: ")
    printLog("#####################################################################################################################################\n")
    printLog(str(df) + "\n\n")

    year_list = df.copy(deep=True)

    for i in range(len(df)):
        if "DLR" in str(df.loc[i, "Description"]):
            df.loc[i, "Symbol"] = "DLR"
        #########################################################################################################################################################
        # HERE ADD AS MANY IFS AS NECESSARY LIKE THE EXAMPLE ABOVE TO CLEAN UP THE DATA (MAKE SURE ALL TRANSACTIONS FOR A SECURITY HAS THE SAME VALUE IN THE "Symbol" COLUMN).
        # ALTERNATIVELY YOU CAN CLEAN UP THE INPUT FILE BEFORE RUNNING THE SCRIPT
        #########################################################################################################################################################
        df.loc[i, "Settlement Date"] = df.loc[i, "Settlement Date"][0:10]
        df.loc[i, "Transaction Date"] = df.loc[i, "Transaction Date"][0:10]
        year_list.loc[i, "Settlement Date"] = year_list.loc[i, "Settlement Date"][0:4]

    df = df[~df['Action'].isin(['BRW', 'DEP', 'NAC'])].reset_index(drop=True)

    df = df.drop(["Activity Type", "Account #", "Account Type"], axis=1)
    year_list = year_list.drop(["Activity Type", "Account #", "Account Type", "Description"], axis=1)

    df = df.sort_values(['Symbol', 'Settlement Date'])
    year_list = year_list.sort_values(['Symbol', 'Settlement Date'])

    df = df.reset_index(drop=True)

    security_list = sorted(df['Symbol'].dropna().unique())
    printLog("\nSecurities List:")
    printLog(str(security_list) + "\n")

    year_list = sorted(year_list['Settlement Date'].unique())
    printLog("\nYear List: ")
    printLog(str(year_list) + "\n")

    printLog("\n#####################################################################################################################################")
    printLog("All Trades Clean: ")
    printLog("#####################################################################################################################################\n")
    printLog(str(df) + "\n\n")
    return df, year_list

exceptions_non_foreign = ['DLR', 'ETHQ.TO', 'D012499']

open('Result.txt', 'w').close()

currencyExchangeRates = currencyExchangeFileToDataFrame(r"USD_CAD Historical Data.csv")
df, year_list = prepData(r'TradeData')

# Create one persistent state object for each security found in the transactions.
security_list = df['Symbol'].unique()
Account = AccountState(year_list, security_list)

# Create persistent SecurityState objects
# Each security keeps its own running ACB, share count, and yearly gain/loss state.
dictOfSecurities = {sec: SecurityState(sec) for sec in security_list}

is_foreign_dict = {sec: True for sec in security_list}
for exc in exceptions_non_foreign:
    if exc in is_foreign_dict:
        is_foreign_dict[exc] = False

for sec, state in dictOfSecurities.items():
    state.is_foreign = is_foreign_dict[sec]

printLog("Starting securities and profits:")
Account.printGainLossTables()

# Process each security independently so its ACB and share count can be tracked over time.
for security in security_list:
    CurrentSecurity = dictOfSecurities[security]
    transactions = df.loc[df['Symbol'] == security]
    printLog("\n\n\n\n\n\n\n")
    printLog("#####################################################################################################################################")
    printLog(str(security))
    printLog("#####################################################################################################################################")
    printLog("\n")

    skipIndex = -1
    # Process transactions in chronological order for this security.
    for i in range(len(transactions)):
        current_action = transactions.iloc[[i]].drop(columns=['Description'])   # Drop Description column for cleaner logging. Log description alone if needed.
        action_type = transactions.loc[transactions.index[i], 'Action']
        quantity = abs(transactions.loc[transactions.index[i], 'Quantity'])
        price = abs(transactions.loc[transactions.index[i], 'Price'])
        net_amount = abs(transactions.loc[transactions.index[i], 'Net Amount'])
        commission = abs(transactions.loc[transactions.index[i], 'Commission'])
        currency = transactions.loc[transactions.index[i], 'Currency']
        settlement_date = transactions.loc[transactions.index[i], 'Settlement Date']
        transaction_date = transactions.loc[transactions.index[i], 'Transaction Date']
        description = transactions.loc[transactions.index[i], 'Description']

        if i > 0 and year != settlement_date[0:4]:
            CurrentSecurity.capital_gain_this_year = 0
            CurrentSecurity.capital_gainLoss_this_year = 0
            CurrentSecurity.capital_loss_this_year = 0
        year = settlement_date[0:4]

        printLog("Current action:\n")
        printLog(str(current_action.to_markdown()))
        printLog("\nDescription: " + str(description) + "\n")
        if i == skipIndex:
            printLog("SKIPPING ACTION: Processed in previous action.\n\n")
            continue
        

        # Apply the ACB and gain/loss rules for this transaction type.
        # A purchase increases both the total ACB and the number of shares held.
        if action_type == 'Buy':
            purchase_price = net_amount
            if currency == 'USD':
                purchase_price = toCAD(purchase_price, transaction_date)
            CurrentSecurity.total_ACB = CurrentSecurity.previous_total_ACB + purchase_price
            Account.setAcb(security, CurrentSecurity.total_ACB, perShare=False)
            CurrentSecurity.share_amount = CurrentSecurity.previous_share_amount + quantity
            CurrentSecurity.ACB_per_share = CurrentSecurity.total_ACB / CurrentSecurity.share_amount if CurrentSecurity.share_amount != 0 else 0
            Account.setAcb(security, CurrentSecurity.ACB_per_share, perShare=True)

        # A sale realizes a gain or loss based on the average ACB of the shares sold.
        elif action_type == 'Sell':
            change = (price * quantity) - commission
            if currency == 'USD':
                change = toCAD(change, transaction_date)
            gainLossFromThisSell = change - ((CurrentSecurity.total_ACB / CurrentSecurity.previous_share_amount) * quantity if CurrentSecurity.previous_share_amount != 0 else 0)
            if gainLossFromThisSell > 0:
                CurrentSecurity.capital_gain_this_year += gainLossFromThisSell
                Account.setSecurityPnL(security, year, CurrentSecurity.capital_gain_this_year)
            else:
                CurrentSecurity.capital_loss_this_year += gainLossFromThisSell
                Account.setSecurityPnL(security, year, CurrentSecurity.capital_loss_this_year)
            CurrentSecurity.capital_gainLoss_this_year += gainLossFromThisSell
            costBase = (CurrentSecurity.total_ACB / CurrentSecurity.previous_share_amount) * quantity if CurrentSecurity.previous_share_amount != 0 else 0

            printLog("\n###############################")
            printLog("For WealthSimple Taxes (CAD)")
            printLog("###############################\n")
            printLog("(Proceeds and Cost Base already includes commissionfees, so put 0 in Expenses field):")
            printLog("Proceeds: " + str(change))
            printLog("Cost Base: " + str(costBase))
            printLog("Expenses: 0")
            printLog("\nGain\\Loss from this sell: " + str(gainLossFromThisSell))
            printLog("Total Gain\\Loss from this stock this year: " + str(CurrentSecurity.capital_gainLoss_this_year) + "\n")

            CurrentSecurity.total_ACB = CurrentSecurity.previous_total_ACB * ((CurrentSecurity.previous_share_amount - quantity) / CurrentSecurity.previous_share_amount) if CurrentSecurity.previous_share_amount != 0 else 0
            Account.setAcb(security, CurrentSecurity.total_ACB, perShare=False)
            CurrentSecurity.share_amount = CurrentSecurity.previous_share_amount - quantity
            if CurrentSecurity.share_amount != 0:
                CurrentSecurity.ACB_per_share = CurrentSecurity.total_ACB / CurrentSecurity.share_amount
                Account.setAcb(security, CurrentSecurity.ACB_per_share, perShare=True)
            else:
                CurrentSecurity.ACB_per_share = 0
                Account.setAcb(security, 0, perShare=False)
                Account.setAcb(security, CurrentSecurity.ACB_per_share, perShare=True)

        # A distribution changes the share count but does not add a new cash cost to ACB.
        elif action_type == 'DIS':
            printLog("\nAction description: Stock Split")
            CurrentSecurity.share_amount += quantity
            CurrentSecurity.ACB_per_share = CurrentSecurity.total_ACB / CurrentSecurity.share_amount if CurrentSecurity.share_amount != 0 else 0
            Account.setAcb(security, CurrentSecurity.ACB_per_share, perShare=True)
        # Cash dividends are reported as income and do not change the ACB of the shares.
        elif action_type == 'DIV':
            printLog("\nAction description: Dividends")
            # Cash dividends are taxable income and do not change ACB or share count.
            dividend_amount = net_amount  # positive value from the data
            if currency == 'USD':
                CAD_dividend = toCAD(dividend_amount, transaction_date)
            else:
                CAD_dividend = dividend_amount

            printLog("\n###############################")
            printLog("DIVIDEND RECEIVED")
            printLog("###############################\n")
            printLog(f"Dividend amount: ${dividend_amount:.2f} {currency}")
            printLog(f"Converted to CAD: ${CAD_dividend:.2f}")
            printLog("Note: This is taxable dividend income (report on T5 or equivalent).")
            printLog("No impact on ACB or share quantity.\n")

        # Reverse splits change the number of shares while leaving the total ACB unchanged.
        elif action_type == 'REV':
            printLog("\nAction description: Reverse Stock Split")
            printReverseSplitRatio(description) # Only prints if found in this action
            printLog("Old " + str(security) + " Share Count: " + str(CurrentSecurity.share_amount))
            if i + 1 < len(transactions): # if not out of bound
                next_action_type = transactions.iloc[i+1]['Action']
                next_quantity = transactions.iloc[i+1]['Quantity']
                next_description = transactions.iloc[i+1]['Description']

                printReverseSplitRatio(next_description) # Only prints if found in next action

                if next_action_type == 'REV':
                    CurrentSecurity.share_amount += next_quantity
                    skipIndex = i + 1 # Skip next action because it's getting processed now

            quantity = transactions.loc[transactions.index[i], 'Quantity'] # Use signed quantity for REV
            CurrentSecurity.share_amount += quantity
            if CurrentSecurity.share_amount != 0:
                CurrentSecurity.ACB_per_share = CurrentSecurity.total_ACB / CurrentSecurity.share_amount if CurrentSecurity.share_amount != 0 else 0
                Account.setAcb(security, CurrentSecurity.ACB_per_share, perShare=True)
            else:
                CurrentSecurity.ACB_per_share = 0
                Account.setAcb(security, 0, perShare=False)
                Account.setAcb(security, CurrentSecurity.ACB_per_share, perShare=True)

            printLog("New " + str(security) + " Share Count: " + str(CurrentSecurity.share_amount) + "\n")

        # Cash in lieu represents a small cash payment for fractional shares.
        elif action_type == 'CIL':
            printLog("\nAction description: Cash In Lieu")
            if currency == 'USD':
                CADAmount = toCAD(net_amount, transaction_date)
            else:
                CADAmount = net_amount
            # Treat small cash-in-lieu payments as an ACB reduction.
            CurrentSecurity.total_ACB = CurrentSecurity.previous_total_ACB - CADAmount  # subtract cash received
            Account.setAcb(security, CurrentSecurity.total_ACB, perShare=False)
            printLog(f"Cash in Lieu of fractional shares: ${CADAmount:.2f} CAD - reduced total ACB by this amount (small amount treatment)\n")

        else:
            message = "\nERROR: Action type undefined: " + str(action_type) + "\nSkipping action"
            printLog(str(message))
            continue

        current_acb = CurrentSecurity.total_ACB if isinstance(CurrentSecurity.total_ACB, (int, float)) else 0.0
        CurrentSecurity.acb_history.append((settlement_date, round(current_acb, 2)))

        # Save the current state so the next transaction can calculate its change from this point.
        CurrentSecurity.previous_total_ACB = CurrentSecurity.total_ACB
        CurrentSecurity.previous_share_amount = CurrentSecurity.share_amount

        printActionResult(CurrentSecurity)
        Account.printAcb()
        printLog("Current total gain/loss: ")
        Account.printTotalPnL()
        printLog("\nCurrent gain/loss detailed: ")
        Account.printGainLossTables()
        printLog("\n-------------------------------------------------------------------------------------------------------------------------------------\n")

# Print the final account-wide ACB and realized gain/loss summary.
printLog("Summary\n")
Account.printAcb()
Account.printGainLossTables()
printLog("\nTotal gain\\loss: ")
Account.printTotalPnL()

printLog("\n\n#####################################################################################################################################")
printLog("T1135 Foreign Assets (Specified Foreign Property) Check - Detailed")
printLog("#####################################################################################################################################")

printLog("\nForeign status determination (CRA rules - non-resident issuers / foreign ETFs):")
printLog("Foreign securities: " + str([sec for sec in security_list if is_foreign_dict.get(sec, False)]))
printLog("Non-foreign (Canadian-domiciled - exceptions): " + str([sec for sec in security_list if not is_foreign_dict.get(sec, False)]))

printLog("\nExceptions list used: " + str(exceptions_non_foreign))
printLog("Note: DLR and ETHQ.TO are Canadian ETFs -> not specified foreign property")
printLog("      Most US-listed stocks (TSLA, PLTR, BABA, etc.) -> are specified foreign property\n")

# Collect all unique transaction dates across foreign securities
# Build the set of dates on which the foreign-property ACB needs to be checked.
all_foreign_dates = set()
for sec_name, state in dictOfSecurities.items():
    if state.is_foreign:
        for date, _ in state.acb_history:
            all_foreign_dates.add(date)

unique_dates = sorted(list(all_foreign_dates))

printLog("Checking foreign ACB 'at any time' after every transaction date:")
printLog("Date                  |  " + "  ".join([f"{sec:>8}" for sec in security_list if is_foreign_dict.get(sec, False)]) + "  |  Total Foreign ACB")
printLog("-" * 100)

# Track the highest aggregate foreign-property cost during the year.
max_foreign_cost = 0.0
max_dates = []
max_per_year = {y: 0.0 for y in year_list}
yearly_max_date = {y: None for y in year_list}

# Reconstruct each date's total foreign-property ACB from the transaction history.
for date in unique_dates:
    year = date[:4]
    line = f"{date} |"
    total_at_date = 0.0
    
    for sec_name, state in dictOfSecurities.items():
        if not state.is_foreign:
            continue
        # Use the most recent recorded ACB on or before this date.
        latest_acb = 0.0
        for hist_date, acb in state.acb_history:
            if hist_date <= date:
                latest_acb = acb
        total_at_date += latest_acb
        line += f"  {latest_acb:8.2f}"
    
    line += f"  |  {total_at_date:12.2f}"
    printLog(line)
    
    # Track the overall and per-year maximum foreign-property cost.
    # Keep the date and amount whenever a new overall maximum is reached.
    if total_at_date > max_foreign_cost:
        max_foreign_cost = total_at_date
        max_dates = [date]
    elif total_at_date == max_foreign_cost:
        max_dates.append(date)
    
    # Also keep the maximum foreign-property amount reached in each individual year.
    if total_at_date > max_per_year.get(year, 0):
        max_per_year[year] = total_at_date
        yearly_max_date[year] = date

printLog("-" * 100)

printLog(f"\nHighest total foreign property cost amount (ACB in CAD): ${max_foreign_cost:,.2f}")
printLog(f"Reached on: {', '.join(max_dates)}")

printLog("\nPer-year maximum foreign property cost:")
for y in sorted(max_per_year.keys()):
    if max_per_year[y] > 0:
        date_str = f" (on {yearly_max_date[y]})" if yearly_max_date[y] else ""
        printLog(f"   {y}: ${max_per_year[y]:,.2f}{date_str}")
    else:
        printLog(f"   {y}: $0.00 (no foreign holdings)")

printLog("\nCRA T1135 filing threshold: cost amount of specified foreign property > $100,000 CAD at any time in the year")
# Determine whether the calculated maximum exceeds the T1135 filing threshold.
if max_foreign_cost > 100000:
    printLog("\n*** YES - YOU MUST FILE FORM T1135 ***")
    printLog("    (for each year where the max exceeded $100,000)")
    if max_foreign_cost > 250000:
        printLog("    → Part B (detailed reporting) may be required if > $250,000")
else:
    printLog("\n*** NO - T1135 not required ***")
    printLog("    (foreign property cost never exceeded $100,000 CAD)")

printLog("\nCalculation notes:")
printLog("- Uses your exact ACB (in CAD) after every buy/sell/dividend adjustment")
printLog("- Checks aggregate across all foreign securities at each relevant date")
printLog("- ACB = adjusted cost base = original cost + commissions + adjustments (no market value used)")
printLog("- DLR, ETHQ.TO treated as Canadian -> excluded from foreign total")
printLog("- If you add new securities later, verify foreign status manually")
