"""The interactive menu. It only talks to the user; all rules live in BankService."""
import logging
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation

from simplebank.errors import BankError
from simplebank.logging_setup import setup_logging
from simplebank.money import format_rupees
from simplebank.reports import account_row, export_csv, mini_statement_text, statement_text
from simplebank.service import BankService

log = logging.getLogger(__name__)


# ---------- small helpers for asking questions ----------
def ask(prompt, default=None):
    hint = f" [{default}]" if default is not None else ""
    answer = input(f"  {prompt}{hint}: ").strip()
    return answer if answer else (default or "")


def ask_required(prompt):
    while True:
        answer = ask(prompt)
        if answer:
            return answer
        print("  This cannot be empty.")


def ask_choice(prompt, options):
    """options is a dict like {"1": "SAVINGS"}; returns the chosen value."""
    print(f"  {prompt}:")
    for key, label in options.items():
        print(f"    {key}. {label}")
    while True:
        pick = input("  Your choice: ").strip()
        if pick in options:
            return options[pick]
        print("  Please type one of:", ", ".join(options))


def ask_int(prompt, default):
    while True:
        try:
            return int(ask(prompt, str(default)))
        except ValueError:
            print("  Please enter a whole number.")


def ask_percent(prompt, default):
    """Asks for a percentage like 7 and returns it as a fraction (0.07)."""
    while True:
        try:
            return Decimal(ask(prompt, default)) / 100
        except InvalidOperation:
            print("  Please enter a number like 7 or 6.5")


def ask_date(prompt):
    """Asks for YYYY-MM-DD. Pressing Enter means 'no limit' and returns None."""
    while True:
        text = ask(f"{prompt} (YYYY-MM-DD, Enter to skip)")
        if not text:
            return None
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            print("  Please use the format YYYY-MM-DD, e.g. 2026-10-18")


def success(message):
    print(f"  [OK] {message}")


# ---------- one function per menu option ----------
def action_open_account(bank):
    kind = ask_choice("Account type", {"1": "SAVINGS", "2": "CURRENT", "3": "FD"})
    holder = ask_required("Holder name")
    opening = ask_required("Opening deposit (₹)")
    options = {}
    if kind == "CURRENT":
        options["overdraft_limit"] = ask("Overdraft limit (₹)", "50000")
    elif kind == "FD":
        options["tenure_months"] = ask_int("Tenure in months", 12)
        options["annual_rate"] = ask_percent("Interest rate % per year", "7")
    account = bank.open_account(kind, holder, opening, **options)
    success(f"Opened {account.kind} account {account.account_no} for {account.holder_name}")


def action_deposit(bank):
    number = ask_required("Account number")
    balance = bank.deposit(number, ask_required("Amount (₹)"))
    success(f"Deposited. New balance: {format_rupees(balance)}")


def action_withdraw(bank):
    number = ask_required("Account number")
    balance = bank.withdraw(number, ask_required("Amount (₹)"))
    success(f"Withdrawn. New balance: {format_rupees(balance)}")


def action_transfer(bank):
    sender = ask_required("From account number")
    receiver = ask_required("To account number")
    bank.transfer(sender, receiver, ask_required("Amount (₹)"))
    success("Transfer completed")


def action_mini_statement(bank):
    account = bank.get_account(ask_required("Account number"))
    count = ask_int("How many transactions", 5)
    print(mini_statement_text(account, count, bank.name))


def action_full_statement(bank):
    account = bank.get_account(ask_required("Account number"))
    print(statement_text(account, bank.name))


def action_export_csv(bank):
    account = bank.get_account(ask_required("Account number"))
    start = ask_date("From date")
    end = ask_date("To date")
    path = f"exports/{account.account_no}_statement.csv"
    rows = export_csv(account, path, start, end)
    success(f"Wrote {rows} row(s) to {path}")


def action_freeze_toggle(bank):
    account = bank.get_account(ask_required("Account number"))
    choice = ask_choice("What do you want to do", {"1": "Freeze", "2": "Unfreeze"})
    if choice == "Freeze":
        account.freeze()
    else:
        account.unfreeze()
    success(f"{account.account_no} is now {account.status}")


def action_month_end(bank):
    count = bank.run_month_end()
    success(f"Month-end processed for {count} account(s)")


def action_list_accounts(bank):
    accounts = bank.list_accounts()
    if not accounts:
        print("  No accounts yet. Use option 1 or 11.")
        return
    for account in accounts:
        print("  " + account_row(account))
    print(f"  Total held by bank: {format_rupees(bank.total_deposits())}")


def action_load_demo(bank):
    bank.open_account("savings", "Asha Verma", 25000)
    bank.open_account("savings", "Ravi Kumar", 8000)
    bank.open_account("current", "Mehta Traders", 10000, overdraft_limit=40000)
    success("Created 3 demo accounts")
    action_list_accounts(bank)


MENU = [
    ("1", "Open account", action_open_account),
    ("2", "Deposit", action_deposit),
    ("3", "Withdraw", action_withdraw),
    ("4", "Transfer", action_transfer),
    ("5", "Mini statement (last few transactions)", action_mini_statement),
    ("6", "Full statement", action_full_statement),
    ("7", "Export statement to CSV", action_export_csv),
    ("8", "Freeze / unfreeze account", action_freeze_toggle),
    ("9", "Run month-end (interest and charges)", action_month_end),
    ("10", "List all accounts", action_list_accounts),
    ("11", "Load demo accounts", action_load_demo),
    ("0", "Exit", None),
]


def print_menu():
    print("\n===== MENU =====")
    for key, label, _ in MENU:
        print(f"  {key:>2}. {label}")


def run_menu(bank):
    actions = {key: func for key, _, func in MENU if func is not None}
    print(f"\nWelcome to {bank.name}")
    while True:
        print_menu()
        choice = input("Choose an option: ").strip()
        if choice == "0":
            print("Goodbye!")
            return
        action = actions.get(choice)
        if action is None:
            print("  [ERROR] Please type a number from the menu.")
            continue
        try:
            action(bank)
        except BankError as exc:
            # Business errors are shown nicely; real bugs are NOT caught here.
            print(f"  [ERROR] {exc}")
            log.warning("Refused: %s: %s", type(exc).__name__, exc)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # so the ₹ sign prints on Windows too
    setup_logging()
    bank = BankService(name="SimpleBank")
    try:
        run_menu(bank)
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")