from __future__ import annotations
import re
from typing import Optional
from .base_rule import ParseResult, TaxRow, to_dec

class PaymentTotalRule:
    """
    Capte 'CB: 26,80 €' / 'CARTE BLEUE 26,80' comme TTC de paiement.
    Faible priorité, sert si on n'a rien d'autre.
    """
    name = "payment_total"
    priority = 90
    _re = re.compile(r"(?i)\b(?:cb|carte\s*bleue|esp(?:èces)?|cash|amex|visa|mastercard)\b\s*[:\-]?\s*([\-]?\d[\d\s.,]*)")

    def apply(self, text: str) -> Optional[ParseResult]:
        m = self._re.search(text)
        if not m:
            return None
        return ParseResult(
            total_ht=None, total_ttc=to_dec(m.group(1)), tva_amount=None,
            tva_details=[], confidence=0.5, notes=["payment_total"]
        )