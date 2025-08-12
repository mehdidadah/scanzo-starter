from __future__ import annotations
import re
from typing import Optional
from .base_rule import ParseResult, TaxRow, to_dec

class TotalTTCRule:
    name = "total_ttc"
    priority = 82
    _ttc = re.compile(r"(?i)\b(?:total\s*)?t\.?\s*t\.?\s*c\.?\b.*?([\-]?\d[\d\s.,]*)")

    def apply(self, text: str) -> Optional[ParseResult]:
        m = self._ttc.search(text)
        if not m:
            return None
        return ParseResult(
            total_ht=None, total_ttc=to_dec(m.group(1)), tva_amount=None,
            tva_details=[], confidence=0.55, notes=["total_ttc"]
        )