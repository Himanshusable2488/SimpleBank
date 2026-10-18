from decimal import Decimal

import pytest

from simplebank.errors import BadAmountError
from simplebank.money import format_rupees, non_negative_money, positive_money, to_money


def test_rounds_half_up():
    assert to_money("2500.755") == Decimal("2500.76")


def test_accepts_commas_and_floats():
    assert to_money("1,500") == Decimal("1500.00")
    assert to_money(0.1) == Decimal("0.10")


def test_decimal_adds_exactly():
    assert to_money("0.1") + to_money("0.2") == Decimal("0.30")


@pytest.mark.parametrize("bad", [None, True, "abc", "", float("nan"), float("inf"), "1e999999"])
def test_rejects_bad_input(bad):
    with pytest.raises(BadAmountError):
        to_money(bad)


def test_positive_and_non_negative_rules():
    with pytest.raises(BadAmountError):
        positive_money(0)
    with pytest.raises(BadAmountError):
        non_negative_money(-1)
    assert non_negative_money(0) == Decimal("0.00")


def test_format_rupees():
    assert format_rupees(Decimal("1234.5")) == "₹1,234.50"
    assert format_rupees(Decimal("-40.00")) == "-₹40.00"