import sys
from pathlib import Path

# Add the parent directory to a Python path to allow imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from fastapi import UploadFile
from PIL import Image
import io

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def sample_receipt_data():
    """Sample receipt data for tests"""
    return {
        "vendor": {
            "name": "Le Petit Café",
            "address": "123 Rue de la Paix, Paris",
            "siret": "123 456 789 00012"
        },
        "transaction": {
            "date": "2024-03-15",
            "time": "14:30",
            "receipt_number": "A2024-001234"
        },
        "tax_lines": [
            {
                "label": "B",
                "rate": 10.0,
                "base_ht": 50.55,
                "tva": 5.05,
                "ttc": 55.60
            },
            {
                "label": "C",
                "rate": 10.0,
                "base_ht": 22.09,
                "tva": 2.21,
                "ttc": 24.30
            }
        ],
        "totals": {
            "total_ht": 72.64,
            "total_tva": 7.26,
            "total_ttc": 79.90
        },
        "payment": {
            "method": "CARD"
        }
    }


@pytest.fixture
def sample_image_bytes():
    """Create a real valid JPEG image for tests"""
    # Create a real image with PIL
    img = Image.new('RGB', (100, 100), color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def mock_upload_file(sample_image_bytes):
    """Mock of an uploaded file"""
    file = Mock(spec=UploadFile)
    file.filename = "receipt.jpg"
    file.content_type = "image/jpeg"

    async def read():
        return sample_image_bytes

    file.read = read
    return file


# Configuration of environment variables for tests
@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Configure environment for tests"""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-testing")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    yield
    # Cleanup after the test if necessary