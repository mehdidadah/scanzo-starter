from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .receipt import Receipt

@dataclass
class ExtractionResult:
    document: Optional[Receipt] = None
    error: Optional[str] = None