from __future__ import annotations

import re
from typing import Optional, List

from .base_rule import ParseResult, TaxRow, to_dec, fix_ttc


class TvaInlineColsRule:
    """
    Ex:
      CODE   Taux    TVA     HT      TTC
      B      10.00%  2,44    24,36   26,80
    """
    name = "tva_inline_cols"
    priority = 70

    header = re.compile(r"(?i)\b(taux).*(tva).*(ht).*(ttc)\b")
    row = re.compile(
        r"(?ix)^[A-Z0-9\-]+\s+([0-9]{1,2}(?:[.,][0-9]{1,2})?)\s*%?\s+([\-]?\d[\d\s.,]*)\s+([\-]?\d[\d\s.,]*)\s+([\-]?\d[\d\s.,]*)"
    )

    def apply(self, text: str) -> Optional[ParseResult]:
        lines = [ln.strip() for ln in text.splitlines()]
        blocks: List[TaxRow] = []
        in_table = False
        for ln in lines:
            if not in_table and self.header.search(ln):
                in_table = True
                continue
            if not in_table:
                continue
            m = self.row.match(ln)
            if not m:
                # on quitte la table sur la 1re ligne non conforme après l'entête
                if blocks:
                    break
                continue
            rate = float(m.group(1).replace(",", "."))
            tva = to_dec(m.group(2))
            ht = to_dec(m.group(3))
            ttc = to_dec(m.group(4))
            ht, tva, ttc = fix_ttc(ht, tva, ttc)
            blocks.append(TaxRow(rate=rate, base_ht=ht, tva=tva, ttc=ttc))

        if not blocks:
            return None

        total_ht = sum([b.base_ht for b in blocks if b.base_ht is not None])  # type: ignore
        total_tva = sum([b.tva for b in blocks if b.tva is not None])          # type: ignore
        total_ttc = sum([b.ttc for b in blocks if b.ttc is not None])          # type: ignore

        return ParseResult(
            total_ht=total_ht, total_ttc=total_ttc, tva_amount=total_tva,
            tva_details=blocks, confidence=0.9, notes=["tva_inline_cols"]
        )