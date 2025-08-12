# scanzo/core/parsing/rules/tva_inline_any.py
from __future__ import annotations
import re
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from typing import Optional, List, Tuple

from .base_rule import ParseResult, TaxRow, to_dec, fix_ttc

_NUM  = re.compile(r"(?<!\d)(\d{1,9}[.,]\d{2})(?!\d)")
_RATE = re.compile(r"(?i)\b(\d{1,2}(?:[.,]\d{1,2})?)\s*%")
_HAS_TVA = re.compile(r"(?i)\btva\b")
_IS_TOTAL = re.compile(r"(?i)\b(total(?:\s*t\.?t\.?c\.?)?|cb|montant\s+total)\b")

Q2 = Decimal("0.01")
HUNDRED = Decimal("100")

def _q2(x: Decimal) -> Decimal:
    return x.quantize(Q2, rounding=ROUND_HALF_UP)

def _grab_amounts(line: str) -> List[Decimal]:
    vals: List[Decimal] = []
    for m in _NUM.finditer(line):
        v = to_dec(m.group(1))
        if v is not None:
            vals.append(_q2(v))
    return vals

def _mad_filter(values: List[Decimal]) -> List[Decimal]:
    # retire les valeurs isolées anormalement loin du centre de la ligne
    if len(values) < 3:
        return values[:]  # rien à filtrer
    m = median(values)
    abs_dev = [ (v - m).copy_abs() for v in values ]
    mad = median(abs_dev)
    if mad == 0:
        return values[:]
    k = Decimal("12")  # tolérant : on n’enlève que les vrais ovnis
    return [v for v in values if ((v - m).copy_abs() / mad) <= k]

def _rate_penalty_if_implicit(ht: Decimal, tva: Decimal) -> Decimal:
    # si pas de taux explicite, on pénalise fortement les taux implicites absurdes
    if ht <= 0:
        return Decimal("5.00")  # évite de choisir des ht≈0
    r = (tva * HUNDRED / ht)
    # fenêtre large [1%, 25%] pour rester générique (0% existe mais rare sur tickets resto)
    if r < Decimal("1.0") or r > Decimal("25.0"):
        return Decimal("5.00") + (r - Decimal("13.0")).copy_abs() / Decimal("10.0")
    return Decimal("0.00")

def _score_triplet(ht: Decimal, tva: Decimal, ttc: Decimal, rate: Optional[Decimal]) -> Decimal:
    s = (ht + tva - ttc).copy_abs()
    if rate is not None and ht > 0:
        s += (tva - _q2(ht * rate / HUNDRED)).copy_abs()
    if rate is None:
        s += _rate_penalty_if_implicit(ht, tva)
    return s

def _best_triplet(values: List[Decimal], rate: Optional[Decimal]) -> Optional[Tuple[Decimal,Decimal,Decimal]]:
    n = len(values)
    if n < 2:
        return None

    best = None
    best_score: Optional[Decimal] = None

    # fenêtres consécutives (préférence naturelle)
    if n >= 3:
        for i in range(n - 2):
            ht, tva, ttc = values[i], values[i+1], values[i+2]
            score = _score_triplet(ht, tva, ttc, rate)
            if best_score is None or score < best_score:
                best, best_score = (ht, tva, ttc), score

    # toutes les paires -> reconstruire le 3e
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a, b = values[i], values[j]
            # (ht, ttc) -> tva
            if b > a:
                score = _score_triplet(a, _q2(b - a), b, rate)
                if best_score is None or score < best_score:
                    best, best_score = (a, _q2(b - a), b), score
            # (tva, ttc) -> ht
            if b > a:
                score = _score_triplet(_q2(b - a), a, b, rate)
                if best_score is None or score < best_score:
                    best, best_score = (_q2(b - a), a, b), score
            # (ht, tva) -> ttc
            score = _score_triplet(a, b, _q2(a + b), rate)
            if best_score is None or score < best_score:
                best, best_score = (a, b, _q2(a + b)), score

    if not best:
        return None

    ht, tva, ttc = best
    # tolérance 1€ sur HT+TVA≈TTC
    if (ht + tva - ttc).copy_abs() > Decimal("1.00"):
        return None

    ht, tva, ttc = fix_ttc(ht, tva, ttc)
    return ht, tva, ttc

class TvaInlineAnyRule:
    """
    Règle générique lignes 'TVA ...' :
    - pas de plafond de montant,
    - MAD pour écarter les ovnis,
    - pénalité sur taux implicite si le taux n’est pas imprimé,
    - réconciliation 'TOTAL' dans les 8 lignes suivantes.
    """
    name = "tva_inline_any"
    priority = 65

    def apply(self, text: str) -> Optional[ParseResult]:
        lines = [ln.strip() for ln in text.splitlines()]
        for idx, raw_line in enumerate(lines):
            if not _HAS_TVA.search(raw_line):
                continue

            rate: Optional[Decimal] = None
            m_rate = _RATE.search(raw_line)
            if m_rate:
                rate = to_dec(m_rate.group(1))

            values = _mad_filter(_grab_amounts(raw_line))
            if len(values) < 2:
                continue

            triplet = _best_triplet(values, rate)

            # Réconciliation via un TOTAL proche si besoin ou pour confirmer un (HT,TVA)
            if (not triplet or (triplet and (triplet[0] + triplet[1] - triplet[2]).copy_abs() > Decimal("0.20"))):
                # choisir 2 valeurs cohérentes (les 2 plus petites marchent bien après MAD)
                small = sorted(values)[:2]
                if len(small) == 2 and small[1] >= small[0]:
                    ht_cand, tva_cand = small[1], small[0]
                    for j in range(1, 9):  # jusque 8 lignes plus bas
                        if idx + j >= len(lines):
                            break
                        nxt = lines[idx + j]
                        if _IS_TOTAL.search(nxt):
                            tot = _grab_amounts(nxt)
                            if tot:
                                ttc_cand = tot[-1]
                                if (ht_cand + tva_cand - ttc_cand).copy_abs() <= Decimal("1.00"):
                                    # si pas de taux imprimé, calcule le taux pour tva_details
                                    r = rate
                                    if r is None and ht_cand > 0:
                                        r = _q2(tva_cand * HUNDRED / ht_cand)
                                    ht, tva, ttc = fix_ttc(ht_cand, tva_cand, ttc_cand)
                                    return ParseResult(
                                        total_ht=ht, total_ttc=ttc, tva_amount=tva,
                                        tva_details=[TaxRow(rate=float(r) if r is not None else None,
                                                            base_ht=ht, tva=tva, ttc=ttc)],
                                        confidence=Decimal("0.93"),
                                        notes=["tva_inline_any", "reconciled_total"],
                                    )

            if triplet:
                ht, tva, ttc = triplet
                r = rate
                if r is None and ht > 0:
                    r = _q2(tva * HUNDRED / ht)
                return ParseResult(
                    total_ht=ht, total_ttc=ttc, tva_amount=tva,
                    tva_details=[TaxRow(rate=float(r) if r is not None else None,
                                        base_ht=ht, tva=tva, ttc=ttc)],
                    confidence=Decimal("0.90"),
                    notes=["tva_inline_any"],
                )

        return None