from __future__ import annotations

from typing import List

from .models.receipt import Receipt
from .models.tax import TaxLine
from .parsing.date_extractor import extract_date
from .text.normalizer import normalize
from .parsing.amounts_extractor import AmountsExtractor
from .parsing.merger import Merger
from .parsing.vendor_extractor import extract_vendor


class ExtractionService:
    def __init__(self):
        self.amounts = AmountsExtractor()
        self.merger = Merger()

    def extract(self, raw: str):
        norm = normalize(raw)

        print(f"norm: {norm}")
        vendor = extract_vendor(norm)
        date = extract_date(norm)

        parse_results = self.amounts.extract(norm)

        merged = self.merger.merge(parse_results)

        if not merged:
            return type("Res", (), {"document": None})

        def _f(x):  # Decimal -> float | None
            return float(x) if x is not None else None

        details: List[TaxLine] = []
        for d in merged.tva_details:
            rate = float(d.rate) if d.rate is not None else 0.0
            details.append(TaxLine(
                rate=rate,
                base_ht=_f(d.base_ht) or 0.0,
                tva=_f(d.tva) or 0.0,
                ttc=_f(d.ttc) or 0.0,
            ))

        doc = Receipt(
            vendor=vendor,
            date=date,
            total_ttc=_f(merged.total_ttc),
            total_ht=_f(merged.total_ht),
            tva_amount=_f(merged.tva_amount),
            tva_details=details,
            payment_method=None,
            table_number=None,
            covers=None,
            coherent=True,
            confidence=min(1.0, merged.confidence),
            raw_text=norm,
            notes=merged.notes,
        )
        return type("Res", (), {"document": doc})
