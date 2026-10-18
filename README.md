# SimpleBank

A command-line banking system written in Python. Open Savings, Current and Fixed Deposit accounts, move money safely between them, run month-end interest, and export statements, all through an interactive menu.

> Initially inspired by a course exercise; extended and redesigned by me.

## What it does

- **Three account types** with their own rules:
  - *Savings*: ₹1,000 minimum balance, 3.5% p.a. interest paid monthly, ₹50,000 daily withdrawal limit.
  - *Current*: overdraft limit (default ₹50,000), 14% p.a. charged monthly on the overdrawn amount.
  - *Fixed Deposit*: fixed tenure, monthly compounding interest, no top-ups, no withdrawal before maturity.
- **Exact money maths** using `Decimal` (no floating-point errors).
- **Safe transfers**: if the receiving side fails, the sender's money is put back and the reversal is recorded in the ledger.
- **Ledger for every account**: every rupee that moves leaves a record. Balances can only change through one internal method.
- **Freeze / unfreeze** accounts (a frozen account blocks customer transactions).
- **Statements**: full statement, mini statement (newest first) and CSV export with an optional date range.
- **Logging** of every transaction, refusal and rollback to `logs/simplebank.log`.
- **Clear, specific errors** (e.g. `LowBalanceError`, `EarlyWithdrawalError`, `DailyLimitError`) instead of generic failures.
- **Automated tests** with pytest.

## Tech stack

Python 3.9+, standard library only (`decimal`, `logging`, `csv`, `dataclasses`, `abc`). `pytest` for tests.

## Setup (VS Code)

1. Open the project folder in VS Code (`File > Open Folder`).
2. Open a terminal (`Ctrl + ~`) and create a virtual environment:
```bash
   python -m venv .venv
```
3. Activate it:
   - Windows: `.venv\Scripts\activate`
   - macOS / Linux: `source .venv/bin/activate`
4. Install the test dependency:
```bash
   pip install -r requirements.txt
```
5. Run the app:
```bash
   python main.py
```
6. Run the tests:
```bash
   pytest
```

## Usage example

Choose option `11` to create demo accounts, then try a transfer to a frozen account:

```text
  [OK] SB1002 is now FROZEN
  From account number: SB1001
  To account number: SB1002
  Amount (₹): 1000
  [ERROR] Transfer of ₹1,000.00 from SB1001 to SB1002 failed and was rolled back
```

The statement of `SB1001` then shows the debit **and** its reversal:

```text
 #3   18-Oct-2026 17:40  DEBIT      1,000.00     19,000.00  Transfer to SB1002
 #4   18-Oct-2026 17:40  CREDIT     1,000.00     20,000.00  Reversal: transfer to SB1002 failed
```

## Project structure

```text
simplebank/
├── main.py                  # entry point
├── requirements.txt
├── pytest.ini
├── simplebank/
│   ├── errors.py            # custom exceptions
│   ├── money.py             # Decimal helpers
│   ├── entries.py           # LedgerEntry record
│   ├── accounts.py          # BaseAccount, Savings, Current, FixedDeposit
│   ├── service.py           # BankService: open accounts, transfers, month-end
│   ├── reports.py           # statements and CSV export
│   ├── logging_setup.py     # file logging
│   └── cli.py               # interactive menu
└── tests/                   # money, accounts, transfers, reports
```

## How it is designed

Three layers, each with one job:

1. **Menu (`cli.py`)** talks to the user and shows friendly messages.
2. **Service (`service.py`)** applies bank-wide rules such as transfers and account numbering.
3. **Accounts (`accounts.py`)** own balances and the rules of each product.

`BaseAccount` is an abstract class: every account type must say how much can be withdrawn and what happens at month-end, while deposit, withdraw, freeze and the ledger are shared.

## Current limitations

- Data lives in memory only, so everything is lost when the program closes.
- Single user, not safe for several people using it at once.
- Amounts use Western digit grouping (1,000,000) rather than Indian (10,00,000).

## Future improvements

- **SQLite persistence** (planned next): save accounts and the ledger, and run transfers inside one database transaction.
- A `Customer` entity that can own several accounts.
- Indian-style number formatting.
- A small web or Streamlit front end.

## Credits

Initially inspired by a course exercise; extended and redesigned by me.