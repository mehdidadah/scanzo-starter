"""
Document processor service for extracting data from receipts.
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from services.ocr_service import OCRService
from models.receipt import Receipt, TaxLine
from prompts.receipt_prompt import RECEIPT_EXTRACTION_PROMPT
from utils.image_utils import optimize_image

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Main service for processing documents and extracting structured data"""

    def __init__(self):
        self.ocr = OCRService()

    async def process_receipt(
            self,
            content: bytes,
            filename: str
    ) -> Dict[str, Any]:
        """
        Process a receipt image and extract structured data.
        
        Args:
            content: Image bytes
            filename: Original filename
            
        Returns:
            Processed receipt data with validation
        """
        try:
            start_time = datetime.utcnow()

            # Step 1: Optimize image for better OCR and lower costs
            logger.info(f"Processing receipt: {filename}")
            optimized_content = optimize_image(content, max_size=1536)

            # Step 2: Extract data using OCR
            logger.info("Extracting data with OCR...")
            raw_data = await self.ocr.extract(
                image_data=optimized_content,
                prompt=RECEIPT_EXTRACTION_PROMPT,
                temperature=0.0
            )

            # Step 3: Parse and validate data
            logger.info("Parsing extracted data...")
            receipt = self._parse_receipt_data(raw_data)

            # Step 4: Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()

            # Step 5: Prepare response
            response = {
                "success": True,
                "data": receipt.model_dump(
                    exclude={'raw_data', 'validation_errors', 'extracted_at'},
                    exclude_none=True
                ),
                "summary": receipt.to_summary(),
                "validation": {
                    "is_valid": len(receipt.validation_errors) == 0,
                    "errors": receipt.validation_errors,
                    "confidence": receipt.confidence_score
                },
                "metadata": {
                    "filename": filename,
                    "processing_time": round(processing_time, 2),
                    "extracted_at": receipt.extracted_at.isoformat()
                }
            }

            logger.info(
                f"Receipt processed successfully: "
                f"vendor='{receipt.vendor_name}', "
                f"total={receipt.total_amount}, "
                f"confidence={receipt.confidence_score}"
            )

            return response

        except Exception as e:
            logger.error(f"Failed to process receipt: {str(e)}", exc_info=True)
            raise

    def _parse_receipt_data(self, raw_data: Dict) -> Receipt:
        """
        Parse raw OCR data into Receipt model.
        
        Args:
            raw_data: Raw data from OCR
            
        Returns:
            Validated Receipt instance
        """
        # Extract vendor information
        vendor = raw_data.get('vendor', {})

        # Extract transaction information
        transaction = raw_data.get('transaction', {})

        # Extract tax lines
        tax_lines = self._parse_tax_lines(raw_data)

        # Extract totals (support both 'totals' and 'amounts' format)
        totals = raw_data.get('totals', {})
        amounts = raw_data.get('amounts', {})  # Fallback for old format

        subtotal = self._safe_float(totals.get('total_ht') or amounts.get('subtotal'))
        tax_amount = self._safe_float(totals.get('total_tva') or amounts.get('tax_amount'))
        total_amount = self._safe_float(totals.get('total_ttc') or amounts.get('total'))

        # If totals are missing, try to calculate from tax lines
        if not all([subtotal, tax_amount, total_amount]) and tax_lines:
            logger.info("Calculating totals from tax lines...")
            if not subtotal:
                subtotal = sum(line.base_amount for line in tax_lines)
            if not tax_amount:
                tax_amount = sum(line.tax_amount for line in tax_lines)
            if not total_amount:
                total_amount = sum(line.total_amount or 0 for line in tax_lines)

        # Create receipt instance
        receipt = Receipt(
            # Vendor
            vendor_name=vendor.get('name'),
            vendor_address=vendor.get('address'),
            vendor_siret=vendor.get('siret'),

            # Transaction
            receipt_number=transaction.get('receipt_number'),
            date=transaction.get('date'),
            time=transaction.get('time'),

            # Amounts
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,

            # Tax details
            tax_lines=tax_lines,

            # Payment
            payment_method=raw_data.get('payment', {}).get('method'),

            # Metadata
            raw_data=raw_data
        )

        return receipt

    def _parse_tax_lines(self, data: Dict) -> List[TaxLine]:
        """
        Parse tax lines from various possible formats.
        
        Args:
            data: Raw OCR data
            
        Returns:
            List of TaxLine instances
        """
        tax_lines = []

        # Priority 1: New format with tax_lines
        if 'tax_lines' in data and data['tax_lines']:
            for line in data['tax_lines']:
                if line and self._is_valid_tax_line(line):
                    tax_lines.append(TaxLine(
                        label=line.get('label'),
                        rate=self._safe_float(line.get('rate')) or 0,
                        base_amount=self._safe_float(line.get('base_ht')) or 0,
                        tax_amount=self._safe_float(line.get('tva')) or 0,
                        total_amount=self._safe_float(line.get('ttc'))
                    ))

        # Priority 2: Legacy format with tax_breakdown
        elif 'tax_breakdown' in data and data['tax_breakdown']:
            for tax in data['tax_breakdown']:
                if tax and self._is_valid_tax_line(tax):
                    tax_lines.append(TaxLine(
                        label=tax.get('label'),
                        rate=self._safe_float(tax.get('rate')) or 0,
                        base_amount=self._safe_float(tax.get('base')) or 0,
                        tax_amount=self._safe_float(tax.get('amount')) or 0,
                        total_amount=self._safe_float(tax.get('total'))
                    ))

        # Priority 3: Single tax from tax_information
        elif 'tax_information' in data:
            tax_info = data['tax_information']
            rate = self._safe_float(tax_info.get('rate'))
            base = self._safe_float(tax_info.get('base_ht'))
            amount = self._safe_float(tax_info.get('tax_amount'))

            if rate and (base or amount):
                tax_lines.append(TaxLine(
                    rate=rate,
                    base_amount=base or 0,
                    tax_amount=amount or 0,
                    total_amount=self._safe_float(tax_info.get('total_ttc'))
                ))

        if tax_lines:
            logger.info(f"Parsed {len(tax_lines)} tax lines")
            for i, line in enumerate(tax_lines, 1):
                logger.debug(
                    f"  Line {i}: rate={line.rate}%, "
                    f"base={line.base_amount}, tax={line.tax_amount}"
                )

        return tax_lines

    def _is_valid_tax_line(self, line: Dict) -> bool:
        """Check if a tax line contains valid data"""
        if not line:
            return False

        # Must have at least a rate or some amounts
        has_rate = self._safe_float(line.get('rate')) is not None
        has_base = self._safe_float(line.get('base_ht') or line.get('base')) is not None
        has_tax = self._safe_float(line.get('tva') or line.get('amount')) is not None

        return has_rate or has_base or has_tax

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None or value == "null" or value == "NULL":
            return None

        try:
            # Handle French format with comma
            if isinstance(value, str):
                value = value.replace(',', '.')
            return float(value)
        except (ValueError, TypeError):
            return None