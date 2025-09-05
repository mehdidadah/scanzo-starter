import pytest
from unittest.mock import AsyncMock, patch
from PIL import Image
import io

from services.document_processor import DocumentProcessor


class TestIntegration:

    def create_valid_image_bytes(self):
        """Helper to create a valid JPEG image"""
        img = Image.new('RGB', (200, 200), color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        return buffer.read()

    @pytest.mark.asyncio
    async def test_full_receipt_processing_flow(self, sample_receipt_data):
        processor = DocumentProcessor()
        # Create a real valid image
        valid_image = self.create_valid_image_bytes()

        # Mock only the external service (OpenAI)
        with patch.object(processor.ocr, 'extract', new=AsyncMock(return_value=sample_receipt_data)):
            # Process the receipt with a real image - no need to mock optimize_image
            result = await processor.process_receipt(
                content=valid_image,
                filename="integration_test.jpg"
            )

            # Full verifications
            assert result['success'] is True

            # Extracted data
            data = result['data']
            assert data['vendor_name'] == "Le Petit Café"
            assert data['vendor_siret'] == "123 456 789 00012"
            assert data['date'] == "2024-03-15"
            assert data['subtotal'] == 72.64
            assert data['tax_amount'] == 7.26
            assert data['total_amount'] == 79.90

            # Tax lines
            assert len(data['tax_lines']) == 2
            tax_line_1 = data['tax_lines'][0]
            assert tax_line_1['rate'] == 10.0
            assert tax_line_1['base_amount'] == 50.55

            # Summary
            summary = result['summary']
            assert summary['vendor'] == "Le Petit Café"
            assert summary['total_ttc'] == 79.90
            assert summary['is_valid'] is True

            # Validation
            validation = result['validation']
            assert validation['is_valid'] is True
            assert validation['confidence'] > 0.8
            assert len(validation['errors']) == 0

            # Metadata
            metadata = result['metadata']
            assert metadata['filename'] == "integration_test.jpg"
            assert 'processing_time' in metadata
            assert 'extracted_at' in metadata