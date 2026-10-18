"""Turns account data into text and CSV: statements, mini statements, exports."""
import csv
from pathlib import Path

from simplebank.money import format_rupees

LINE_WIDTH = 80


def account_row(account):
    """One-line summary used by 'List all accounts'."""
    return (f"{account.account_no} | {account.kind:<7} | {account.holder_name:<18} | "
            f"{format_rupees(account.balance):>14} | {account.status}")


def _entry_line(entry):
    return (f" #{entry.entry_no:<3} {entry.created_at:%d-%b-%Y %H:%M}  {entry.kind:<6} "
            f"{entry.amount:>12,.2f} {entry.balance_after:>13,.2f}  {entry.narration}")


def entries_between(account, start=None, end=None):
    """Ledger entries whose date is between start and end (both optional, inclusive)."""
    chosen = []
    for entry in account.ledger:
        day = entry.created_at.date()
        if start is not None and day < start:
            continue
        if end is not None and day > end:
            continue
        chosen.append(entry)
    return chosen


def _statement(title, account, entries):
    lines = [
        "=" * LINE_WIDTH,
        f" {title}",
        f" Account : {account.account_no}    Holder : {account.holder_name}    "
        f"Type : {account.kind}    Status : {account.status}",
        "-" * LINE_WIDTH,
    ]
    lines += [_entry_line(e) for e in entries] or [" (no transactions)"]
    lines += [
        "-" * LINE_WIDTH,
        f" Closing balance : {format_rupees(account.balance)}",
        "=" * LINE_WIDTH,
    ]
    return "\n".join(lines)


def statement_text(account, bank_name="SimpleBank"):
    return _statement(f"{bank_name} | FULL STATEMENT", account, list(account.ledger))


def mini_statement_text(account, count=5, bank_name="SimpleBank"):
    newest_first = list(reversed(account.ledger))[:count]
    return _statement(f"{bank_name} | LAST {count} TRANSACTIONS (newest first)", account, newest_first)


def export_csv(account, path, start=None, end=None):
    """Write the ledger to a CSV file and return how many rows were written."""
    rows = entries_between(account, start, end)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["entry_no", "date_time", "type", "category",
                         "amount", "balance_after", "narration"])
        for e in rows:
            writer.writerow([e.entry_no, e.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                             e.kind, e.category, e.amount, e.balance_after, e.narration])
    return len(rows)