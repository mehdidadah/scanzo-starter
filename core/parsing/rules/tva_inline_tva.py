# scanzo/core/parsing/rules/tva_inline_tva.py
from __future__ import annotations
import re
from typing import Optional
from .base_rule import ParseResult, TaxRow

class TvaInlineTvaRule:
    """
    Détecte 'TVA 10 %' (quand les montants sont illisibles).
    Sert au fallback: si on n'a qu'un TTC + un seul taux, on calcule HT/TVA.
    """
    name = "tva_inline_tva"
    priority = 50

    _rate = re.compile(r"(?i)\bTVA\s*([0-9]{1,2}(?:[.,][0-9]{1,2})?)\s*%")

    def apply(self, text: str) -> Optional[ParseResult]:
        rates = set()
        for m in self._rate.finditer(text):
            r = float(m.group(1).replace(",", "."))
            rates.add(r)
        if not rates:
            return None
        # garde un seul si unique
        details = [TaxRow(rate=r, base_ht=None, tva=None, ttc=None) for r in sorted(rates)]
        return ParseResult(tva_details=details, confidence=0.3, notes=["tva_inline_tva"])