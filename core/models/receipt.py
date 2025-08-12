from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional
from .tax import TaxLine

@dataclass
class Receipt:
    vendor: Optional[str]
    date: Optional[str]
    total_ttc: Optional[float]
    total_ht: Optional[float]
    tva_amount: Optional[float]
    tva_details: List[TaxLine]
    payment_method: Optional[str]
    table_number: Optional[str]
    covers: Optional[int]
    coherent: Optional[bool]
    confidence: Optional[float]
    raw_text: str
    notes: List[str]