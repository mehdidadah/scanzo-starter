from __future__ import annotations
from typing import List
from .rule_registry import get_amount_rules
from .rules.base_rule import ParseResult

class AmountsExtractor:
    def extract(self, text: str) -> List[ParseResult]:
        out: List[ParseResult] = []
        for rule in get_amount_rules():
            res = rule.apply(text)
            if res:
                out.append(res)
        return out