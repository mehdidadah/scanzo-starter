from fastapi import APIRouter, UploadFile, File, HTTPException
from ....core.ocr.google_vision import GoogleVisionOCR
from ....core.services.extraction_service import ExtractionService
from ....core.models.extraction_result import ExtractionStatus

router = APIRouter()
ocr = GoogleVisionOCR()
service = ExtractionService()

@router.post("/scan")
async def scan(file: UploadFile = File(...)):
    if not (file.content_type or "").startswith("image/") and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Image or PDF required")
    content = await file.read()
    ocr_text = ocr.extract_text(content)
    result = service.extract(ocr_text)
    if result.status == ExtractionStatus.FAILED:
        raise HTTPException(422, {"errors": result.errors, "warnings": result.warnings})
    return result.document
