"""
Document scanning endpoints for the Scanzo API.
"""

from typing import Dict, Any, Optional, Coroutine
import logging
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.responses import JSONResponse

from services.document_processor import DocumentProcessor
from app.config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/scan", tags=["Document Scanning"])

# Initialize document processor (singleton)
processor = DocumentProcessor()


# === Response Models === 
class ScanResponse:
    """Standard response structure for scan endpoints"""

    @staticmethod
    def success(data: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict:
        return {
            "success": True,
            "data": data,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    def error(message: str, details: Any = None) -> Dict:
        return {
            "success": False,
            "error": message,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }


# === Validation Helpers ===
async def validate_file(file: UploadFile) -> bytes:
    """
    Validate uploaded file and return its content.
    
    Args:
        file: Uploaded file
        
    Returns:
        File content as bytes
        
    Raises:
        HTTPException: If file is invalid
    """
    # Check content type
    if file.content_type not in settings.allowed_file_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{file.content_type}' not supported. "
                   f"Allowed types: {', '.join(settings.allowed_file_types)}"
        )

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb:.1f}MB"
        )

    # Check if file is not empty
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded"
        )

    return content


# === Main Endpoints ===
@router.post(
    "/receipt",
    response_model=Dict[str, Any],
    summary="Scan a receipt",
    description="Extract structured data from a receipt image"
)
async def scan_receipt(
        file: UploadFile = File(..., description="Receipt image (JPEG, PNG)")
) -> dict[str, Any] | JSONResponse:
    """
    Scan a receipt and extract structured data.
    
    This endpoint is optimized for receipts with focus on:
    - Vendor information
    - Transaction details  
    - Financial totals (HT, TVA, TTC)
    - Tax breakdown by rate
    - Payment method
    
    Returns:
        JSON with extracted data, validation status, and confidence score
    """
    try:
        # Validate file
        content = await validate_file(file)

        logger.info(f"Processing receipt: {file.filename} ({len(content)} bytes)")

        # Process receipt
        result = await processor.process_receipt(
            content=content,
            filename=file.filename
        )

        # Add file metadata
        result["metadata"]["file_info"] = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(content)
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process receipt: {str(e)}", exc_info=True)

        # Return clean error response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ScanResponse.error(
                message="Failed to process receipt",
                details=str(e) if settings.debug else None
            )
        )


@router.post(
    "/",
    response_model=Dict[str, Any],
    summary="Scan a document (auto-detect type)",
    description="Automatically detect document type and extract data"
)
async def scan_document(
        file: UploadFile = File(..., description="Document image"),
        force_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scan any supported document with automatic type detection.
    
    Currently supports:
    - Receipts
    
    Future support:
    - Invoices
    - Tickets
    - Statements
    
    Args:
        file: Document image
        force_type: Force specific document type (optional)
        
    Returns:
        Extracted data based on detected document type
    """
    # For now, forward to receipt endpoint
    # In the future, this will detect and route to appropriate processor
    return await scan_receipt(file)


@router.post(
    "/batch",
    response_model=Dict[str, Any],
    summary="Scan multiple documents",
    description="Process multiple documents in one request (Coming Soon)"
)
async def scan_batch(
        files: list[UploadFile] = File(..., description="Multiple document images")
) -> Dict[str, Any]:
    """
    Batch processing endpoint for multiple documents.
    
    Note: This endpoint is planned for future implementation.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Batch processing not yet implemented. Please use single document endpoints."
    )


# === Utility Endpoints ===
@router.get(
    "/supported-types",
    response_model=Dict[str, Any],
    summary="Get supported file types",
    description="List all supported file types and size limits"
)
async def get_supported_types() -> Dict[str, Any]:
    """Get information about supported file types and limits"""
    return {
        "supported_types": settings.allowed_file_types,
        "max_file_size_mb": settings.max_file_size_mb,
        "document_types": ["receipt"],  # Add more as implemented
        "future_support": ["invoice", "ticket", "statement"]
    }