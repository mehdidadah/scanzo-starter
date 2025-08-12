import re
from typing import Optional

# formats: 14-06-2025 | 03/07/2025 | texte FR
RE_NUM = re.compile(r"(?<!\d)(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})(?!\d)")
RE_FR = re.compile(
    r"(?i)\b(\d{1,2})\s+(janv|janvier|févr|fev|février|mars|avr|avril|mai|juin|juil|juillet|août|aout|sept|septembre|oct|octobre|nov|novembre|déc|dec|décembre)\s+(\d{4})"
)
MOIS = {
    "janv":"01","janvier":"01","févr":"02","fev":"02","février":"02","mars":"03","avr":"04","avril":"04","mai":"05",
    "juin":"06","juil":"07","juillet":"07","août":"08","aout":"08","sept":"09","septembre":"09",
    "oct":"10","octobre":"10","nov":"11","novembre":"11","déc":"12","dec":"12","décembre":"12"
}

def extract_date(text: str) -> Optional[str]:
    m = RE_NUM.search(text)
    if m:
        d, mth, y = m.group(1), m.group(2), m.group(3)
        if len(y) == 2:
            y = "20" + y
        return f"{int(d):02d}-{int(mth):02d}-{int(y):04d}"
    m = RE_FR.search(text)
    if m:
        d, mo, y = m.group(1), m.group(2).lower(), m.group(3)
        mm = MOIS.get(mo)
        if mm:
            return f"{int(d):02d}-{mm}-{int(y):04d}"
    return None