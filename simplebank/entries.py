"""One line of an account's ledger (a single money movement)."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)  # frozen = cannot be edited after it is created
class LedgerEntry:
    entry_no: int            # 1, 2, 3... inside one account
    account_no: str
    kind: str                # "CREDIT" (money in) or "DEBIT" (money out)
    category: str            # OPENING, DEPOSIT, WITHDRAWAL, TRANSFER_IN, TRANSFER_OUT,
                             # INTEREST, CHARGE, REVERSAL
    amount: Decimal
    balance_after: Decimal
    narration: str
    created_at: datetime