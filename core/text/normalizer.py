# normalizer.py (complète ta fonction normalize_text)
import re

_RE_GLUED_AMOUNTS = re.compile(r"([.,]\d{2})(?=\d)")
_RE_MULTI_AMOUNTS = re.compile(r"(\d{1,8}[.,]\d{2})(?=(\d{1,8}[.,]\d{2}))")

def _fix_glued_amounts(s: str) -> str:
    # 1) ... ,00SUITE -> ... ,00 SUITE
    s = _RE_GLUED_AMOUNTS.sub(r"\1 ", s)
    # 2) ... 30,003,00 -> 30,00 3,00 (montants successifs sans espace)
    s = _RE_MULTI_AMOUNTS.sub(r"\1 ", s)
    return s

def normalize(raw: str) -> str:
    text = raw.replace("\xa0", " ").replace("€", " € ")
    text = _fix_glued_amounts(text)
    # … puis le reste de ta normalisation (lower/upper, trim lignes, etc.)
    return "\n".join(ln.strip() for ln in text.splitlines())