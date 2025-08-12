from typing import Protocol

class OCRService(Protocol):
    def extract_text(self, image_bytes: bytes) -> str:  # pragma: no cover
        ...