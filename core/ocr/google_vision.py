from google.cloud import vision
from .base import OCRService

class GoogleVisionOCR:
    def __init__(self, language_hints=("fr",)):
        self.client = vision.ImageAnnotatorClient()
        self.language_hints = list(language_hints)

    def extract_text(self, image_bytes: bytes) -> str:
        image = vision.Image(content=image_bytes)
        ctx = vision.ImageContext(language_hints=self.language_hints)
        resp = self.client.text_detection(image=image, image_context=ctx)
        if resp.error.message:
            raise RuntimeError(resp.error.message)
        return (resp.full_text_annotation.text or "").strip()