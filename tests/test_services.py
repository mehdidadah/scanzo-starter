import pytest
from unittest.mock import Mock, AsyncMock, patch
import json
from PIL import Image
import io

from services.document_processor import DocumentProcessor
from services.ocr_service import OCRService


class TestOCRService:
    @pytest.mark.asyncio
    async def test_extract_success(self, sample_receipt_data):
        service = OCRService()
        with patch.object(service, 'client') as mock_client:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock(content=json.dumps(sample_receipt_data))
            mock_client.chat = Mock()
            mock_client.chat.completions = Mock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            result = await service.extract(
                image_data=b"fake_image_data",
                prompt="Extract receipt"
            )
            assert result == sample_receipt_data
            mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_retry_on_failure(self):
        service = OCRService()
        with patch.object(service, 'client') as mock_client:
            mock_client.chat = Mock()
            mock_client.chat.completions = Mock()
            mock_client.chat.completions.create = AsyncMock(side_effect=[
                Exception("API Error 1"),
                Exception("API Error 2"),
            ])
            with pytest.raises(Exception):
                await service.extract(b"fake_image", "prompt")

    @pytest.mark.asyncio
    async def test_detect_document_type(self):
        service = OCRService()
        with patch.object(service, 'client') as mock_client:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="receipt"))]
            mock_client.chat = Mock()
            mock_client.chat.completions = Mock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            doc_type = await service.detect_document_type(b"fake_image")
            assert doc_type == "receipt"


class TestDocumentProcessor:

    def create_valid_image_bytes(self):
        """Helper to create a valid JPEG image"""
        img = Image.new('RGB', (100, 100), color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        return buffer.read()

    @pytest.mark.asyncio
    async def test_process_receipt_success(self, sample_receipt_data):
        processor = DocumentProcessor()
        # Create a real valid image
        valid_image = self.create_valid_image_bytes()

        with patch.object(processor.ocr, 'extract', new=AsyncMock(return_value=sample_receipt_data)):
            # No need to mock optimize_image if we use a real image
            result = await processor.process_receipt(
                content=valid_image,
                filename="test_receipt.jpg"
            )

            assert result['success'] is True
            assert result['data']['vendor_name'] == "Le Petit Café"
            assert result['data']['total_amount'] == 79.90
            assert len(result['data']['tax_lines']) == 2
            assert result['validation']['is_valid'] is True

    @pytest.mark.asyncio
    async def test_process_receipt_with_validation_errors(self):
        processor = DocumentProcessor()
        # Create a real valid image
        valid_image = self.create_valid_image_bytes()

        bad_data = {
            "vendor": {"name": "Test"},
            "totals": {
                "total_ht": 100,
                "total_tva": 10,
                "total_ttc": 120
            }
        }

        with patch.object(processor.ocr, 'extract', new=AsyncMock(return_value=bad_data)):
            result = await processor.process_receipt(
                content=valid_image,
                filename="test.jpg"
            )

            assert result['success'] is True
            assert result['validation']['is_valid'] is False
            assert len(result['validation']['errors']) > 0

    def test_parse_tax_lines_new_format(self):
        processor = DocumentProcessor()
        data = {
            "tax_lines": [
                {"label": "A", "rate": 10, "base_ht": 100, "tva": 10, "ttc": 110},
                {"label": "B", "rate": 20, "base_ht": 50, "tva": 10, "ttc": 60}
            ]
        }
        tax_lines = processor._parse_tax_lines(data)
        assert len(tax_lines) == 2
        assert tax_lines[0].label == "A"
        assert tax_lines[0].rate == 10
        assert tax_lines[1].label == "B"
        assert tax_lines[1].rate == 20

    def test_parse_tax_lines_legacy_format(self):
        processor = DocumentProcessor()
        data = {
            "tax_breakdown": [
                {"label": "TVA 10%", "rate": 10, "base": 100, "amount": 10, "total": 110}
            ]
        }
        tax_lines = processor._parse_tax_lines(data)
        assert len(tax_lines) == 1
        assert tax_lines[0].rate == 10
        assert tax_lines[0].base_amount == 100

    def test_safe_float_conversion(self):
        processor = DocumentProcessor()
        assert processor._safe_float(10) == 10.0
        assert processor._safe_float("10") == 10.0
        assert processor._safe_float("10,5") == 10.5
        assert processor._safe_float("10.5") == 10.5
        assert processor._safe_float(None) is None
        assert processor._safe_float("null") is None
        assert processor._safe_float("invalid") is None