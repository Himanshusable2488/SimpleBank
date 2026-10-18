"""BankService: the layer the menu talks to. It owns all accounts and the transfer logic."""
import logging
from datetime import datetime
from decimal import Decimal

from simplebank.accounts import CurrentAccount, FixedDepositAccount, SavingsAccount
from simplebank.errors import (
    BankError,
    RuleViolationError,
    TransferRolledBackError,
    UnknownAccountError,
)
from simplebank.money import format_rupees, positive_money

log = logging.getLogger(__name__)


class BankService:
    ACCOUNT_KINDS = {
        "SAVINGS": SavingsAccount,
        "CURRENT": CurrentAccount,
        "FD": FixedDepositAccount,
    }

    def __init__(self, name="SimpleBank", prefix="SB", clock=datetime.now):
        self.name = name
        self._prefix = prefix
        self._clock = clock
        self._next_number = 1001      # belongs to THIS bank object, not shared globally
        self._accounts = {}           # account number -> account object

    # ----- accounts -----
    def open_account(self, kind, holder_name, opening_balance=0, **options):
        key = str(kind).strip().upper()
        if key not in self.ACCOUNT_KINDS:
            raise RuleViolationError(
                f"Unknown account type {kind!r}. Choose from {sorted(self.ACCOUNT_KINDS)}"
            )
        number = f"{self._prefix}{self._next_number}"
        account = self.ACCOUNT_KINDS[key](
            number, holder_name, opening_balance, clock=self._clock, **options
        )
        # Only reached if the account was created successfully, so no number is wasted.
        self._accounts[number] = account
        self._next_number += 1
        log.info("Opened %s account %s for %s", key, number, account.holder_name)
        return account

    def get_account(self, account_no):
        key = str(account_no).strip().upper()
        try:
            return self._accounts[key]
        except KeyError:
            raise UnknownAccountError(account_no) from None

    def list_accounts(self):
        return list(self._accounts.values())

    def total_deposits(self):
        return sum((acc.balance for acc in self._accounts.values()), Decimal("0.00"))

    # ----- money movement -----
    def deposit(self, account_no, amount):
        return self.get_account(account_no).deposit(amount)

    def withdraw(self, account_no, amount):
        return self.get_account(account_no).withdraw(amount)

    def transfer(self, from_no, to_no, amount):
        """Move money between two accounts: either both steps happen, or neither."""
        source = self.get_account(from_no)
        target = self.get_account(to_no)
        if source is target:
            raise RuleViolationError("Sender and receiver must be different accounts")
        amount = positive_money(amount)

        # Step 1: take the money out. If this fails nothing has changed yet.
        source.withdraw(amount, f"Transfer to {target.account_no}", category="TRANSFER_OUT")

        # Step 2: put it in. If this fails, give the money back to the sender.
        try:
            target.deposit(amount, f"Transfer from {source.account_no}", category="TRANSFER_IN")
        except Exception as exc:
            source.restore(amount, f"Reversal: transfer to {target.account_no} failed")
            log.warning("Transfer %s -> %s of %s rolled back: %s",
                        source.account_no, target.account_no, amount, exc)
            if isinstance(exc, BankError):
                raise TransferRolledBackError(
                    f"Transfer of {format_rupees(amount)} from {source.account_no} to "
                    f"{target.account_no} failed and was rolled back"
                ) from exc
            raise   # an unexpected bug: money is restored, but let the bug show

        log.info("Transfer %s -> %s of %s done", source.account_no, target.account_no, amount)

    def run_month_end(self):
        for account in self._accounts.values():
            account.month_end()
        log.info("Month-end processed for %d accounts", len(self._accounts))
        return len(self._accounts)