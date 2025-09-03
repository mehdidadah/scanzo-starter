from openai import AsyncOpenAI
import base64
from typing import Dict, Any, Optional
import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

class OCRService:
    """Service OCR optimisé pour performance"""
    
    def __init__(self):
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set. OCRService will fail on extract calls.")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else AsyncOpenAI()
        self.model = settings.openai_model
    
    @retry(
        stop=stop_after_attempt(2),  # Réduit à 2 essais
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    async def extract(
        self, 
        image_data: bytes, 
        prompt: str,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Extraction OCR optimisée - UN SEUL PASS
        """
        try:
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # System prompt insistant sur l'extraction COMPLÈTE
            system_prompt = """You are a PRECISE document scanner.
            CRITICAL: Extract EVERY line from tax tables - do not skip or merge lines!
            If you see 2 tax lines, return 2 entries. If you see 3, return 3.
            Look especially at the BOTTOM of receipts for tax breakdown tables.
            Example tax table:
            B TVA 10.00    50.55    5.05    55.60
            C TVA 10.00    22.09    2.21    24.30
            This has TWO lines that must BOTH be extracted."""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=3000  # Suffisant pour extraction complète
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Logging amélioré
            logger.info(f"OCR Extract - Vendor: {result.get('vendor', {}).get('name')}")
            tax_breakdown = result.get('tax_breakdown', [])
            tax_lines = result.get('tax_lines', [])
            lines_count = len(tax_lines) if tax_lines else len(tax_breakdown)
            logger.info(f"Tax lines found: {lines_count}")
            if tax_lines:
                for i, line in enumerate(tax_lines):
                    logger.info(f"  Line {i+1}: {line.get('label', 'N/A')} - "
                              f"Rate: {line.get('rate')}%, "
                              f"Base HT: {line.get('base_ht')}, "
                              f"TVA: {line.get('tva')}, TTC: {line.get('ttc')}")
            else:
                for i, tax in enumerate(tax_breakdown):
                    logger.info(f"  Line {i+1}: {tax.get('label', 'N/A')} - "
                              f"Rate: {tax.get('rate')}%, "
                              f"Base: {tax.get('base')}, "
                              f"Tax: {tax.get('amount')}")
            
            return result
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            raise
    
    async def detect_document_type(self, image_data: bytes) -> str:
        """Détection rapide du type"""
        prompt = 'Is this a "receipt" or "invoice"? Answer with one word only.'
        
        try:
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "low"  # Low detail pour rapidité
                            }
                        }
                    ]
                }],
                max_tokens=10,
                temperature=0
            )
            
            result = response.choices[0].message.content.lower().strip()
            return "invoice" if "invoice" in result else "receipt"
            
        except:
            return "receipt"
