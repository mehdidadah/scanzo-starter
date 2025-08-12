from __future__ import annotations
import re
from typing import Optional, List, Tuple, Set
from decimal import Decimal
from .base_rule import ParseResult, TaxRow, to_dec, quant2, normalize_rate

# ligne = un nombre seul éventuellement suivi de €
_NUM_LINE = re.compile(r"^\s*([\-]?\d[\d\s.,]*)\s*(?:€|eur|euros?)?\s*$", re.I)

# indices de taux: "TVA 10.00", "TVA: 5,5%"
_RATE_HINT = re.compile(r"(?i)\btva\b[^%\n\r]*?([0-9]{1,2}(?:[.,][0-9]{1,2})?)\s*%?")

# ancres larges
_ANCHOR = re.compile(r"(?i)\b(ht|tva|ttc|base\s*ht|base\s*ttc|mt\.?\s*tva|montant\s*tva)\b")

def _almost_eq(a: Decimal, b: Decimal, tol: Decimal = Decimal("0.02")) -> bool:
    return abs(a - b) <= tol

def _ratio_ok(tva: Decimal, ht: Decimal) -> bool:
    if ht == 0:
        return False
    r = (tva / ht)
    # bornes classiques FR (2.1%, 5.5%, 10%, 20%) avec une marge
    return Decimal("0.005") <= r <= Decimal("0.30")

def _to3(vals: List[Decimal]) -> Optional[Tuple[Decimal, Decimal, Decimal]]:
    """Retourne (ht, tva, ttc) si a+b≈c; choisit tva comme le plus petit des deux (a,b) si plausible."""
    if len(vals) != 3:
        return None
    a, b, c = vals
    if not _almost_eq(a + b, c):
        return None
    # heuristique robuste: en l'absence d'en-tête fiable, TVA = min(a,b) et ratio plausible
    h1, t1 = (a, b) if a >= b else (b, a)
    if _ratio_ok(t1, h1):
        return (h1, t1, c)
    # sinon on tolère l'autre permutation si plausible
    h2, t2 = (b, a)
    if _ratio_ok(t2, h2):
        return (h2, t2, c)
    # dernier recours: garder (a,b,c)
    return (a, b, c)

def _header_order(lines: List[str], i: int) -> List[str]:
    """
    Essaie d'inférer un ordre de labels sur 3-4 lignes autour de l'ancre.
    Ex: ["Mt. TVA", "Base HT Base TTC"] -> ["TVA", "HT", "TTC"].
    """
    txt = " ".join(lines[max(0, i-2):min(len(lines), i+3)])
    order: List[Tuple[int,str]] = []
    for label, canon in [("Mt. TVA", "TVA"), ("Montant TVA", "TVA"), ("TVA", "TVA"),
                         ("Base HT", "HT"), ("HT", "HT"),
                         ("Base TTC", "TTC"), ("TTC", "TTC")]:
        pos = txt.lower().find(label.lower())
        if pos != -1:
            order.append((pos, canon))
    order.sort(key=lambda x: x[0])
    dedup: List[str] = []
    for _, canon in order:
        if canon not in dedup:
            dedup.append(canon)
    # on veut idéalement les trois
    return dedup

class TvaVerticalRule:
    """
    Règle verticale robuste:
    - détecte des blocs à partir d'ancres (HT/TVA/TTC, Mt. TVA, Base HT/TTC, …)
    - associe les 3 nombres qui suivent en (HT, TVA, TTC) avec le contexte des entêtes
    - déduplique par indices ET par valeurs (évite répétitions du même résumé)
    - calcule le taux si absent (tva_details.rate toujours renseigné)
    """
    name = "tva_vertical"
    priority = 78

    def apply(self, text: str) -> Optional[ParseResult]:
        lines = [ln.strip() for ln in text.splitlines()]
        anchors = [i for i, ln in enumerate(lines) if _ANCHOR.search(ln)]
        if not anchors:
            return None

        seen_idx: Set[Tuple[int,int,int]] = set()
        seen_vals: Set[Tuple[Decimal,Decimal,Decimal]] = set()
        triples: List[Tuple[Optional[float], Decimal, Decimal, Decimal]] = []

        for idx in anchors:
            order = _header_order(lines, idx)  # ex ["TVA","HT","TTC"] ou ["HT","TVA","TTC"] etc.
            last_rate: Optional[float] = None
            buf_vals: List[Tuple[int,Decimal]] = []

            j0 = max(0, idx - 2)
            j1 = min(len(lines), idx + 40)
            j = j0
            while j < j1:
                ln = lines[j]
                # indice de taux
                mr = _RATE_HINT.search(ln)
                if mr:
                    try:
                        last_rate = float(mr.group(1).replace(",", "."))
                    except Exception:
                        pass

                m = _NUM_LINE.match(ln)
                if m:
                    try:
                        val = to_dec(m.group(1))
                    except Exception:
                        j += 1
                        continue
                    buf_vals.append((j, val))

                    # essaye par fenêtre glissante de 3
                    while len(buf_vals) >= 3:
                        (i1, v1), (i2, v2), (i3, v3) = buf_vals[-3:]
                        if (i1, i2, i3) in seen_idx:
                            break

                        trip: Optional[Tuple[Decimal,Decimal,Decimal]] = None
                        if len(order) >= 3:
                            # on mappe selon l'ordre détecté: ex order=["TVA","HT","TTC"]
                            mapping = {"HT": None, "TVA": None, "TTC": None}
                            # place v1,v2,v3 sur order[0], order[1], order[2]
                            mapping[order[0]] = v1
                            mapping[order[1]] = v2
                            mapping[order[2]] = v3
                            ht, tva, ttc = mapping["HT"], mapping["TVA"], mapping["TTC"]
                            if None not in (ht, tva, ttc) and _almost_eq(ht + tva, ttc) and _ratio_ok(tva, ht):
                                trip = (ht, tva, ttc)
                        # fallback générique
                        if not trip:
                            trip = _to3([v1, v2, v3])

                        if trip:
                            ht, tva, ttc = trip
                            key_idx = (i1, i2, i3)
                            key_val = (quant2(ht), quant2(tva), quant2(ttc))
                            if key_val not in seen_vals:
                                seen_idx.add(key_idx)
                                seen_vals.add(key_val)
                                triples.append((last_rate, ht, tva, ttc))
                            break  # on avance; évite de reconsommer les mêmes 3 lignes à répétition
                        else:
                            # pas cohérent -> on glisse
                            break
                else:
                    # coupe la série s'il y a un blanc et qu'on a déjà pris qqch
                    if not ln and buf_vals:
                        buf_vals = []
                j += 1

        if not triples:
            return None

        # synthèse avec taux obligatoires
        details: List[TaxRow] = []
        tot_ht = Decimal("0")
        tot_tva = Decimal("0")
        tot_ttc = Decimal("0")

        for rate, ht, tva, ttc in triples:
            # calcule un taux si absent
            if (rate is None or rate == 0.0) and ht and ht != 0:
                try:
                    rate = float((tva / ht * 100).quantize(Decimal("0.01")))
                except Exception:
                    rate = None
            # bornes de sécurité: si le ratio est aberrant, on jette ce triple
            if not _ratio_ok(tva, ht) or not _almost_eq(ht + tva, ttc):
                continue

            rate = normalize_rate(rate, ht, tva)
            details.append(TaxRow(rate=rate, base_ht=quant2(ht), tva=quant2(tva), ttc=quant2(ttc)))
            tot_ht += ht
            tot_tva += tva
            tot_ttc += ttc

        if not details:
            return None

        # dédup finale par valeurs (au cas où)
        uniq: List[TaxRow] = []
        seen_final: Set[Tuple[Decimal,Decimal,Decimal]] = set()
        for d in details:
            key = (d.base_ht, d.tva, d.ttc)
            if key not in seen_final:
                seen_final.add(key)
                uniq.append(d)

        return ParseResult(
            total_ht=quant2(sum((d.base_ht for d in uniq), Decimal("0"))),
            total_ttc=quant2(sum((d.ttc for d in uniq), Decimal("0"))),
            tva_amount=quant2(sum((d.tva for d in uniq), Decimal("0"))),
            tva_details=uniq,
            confidence=0.85 if len(uniq) > 1 else 0.80,
            notes=["tva_vertical"],
        )