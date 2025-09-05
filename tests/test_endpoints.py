import pytest
from unittest.mock import AsyncMock, patch
from io import BytesIO


class TestScanEndpoints:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "up"

    def test_supported_types(self, client):
        response = client.get("/api/v1/scan/supported-types")
        assert response.status_code == 200
        data = response.json()
        assert "image/jpeg" in data["supported_types"]
        assert "receipt" in data["document_types"]

    @pytest.mark.asyncio
    async def test_scan_receipt_success(self, client, sample_receipt_data, sample_image_bytes):
        with patch('app.api.v1.endpoints.scan.processor.process_receipt', new=AsyncMock(return_value={
            "success": True,
            "data": {"vendor_name": "Test"},
            "metadata": {"processing_time": 2.5}
        })):
            files = {"file": ("receipt.jpg", BytesIO(sample_image_bytes), "image/jpeg")}
            response = client.post("/api/v1/scan/receipt", files=files)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_scan_receipt_invalid_file_type(self, client):
        files = {"file": ("document.pdf", BytesIO(b"fake pdf"), "application/pdf")}
        response = client.post("/api/v1/scan/receipt", files=files)
        assert response.status_code == 415
        assert "not supported" in response.json()["detail"].lower()

    def test_scan_receipt_file_too_large(self, client):
        from fastapi import HTTPException
        large_content = b"x" * (11 * 1024 * 1024)
        with patch('app.api.v1.endpoints.scan.validate_file', side_effect=HTTPException(
            status_code=413,
            detail="File too large"
        )):
            files = {"file": ("large.jpg", BytesIO(large_content), "image/jpeg")}
            response = client.post("/api/v1/scan/receipt", files=files)
            assert response.status_code == 413

    def test_scan_receipt_empty_file(self, client):
        files = {"file": ("empty.jpg", BytesIO(b""), "image/jpeg")}
        response = client.post("/api/v1/scan/receipt", files=files)
        assert response.status_code == 400
        assert "empty file" in response.json()["detail"].lower()

    def test_batch_endpoint_not_implemented(self, client):
        files = [
            ("files", ("receipt1.jpg", BytesIO(b"fake"), "image/jpeg")),
            ("files", ("receipt2.jpg", BytesIO(b"fake"), "image/jpeg"))
        ]
        response = client.post("/api/v1/scan/batch", files=files)
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"].lower()
