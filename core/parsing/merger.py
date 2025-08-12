from decimal import Decimal
from .rules.base_rule import ParseResult, TaxRow, quant2

def _dedup_rows(rows):
    seen = set()
    out = []
    for r in rows:
        key = (quant2(r.base_ht), quant2(r.tva), quant2(r.ttc))
        if key not in seen:
            seen.add(key)
            out.append(TaxRow(rate=r.rate, base_ht=quant2(r.base_ht), tva=quant2(r.tva), ttc=quant2(r.ttc)))
    return out

class Merger:
    def merge(self, results):
        if not results:
            return None
        # prends le meilleur avec TTC en base
        best = max(results, key=lambda r: (r.total_ttc is not None, r.confidence))
        total_ht = best.total_ht
        total_ttc = best.total_ttc
        tva_amount = best.tva_amount
        details = list(best.tva_details or [])

        # complète les manquants à partir des autres
        for r in sorted(results, key=lambda x: x.confidence, reverse=True):
            if total_ttc is None and r.total_ttc is not None:
                total_ttc = r.total_ttc
            if total_ht is None and r.total_ht is not None:
                total_ht = r.total_ht
            if tva_amount is None and r.tva_amount is not None:
                tva_amount = r.tva_amount
            if r.tva_details:
                details.extend(r.tva_details)

        details = _dedup_rows(details)

        # cohérence de base si possible
        if total_ht is None and total_ttc is not None and tva_amount is not None:
            total_ht = quant2(total_ttc - tva_amount)
        if total_ttc is None and total_ht is not None and tva_amount is not None:
            total_ttc = quant2(total_ht + tva_amount)
        if tva_amount is None and total_ht is not None and total_ttc is not None:
            tva_amount = quant2(total_ttc - total_ht)

        conf = min(1.0, max(r.confidence for r in results))
        notes = list({n for r in results for n in (r.notes or [])})

        return ParseResult(
            total_ht=total_ht, total_ttc=total_ttc, tva_amount=tva_amount,
            tva_details=details, confidence=conf, notes=notes
        )