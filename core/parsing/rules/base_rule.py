from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

Q2 = Decimal("0.01")
HUNDRED = Decimal("100")

CANON_RATES = [5.5, 10.0, 20.0]  # ajoute ici d'autres taux si besoin


def q2(x: Decimal) -> Decimal:
    return x.quantize(Q2, rounding=ROUND_HALF_UP)


def compute_rate_from_amounts(base_ht: Decimal | None, tva: Decimal | None) -> float | None:
    if base_ht is None or tva is None or base_ht <= 0:
        return None
    r = (tva * HUNDRED) / base_ht
    return float(q2(r))


def snap_rate(x: float | None) -> float | None:
    if x is None:
        return None
    d = Decimal(str(x))

    # 1) Snap sur taux canoniques si proche
    for r in CANON_RATES:
        if abs(float(d) - r) <= 0.3:  # tolérance 0.3 pt -> 9.98 -> 10.0
            return r

    # 2) Sinon, arrondi au dixième (utile pour 5.47 -> 5.5, etc.)
    return float(d.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def normalize_rate(rate: float | None, base_ht: Decimal | None, tva: Decimal | None) -> float | None:
    """
    Rend un taux propre en % :
      - None     -> déduit de HT/TVA si possible
      - 0<r<=1.5 -> c’était une fraction (0.1 => 10.0)
      - r<=0 ou r>=60 -> si on a HT/TVA, on préfère le taux déduit
      - si r ≈ montant HT/TVA (ex: '1.18'), on recalcule via HT/TVA
      - snap final vers taux canoniques
    """
    r_from = compute_rate_from_amounts(base_ht, tva)

    if rate is None:
        return snap_rate(r_from)

    try:
        d = Decimal(str(rate))
    except Exception:
        return snap_rate(r_from)

    # Heuristique "faux positif": le 'taux' est en fait un montant lu (ex: 1.18)
    if tva is not None and abs(float(d) - float(tva)) <= 0.05:
        return snap_rate(r_from)
    if base_ht is not None and abs(float(d) - float(base_ht)) <= 0.05:
        return snap_rate(r_from)

    # Fraction -> %
    if d > 0 and d <= Decimal("1.5"):
        d = d * HUNDRED

    # Aberrant -> préfère le taux déduit
    if d <= 0 or d >= Decimal("60"):
        return snap_rate(r_from)

    return snap_rate(float(d))


def taxrow_signature(rate: float | None, base_ht: Decimal | None, tva: Decimal | None, ttc: Decimal | None) -> tuple:
    """Signature pour dédupe stricte (taux arrondi à 0.01 %, montants à 0,01)."""
    r = None if rate is None else float(Decimal(str(rate)).quantize(Decimal("0.01")))

    def _q(x):
        return None if x is None else str(q2(x))

    return (r, _q(base_ht), _q(tva), _q(ttc))


def _to_decimal(s: str) -> Decimal:
    s = s.strip()
    # garde le signe, enlève espaces fines, remplace virgule par point
    s = s.replace("\u202f", " ").replace("\xa0", " ")
    out = []
    for ch in s:
        if ch.isdigit() or ch in "-.,":
            out.append(ch)
        elif ch == " ":
            continue
    s2 = "".join(out).replace(",", ".")
    if s2 in ("", "-", ".", "-."):
        raise ValueError("not a number")
    return Decimal(s2)


def quant2(x: Decimal | float | None) -> Optional[Decimal]:
    if x is None:
        return None
    if not isinstance(x, Decimal):
        x = Decimal(str(x))
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def to_dec(s: str) -> Decimal:
    return quant2(_to_decimal(s))  # type: ignore


@dataclass
class TaxRow:
    rate: Optional[float]  # sera rempli ou calculé au merge
    base_ht: Optional[Decimal]
    tva: Optional[Decimal]
    ttc: Optional[Decimal]


@dataclass
class ParseResult:
    total_ht: Optional[Decimal]
    total_ttc: Optional[Decimal]
    tva_amount: Optional[Decimal]
    tva_details: List[TaxRow]
    confidence: float
    notes: List[str]


def fix_ttc(ht: Optional[Decimal], tva: Optional[Decimal], ttc: Optional[Decimal]) -> tuple[
    Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
    """cohérence simple: si deux sont là, calcule le troisième."""
    if ht is not None and tva is not None:
        calc = quant2(ht + tva)
        if ttc is None or abs(calc - ttc) > Decimal("0.02"):
            ttc = calc
    elif ht is not None and ttc is not None:
        calc = quant2(ttc - ht)
        if tva is None or abs(calc - tva) > Decimal("0.02"):
            tva = calc
    elif tva is not None and ttc is not None:
        calc = quant2(ttc - tva)
        if ht is None or abs(calc - ht) > Decimal("0.02"):
            ht = calc
    return ht, tva, ttc
