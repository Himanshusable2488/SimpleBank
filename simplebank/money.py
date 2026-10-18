"""Helpers that turn user input into exact Decimal money.

Why Decimal? Floats cannot store 0.1 exactly (0.1 + 0.2 = 0.30000000000000004).
For money we want exact paise, so every amount goes through to_money().
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from simplebank.errors import BadAmountError

ONE_PAISA = Decimal("0.01")


def round_money(value):
    """Round any Decimal to 2 places, halves go up (2.675 -> 2.68)."""
    return value.quantize(ONE_PAISA, rounding=ROUND_HALF_UP)


def to_money(value):
    """Convert text/int/float/Decimal into a 2-place Decimal, or raise BadAmountError."""
    if value is None or isinstance(value, bool):
        raise BadAmountError(value)
    try:
        amount = Decimal(str(value).strip().replace(",", ""))
        if not amount.is_finite():
            raise BadAmountError(value)
        return round_money(amount)
    except InvalidOperation:
        raise BadAmountError(value) from None


def positive_money(value):
    amount = to_money(value)
    if amount <= 0:
        raise BadAmountError(value)
    return amount


def non_negative_money(value):
    amount = to_money(value)
    if amount < 0:
        raise BadAmountError(value)
    return amount


def format_rupees(amount):
    sign = "-" if amount < 0 else ""
    return f"{sign}₹{abs(amount):,.2f}"