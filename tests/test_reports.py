import csv
from datetime import date, datetime, timedelta

from simplebank.accounts import SavingsAccount
from simplebank.reports import entries_between, export_csv, mini_statement_text, statement_text


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 10, 18, 10, 0)

    def __call__(self):
        return self.now


def make_account():
    clock = FakeClock()
    acc = SavingsAccount("SB1", "Asha", 10000, clock=clock)
    acc.deposit(111)
    clock.now += timedelta(days=1)
    acc.deposit(222)
    acc.deposit(333)
    return acc


def test_mini_statement_is_newest_first_and_limited():
    text = mini_statement_text(make_account(), count=2)
    assert text.index("333.00") < text.index("222.00")
    assert "Opening deposit" not in text and "111.00" not in text


def test_full_statement_shows_everything():
    text = statement_text(make_account())
    assert "Opening deposit" in text and "Closing balance" in text


def test_date_filter():
    acc = make_account()
    assert len(entries_between(acc, start=date(2026, 10, 19))) == 2
    assert len(entries_between(acc, end=date(2026, 10, 18))) == 2
    assert len(entries_between(acc)) == 4


def test_csv_export(tmp_path):
    path = tmp_path / "out" / "SB1.csv"
    rows = export_csv(make_account(), path)
    assert rows == 4
    with open(path, newline="", encoding="utf-8") as f:
        data = list(csv.reader(f))
    assert data[0][0] == "entry_no" and len(data) == 5