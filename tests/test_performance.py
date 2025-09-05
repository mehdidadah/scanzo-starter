import pytest
from unittest.mock import AsyncMock, patch
from PIL import Image
import io
import asyncio

from services.document_processor import DocumentProcessor
from models.receipt import Receipt, TaxLine


class TestPerformance:

    def create_valid_image_bytes(self):
        """Helper to create a valid JPEG image"""
        img = Image.new('RGB', (100, 100), color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        return buffer.read()

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, sample_receipt_data):
        processor = DocumentProcessor()
        # Create a real valid image
        valid_image = self.create_valid_image_bytes()

        with patch.object(processor.ocr, 'extract', new=AsyncMock(return_value=sample_receipt_data)):
            # Process 5 receipts in parallel with real images
            tasks = [
                processor.process_receipt(valid_image, f"receipt_{i}.jpg")
                for i in range(5)
            ]

            results = await asyncio.gather(*tasks)

            # Verify that all succeeded
            for result in results:
                assert result['success'] is True

    def test_large_tax_lines_handling(self):
        tax_lines = [
            TaxLine(
                label=f"Line{i}",
                rate=10 + (i % 3) * 5,
                base_amount=100 + i,
                tax_amount=10 + i * 0.1
            )
            for i in range(50)
        ]
        receipt = Receipt(
            vendor_name="Big Store",
            tax_lines=tax_lines
        )
        assert receipt.subtotal > 0
        assert receipt.tax_amount > 0
        assert len(receipt.tax_lines) == 50