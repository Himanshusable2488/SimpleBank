"""Every error SimpleBank can raise on purpose.

All of them inherit from BankError. The menu catches BankError to show a
friendly message, while real bugs (TypeError, etc.) still crash loudly.
"""


class BankError(Exception):
    """Parent of every business error in this project."""


class BadAmountError(BankError):
    def __init__(self, value):
        self.value = value
        super().__init__(
            f"Invalid amount {value!r}: enter a positive number like 2500 or 2500.75"
        )


class LowBalanceError(BankError):
    def __init__(self, account_no, wanted, available):
        self.account_no = account_no
        self.wanted = wanted
        self.available = available
        self.shortfall = wanted - available
        super().__init__(
            f"{account_no}: you asked for ₹{wanted:,.2f} but only ₹{available:,.2f} "
            f"can be withdrawn (short by ₹{self.shortfall:,.2f})"
        )


class FrozenAccountError(BankError):
    def __init__(self, account_no):
        self.account_no = account_no
        super().__init__(f"{account_no} is frozen: customer transactions are blocked")


class UnknownAccountError(BankError):
    def __init__(self, account_no):
        self.account_no = account_no
        super().__init__(f"No account found with number {account_no!r}")


class TransferRolledBackError(BankError):
    """A transfer failed half-way and the sender's money was put back."""


class EarlyWithdrawalError(BankError):
    def __init__(self, account_no, months_left):
        self.account_no = account_no
        self.months_left = months_left
        super().__init__(
            f"{account_no}: fixed deposit has not matured, {months_left} month(s) to go"
        )


class DailyLimitError(BankError):
    def __init__(self, account_no, limit, remaining):
        self.account_no = account_no
        self.limit = limit
        self.remaining = remaining
        super().__init__(
            f"{account_no}: daily withdrawal limit is ₹{limit:,.2f}, "
            f"only ₹{remaining:,.2f} left for today"
        )


class RuleViolationError(BankError):
    """A product rule was broken (minimum deposit, no top-ups, bad setup...)."""