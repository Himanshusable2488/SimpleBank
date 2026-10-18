"""The account types: Savings, Current and Fixed Deposit.

BaseAccount holds everything the types share (balance, ledger, freeze,
deposit, withdraw). Each child class only adds what is different.
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal, InvalidOperation

from simplebank.entries import LedgerEntry
from simplebank.errors import (
    DailyLimitError,
    EarlyWithdrawalError,
    FrozenAccountError,
    LowBalanceError,
    RuleViolationError,
)
from simplebank.money import non_negative_money, positive_money, round_money, to_money

log = logging.getLogger(__name__)

ZERO = Decimal("0.00")


class BaseAccount(ABC):
    kind = "BASE"
    DAILY_LIMIT = None  # a child class can set a Decimal to limit withdrawals per day

    def __init__(self, account_no, holder_name, opening_balance=0, clock=datetime.now):
        # Check all inputs first, so a bad request creates nothing.
        if not isinstance(holder_name, str) or not holder_name.strip():
            raise RuleViolationError("Holder name cannot be empty")
        opening = non_negative_money(opening_balance)

        self._account_no = account_no
        self._holder_name = holder_name.strip().title()
        self._clock = clock          # a function that returns "now" (easy to fake in tests)
        self._balance = ZERO
        self._frozen = False
        self._ledger = []
        if opening > 0:
            self._record("CREDIT", "OPENING", opening, "Opening deposit")

    # ----- read-only views (no setters, so outside code cannot change them) -----
    @property
    def account_no(self):
        return self._account_no

    @property
    def holder_name(self):
        return self._holder_name

    @property
    def balance(self):
        return self._balance

    @property
    def status(self):
        return "FROZEN" if self._frozen else "ACTIVE"

    @property
    def ledger(self):
        return tuple(self._ledger)   # a tuple cannot be edited by the caller

    # ----- the one place where money actually moves -----
    def _record(self, kind, category, amount, narration):
        if kind == "CREDIT":
            self._balance += amount
        else:
            self._balance -= amount
        entry = LedgerEntry(
            entry_no=len(self._ledger) + 1,
            account_no=self._account_no,
            kind=kind,
            category=category,
            amount=amount,
            balance_after=self._balance,
            narration=narration,
            created_at=self._clock(),
        )
        self._ledger.append(entry)
        log.info("%s %s %s %s -> balance %s", self._account_no, kind, category, amount, self._balance)
        return entry

    def _require_active(self):
        if self._frozen:
            raise FrozenAccountError(self._account_no)

    def _withdrawn_today(self):
        """Money that left today through withdrawals/transfers (minus rolled-back ones)."""
        today = self._clock().date()
        used = ZERO
        for entry in self._ledger:
            if entry.created_at.date() != today:
                continue
            if entry.category in ("WITHDRAWAL", "TRANSFER_OUT"):
                used += entry.amount
            elif entry.category == "REVERSAL":
                used -= entry.amount
        return used

    def _check_daily_limit(self, amount):
        if self.DAILY_LIMIT is None:
            return
        remaining = self.DAILY_LIMIT - self._withdrawn_today()
        if amount > remaining:
            raise DailyLimitError(self._account_no, self.DAILY_LIMIT, max(remaining, ZERO))

    def _check_withdraw_allowed(self):
        """Hook for children that need an extra rule (e.g. FD maturity). Default: nothing."""

    # ----- customer operations -----
    def deposit(self, amount, narration="Cash deposit", category="DEPOSIT"):
        self._require_active()
        amount = positive_money(amount)
        self._record("CREDIT", category, amount, narration)
        return self._balance

    def withdraw(self, amount, narration="Cash withdrawal", category="WITHDRAWAL"):
        # Same steps for every account type; only max_withdrawable() differs.
        self._require_active()
        amount = positive_money(amount)
        self._check_withdraw_allowed()
        self._check_daily_limit(amount)
        available = self.max_withdrawable()
        if amount > available:
            raise LowBalanceError(self._account_no, amount, available)
        self._record("DEBIT", category, amount, narration)
        return self._balance

    # ----- bank operations -----
    def restore(self, amount, narration):
        """Put back money after a failed transfer. Allowed even when frozen."""
        self._record("CREDIT", "REVERSAL", positive_money(amount), narration)

    def freeze(self):
        self._frozen = True
        log.info("%s frozen", self._account_no)

    def unfreeze(self):
        self._frozen = False
        log.info("%s unfrozen", self._account_no)

    # ----- every account type must define these two -----
    @abstractmethod
    def max_withdrawable(self):
        """How much the customer can take out right now."""

    @abstractmethod
    def month_end(self):
        """Add interest or charges for the month."""

    def __repr__(self):
        return f"{type(self).__name__}({self._account_no!r}, balance={self._balance})"


class SavingsAccount(BaseAccount):
    kind = "SAVINGS"
    MIN_BALANCE = Decimal("1000.00")
    ANNUAL_RATE = Decimal("0.035")        # 3.5% a year
    DAILY_LIMIT = Decimal("50000.00")

    def __init__(self, account_no, holder_name, opening_balance=MIN_BALANCE, clock=datetime.now):
        if non_negative_money(opening_balance) < self.MIN_BALANCE:
            raise RuleViolationError(
                f"Savings account needs at least ₹{self.MIN_BALANCE:,.2f} to open"
            )
        super().__init__(account_no, holder_name, opening_balance, clock)

    def max_withdrawable(self):
        return max(self._balance - self.MIN_BALANCE, ZERO)

    def month_end(self):
        interest = round_money(self._balance * self.ANNUAL_RATE / 12)
        if interest > 0:
            self._record("CREDIT", "INTEREST", interest, "Monthly interest")


class CurrentAccount(BaseAccount):
    kind = "CURRENT"
    OVERDRAFT_RATE = Decimal("0.14")      # 14% a year, only on the overdrawn part

    def __init__(self, account_no, holder_name, opening_balance=0,
                 overdraft_limit=50000, clock=datetime.now):
        limit = non_negative_money(overdraft_limit)
        super().__init__(account_no, holder_name, opening_balance, clock)
        self._overdraft_limit = limit

    @property
    def overdraft_limit(self):
        return self._overdraft_limit

    def max_withdrawable(self):
        return self._balance + self._overdraft_limit

    def month_end(self):
        if self._balance < 0:
            charge = round_money(-self._balance * self.OVERDRAFT_RATE / 12)
            if charge > 0:
                self._record("DEBIT", "CHARGE", charge, "Overdraft interest")


class FixedDepositAccount(BaseAccount):
    kind = "FD"

    def __init__(self, account_no, holder_name, opening_balance,
                 tenure_months=12, annual_rate=Decimal("0.07"), clock=datetime.now):
        opening = positive_money(opening_balance)
        if isinstance(tenure_months, bool) or not isinstance(tenure_months, int) or tenure_months <= 0:
            raise RuleViolationError("tenure_months must be a whole number above 0")
        try:
            rate = Decimal(str(annual_rate))
        except InvalidOperation:
            raise RuleViolationError("annual_rate must be a number") from None
        if not rate.is_finite() or not (0 < rate <= 1):
            raise RuleViolationError("annual_rate must be between 0 and 1 (0.07 means 7%)")

        super().__init__(account_no, holder_name, opening, clock)
        self._tenure_months = tenure_months
        self._annual_rate = rate
        self._months_done = 0

    @property
    def tenure_months(self):
        return self._tenure_months

    @property
    def is_matured(self):
        return self._months_done >= self._tenure_months

    @property
    def months_left(self):
        return max(self._tenure_months - self._months_done, 0)

    def _check_withdraw_allowed(self):
        if not self.is_matured:
            raise EarlyWithdrawalError(self._account_no, self.months_left)

    def max_withdrawable(self):
        return self._balance if self.is_matured else ZERO

    def deposit(self, amount, narration="", category="DEPOSIT"):
        # No top-ups at all. This also makes a transfer INTO an FD fail (and roll back).
        raise RuleViolationError(f"{self._account_no} is a fixed deposit: top-ups are not allowed")

    def month_end(self):
        if self.is_matured:
            return                       # interest is paid only during the tenure
        interest = round_money(self._balance * self._annual_rate / 12)
        if interest > 0:
            self._record("CREDIT", "INTEREST", interest, "Monthly FD interest")
        self._months_done += 1