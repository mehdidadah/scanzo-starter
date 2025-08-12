import re

class TextCleaner:
    def process(self, text: str) -> str:
        # supprime artefacts invisibles, normalise espaces
        t = text.replace("\u3002", " ")
        t = re.sub(r"\u00A0", " ", t)  # nbsp -> space
        t = re.sub(r"\s+\n", "\n", t)
        t = re.sub(r"\n+", "\n", t)
        return t.strip()