from __future__ import annotations
import re
from typing import Optional
from .base_rule import ParseResult, TaxRow, to_dec, fix_ttc

class TvaParentheticalRule:
    """
    Ex: '10% : 6,95 € (69,55 € HT / 76,50 € TTC)'
    """
    name = "tva_parenthetical"
    priority = 60

    _re = re.compile(
        r"(?i)\b([0-9]{1,2}(?:[.,][0-9]{1,2})?)%\s*[:\-]?\s*([\-]?[0-9][\d\s.,]*)\s*(?:€|eur|euros?)?\s*\(\s*([\-]?[0-9][\d\s.,]*)\s*(?:€|eur|euros?)?\s*HT\s*/\s*([\-]?[0-9][\d\s.,]*)\s*(?:€|eur|euros?)?\s*TTC\s*\)"
    )

    def apply(self, text: str) -> Optional[ParseResult]:
        m = self._re.search(text)
        if not m:
            return None
        rate = float(m.group(1).replace(",", "."))
        tva = to_dec(m.group(2))
        ht = to_dec(m.group(3))
        ttc = to_dec(m.group(4))
        ht, tva, ttc = fix_ttc(ht, tva, ttc)
        return ParseResult(
            total_ht=ht, total_ttc=ttc, tva_amount=tva,
            tva_details=[TaxRow(rate=rate, base_ht=ht, tva=tva, ttc=ttc)],
            confidence=0.95, notes=["tva_parenthetical"]
        )