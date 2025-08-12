def coherent(doc, eps: float = 0.1) -> bool:
    if doc.total_ttc is None:
        return False
    if doc.total_ht is not None and doc.tva_amount is not None:
        if abs((doc.total_ht + doc.tva_amount) - doc.total_ttc) <= eps:
            return True
    if getattr(doc, "tva_details", None):
        s = 0.0
        for line in doc.tva_details:
            if line.ttc is not None:
                s += float(line.ttc)
            else:
                s += float(line.base_ht or 0) + float(line.tva or 0)
        if abs(s - doc.total_ttc) <= eps:
            return True
    return False


def confidence_proxy(doc) -> float:
    weights = {"vendor": 0.15, "date": 0.15, "ttc": 0.25, "ht": 0.15, "tva": 0.15, "tva_details": 0.15}
    score = 0.0
    if doc.vendor: score += weights["vendor"]
    if doc.date: score += weights["date"]
    if doc.total_ttc is not None: score += weights["ttc"]
    if doc.total_ht is not None: score += weights["ht"]
    if doc.tva_amount is not None: score += weights["tva"]
    if getattr(doc, "tva_details", None):
        if len(doc.tva_details) > 0:
            score += weights["tva_details"]
    if coherent(doc): score += 0.10
    return min(score, 1.0)