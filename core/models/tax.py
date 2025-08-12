from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class TaxLine:
    rate: float
    base_ht: float
    tva: float
    ttc: float