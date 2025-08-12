from __future__ import annotations
import re
from typing import Optional
from .base_rule import ParseResult, TaxRow, to_dec

class TotalsLineRule:
    """
    Capte 'TOTAL HT ...', 'TOTAL TTC ...', 'TVA ...' en lignes.
    Sert de filet de sécurité / complément.
    """
    name = "totals_line"
    priority = 80

    _ttc = re.compile(r"(?i)\btotal\s*t\.?\s*t\.?\s*c\.?\b.*?([\-]?\d[\d\s.,]*)")
    _ht  = re.compile(r"(?i)\btotal\s*ht\b.*?([\-]?\d[\d\s.,]*)")
    _tva = re.compile(r"(?i)\btotal\s*tva\b.*?([\-]?\d[\d\s.,]*)")

    def apply(self, text: str) -> Optional[ParseResult]:
        mttc = self._ttc.search(text)
        mht  = self._ht.search(text)
        mtva = self._tva.search(text)

        if not (mttc or mht or mtva):
            return None

        total_ttc = to_dec(mttc.group(1)) if mttc else None
        total_ht  = to_dec(mht.group(1))  if mht  else None
        tva_amt   = to_dec(mtva.group(1)) if mtva else None

        return ParseResult(
            total_ht=total_ht, total_ttc=total_ttc, tva_amount=tva_amt,
            tva_details=[], confidence=0.7, notes=["totals_line"]
        )