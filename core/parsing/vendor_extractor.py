import re
from typing import Optional

BAD = re.compile(
    r"(?i)(siret|naf|tva|rcs|france|www\.|http|tel|tél|telephone|instagram|facebook|@|centre\s+commercial|cours|avenue|rue|boulevard|place|\b\d{5}\b)"
)

def extract_vendor(text: str) -> Optional[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # garde les 8 premières lignes, ignore info administrative/adresse
    cand = []
    for ln in lines[:12]:
        if BAD.search(ln):
            continue
        # plus de lettres que de chiffres
        letters = sum(c.isalpha() for c in ln)
        digits = sum(c.isdigit() for c in ln)
        if letters <= digits or len(ln) < 3:
            continue
        cand.append(ln)

    if not cand:
        return None

    # préfère une ligne majuscules raisonnable
    upper = [c for c in cand if c.upper() == c and 2 <= len(c) <= 40]
    if upper:
        return upper[0]

    # sinon la première ligne dominante
    return cand[0]