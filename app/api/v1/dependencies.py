from typing import Generator
from app.config import settings

# Shared dependencies for API v1

def get_settings() -> Generator:
    yield settings
