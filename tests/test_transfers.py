from decimal import Decimal

import pytest

from simplebank.errors import (
    DailyLimitError, FrozenAccountError, LowBalanceError, RuleViolationError,
    TransferRolledBackError, UnknownAccountError,
)
from simplebank.service import BankService


@pytest.fixture
def bank():
    b = BankService()
    b.open_account("savings", "Asha Verma", 25000)    # SB1001
    b.open_account("savings", "Ravi Kumar", 8000)     # SB1002
    return b


def test_account_numbers_start_at_1001(bank):
    assert [a.account_no for a in bank.list_accounts()] == ["SB1001", "SB1002"]


def test_failed_opening_does_not_use_up_a_number(bank):
    with pytest.raises(RuleViolationError):
        bank.open_account("savings", "Poor Person", 10)
    assert bank.open_account("savings", "New Person", 5000).account_no == "SB1003"


def test_unknown_account_type_is_refused(bank):
    with pytest.raises(RuleViolationError):
        bank.open_account("gold", "Someone", 5000)


def test_successful_transfer_moves_money(bank):
    total = bank.total_deposits()
    bank.transfer("SB1001", "SB1002", 5000)
    assert bank.get_account("SB1001").balance == Decimal("20000.00")
    assert bank.get_account("SB1002").balance == Decimal("13000.00")
    assert bank.total_deposits() == total


def test_account_lookup_ignores_case_and_spaces(bank):
    assert bank.get_account(" sb1001 ").account_no == "SB1001"


def test_transfer_to_frozen_account_is_rolled_back(bank):
    bank.get_account("SB1002").freeze()
    total = bank.total_deposits()
    with pytest.raises(TransferRolledBackError) as info:
        bank.transfer("SB1001", "SB1002", 5000)
    assert isinstance(info.value.__cause__, FrozenAccountError)
    assert bank.total_deposits() == total
    assert bank.get_account("SB1001").balance == Decimal("25000.00")
    assert bank.get_account("SB1001").ledger[-1].category == "REVERSAL"


def test_transfer_into_fixed_deposit_is_rolled_back(bank):
    bank.open_account("fd", "Asha Verma", 100000, tenure_months=3)   # SB1003
    total = bank.total_deposits()
    with pytest.raises(TransferRolledBackError):
        bank.transfer("SB1001", "SB1003", 1000)
    assert bank.total_deposits() == total


def test_insufficient_funds_changes_nothing(bank):
    entries_before = len(bank.get_account("SB1002").ledger)
    with pytest.raises(LowBalanceError):
        bank.transfer("SB1002", "SB1001", 7500)       # only 7000 is withdrawable
    assert len(bank.get_account("SB1002").ledger) == entries_before


def test_cannot_transfer_to_same_account(bank):
    with pytest.raises(RuleViolationError):
        bank.transfer("SB1001", "SB1001", 100)


def test_unknown_account_in_transfer(bank):
    with pytest.raises(UnknownAccountError):
        bank.transfer("SB1001", "SB9999", 100)


def test_unexpected_crash_still_restores_the_money(bank, monkeypatch):
    source, target = bank.get_account("SB1001"), bank.get_account("SB1002")

    def broken_deposit(*args, **kwargs):
        raise RuntimeError("something unexpected")

    monkeypatch.setattr(target, "deposit", broken_deposit)
    with pytest.raises(RuntimeError):
        bank.transfer("SB1001", "SB1002", 5000)
    assert source.balance == Decimal("25000.00")


def test_rolled_back_transfer_does_not_use_up_daily_limit():
    bank = BankService()
    bank.open_account("savings", "Rich Sender", 200000)   # SB1001, limit 50,000/day
    bank.open_account("savings", "Frozen Receiver", 5000) # SB1002
    bank.get_account("SB1002").freeze()
    with pytest.raises(TransferRolledBackError):
        bank.transfer("SB1001", "SB1002", 40000)
    bank.withdraw("SB1001", 40000)                         # still allowed


def test_transfers_count_towards_daily_limit():
    bank = BankService()
    bank.open_account("savings", "Rich Sender", 200000)
    bank.open_account("savings", "Receiver", 5000)
    bank.transfer("SB1001", "SB1002", 40000)
    with pytest.raises(DailyLimitError):
        bank.withdraw("SB1001", 20000)


def test_month_end_runs_for_every_account(bank):
    bank.open_account("current", "Shop", 0, overdraft_limit=10000)
    bank.withdraw("SB1003", 1000)
    count = bank.run_month_end()
    assert count == 3
    assert bank.get_account("SB1001").ledger[-1].category == "INTEREST"
    assert bank.get_account("SB1003").ledger[-1].category == "CHARGE"