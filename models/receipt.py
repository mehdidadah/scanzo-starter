"""
Receipt model with essential fields for tax and amount extraction.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PaymentMethod(str, Enum):
    """Payment methods commonly found on receipts"""
    CASH = "cash"
    CARD = "card"
    CHECK = "check"
    MOBILE = "mobile"
    OTHER = "other"


class TaxLine(BaseModel):
    """Individual tax line from receipt"""
    label: Optional[str] = Field(None, description="Line identifier (A, B, C, *)")
    rate: float = Field(ge=0, le=100, description="Tax rate percentage")
    base_amount: float = Field(ge=0, description="Amount HT (before tax)")
    tax_amount: float = Field(ge=0, description="Tax amount (TVA)")
    total_amount: Optional[float] = Field(None, ge=0, description="Amount TTC (with tax)")

    @model_validator(mode='after')
    def validate_amounts(self):
        """Ensure amounts are coherent"""
        if self.total_amount is None:
            self.total_amount = round(self.base_amount + self.tax_amount, 2)
        return self

    def is_coherent(self, tolerance: float = 0.02) -> bool:
        """Check if tax calculation is correct"""
        expected_tax = round(self.base_amount * self.rate / 100, 2)
        expected_total = round(self.base_amount + self.tax_amount, 2)

        tax_valid = abs(expected_tax - self.tax_amount) <= tolerance
        total_valid = abs(expected_total - self.total_amount) <= tolerance

        return tax_valid and total_valid


class Receipt(BaseModel):
    """Receipt document model - focused on essential financial data"""

    # === Vendor Information ===
    vendor_name: Optional[str] = Field(None, description="Merchant/Store name")
    vendor_address: Optional[str] = Field(None, description="Store address")
    vendor_siret: Optional[str] = Field(None, description="SIRET/Tax ID")

    # === Transaction Info ===
    receipt_number: Optional[str] = Field(None, description="Receipt/Transaction number")
    date: Optional[str] = Field(None, description="Transaction date YYYY-MM-DD")
    time: Optional[str] = Field(None, description="Transaction time HH:MM")

    # === Financial Summary (Most Important) ===
    subtotal: Optional[float] = Field(None, ge=0, description="Total HT (before tax)")
    tax_amount: Optional[float] = Field(None, ge=0, description="Total TVA (tax)")
    total_amount: Optional[float] = Field(None, ge=0, description="Total TTC (with tax)")

    # === Tax Details ===
    tax_lines: List[TaxLine] = Field(
        default_factory=list,
        description="Detailed tax breakdown by rate"
    )

    # === Payment ===
    payment_method: Optional[PaymentMethod] = None

    # === Metadata ===
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float = Field(default=0.0, ge=0, le=1)
    validation_errors: List[str] = Field(default_factory=list)

    # Raw OCR data for debugging (excluded from API response)
    raw_data: Optional[Dict[str, Any]] = Field(None, exclude=True)

    @field_validator('date', mode='before')
    @classmethod
    def normalize_date(cls, v):
        """Convert date to ISO format YYYY-MM-DD"""
        if not v or not isinstance(v, str):
            return v

        # Handle DD/MM/YYYY or DD-MM-YYYY format
        for separator in ['/', '-']:
            if separator in v:
                parts = v.split(separator)
                if len(parts) == 3:
                    day, month, year = parts
                    # If year is first, already in good format
                    if len(parts[0]) == 4:
                        return v
                    # Convert to ISO format
                    if len(year) == 4:
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return v

    @field_validator('payment_method', mode='before')
    @classmethod
    def normalize_payment(cls, v):
        """Normalize payment method string"""
        if not v:
            return None

        v = str(v).lower().strip()

        # Map common variations
        payment_map = {
            'cb': PaymentMethod.CARD,
            'carte': PaymentMethod.CARD,
            'card': PaymentMethod.CARD,
            'credit': PaymentMethod.CARD,
            'debit': PaymentMethod.CARD,
            'especes': PaymentMethod.CASH,
            'espèces': PaymentMethod.CASH,
            'cash': PaymentMethod.CASH,
            'cheque': PaymentMethod.CHECK,
            'chèque': PaymentMethod.CHECK,
            'check': PaymentMethod.CHECK,
            'mobile': PaymentMethod.MOBILE,
            'apple pay': PaymentMethod.MOBILE,
            'google pay': PaymentMethod.MOBILE,
        }

        for key, value in payment_map.items():
            if key in v:
                return value

        return PaymentMethod.OTHER

    @model_validator(mode='after')
    def validate_receipt(self):
        """Validate receipt data coherence"""
        errors = []

        # Check if we have minimum required data
        if not self.vendor_name:
            errors.append("Missing vendor name")

        if not self.total_amount:
            errors.append("Missing total amount")

        # Validate financial coherence
        if all([self.subtotal, self.tax_amount, self.total_amount]):
            calculated = round(self.subtotal + self.tax_amount, 2)
            if abs(calculated - self.total_amount) > 0.10:
                errors.append(
                    f"Amount mismatch: {self.subtotal} + {self.tax_amount} = "
                    f"{calculated} ≠ {self.total_amount}"
                )

        # Validate tax lines coherence
        if self.tax_lines:
            # Sum of tax lines should match totals
            sum_base = sum(line.base_amount for line in self.tax_lines)
            sum_tax = sum(line.tax_amount for line in self.tax_lines)

            if self.subtotal and abs(sum_base - self.subtotal) > 0.50:
                errors.append(
                    f"Tax lines base sum ({sum_base}) doesn't match subtotal ({self.subtotal})"
                )

            if self.tax_amount and abs(sum_tax - self.tax_amount) > 0.50:
                errors.append(
                    f"Tax lines tax sum ({sum_tax}) doesn't match tax amount ({self.tax_amount})"
                )

            # If totals are missing, calculate from tax lines
            if not self.subtotal:
                self.subtotal = sum_base
            if not self.tax_amount:
                self.tax_amount = sum_tax
            if not self.total_amount:
                self.total_amount = round(self.subtotal + self.tax_amount, 2)

        # Calculate confidence score
        self.confidence_score = self._calculate_confidence()

        # Store validation errors
        self.validation_errors = errors

        return self

    def _calculate_confidence(self) -> float:
        """Calculate extraction confidence based on data completeness"""
        score = 0.0
        weights = {
            'has_vendor': 0.20,
            'has_date': 0.15,
            'has_totals': 0.30,
            'has_tax_details': 0.25,
            'amounts_coherent': 0.10
        }

        if self.vendor_name:
            score += weights['has_vendor']

        if self.date:
            score += weights['has_date']

        if all([self.subtotal, self.tax_amount, self.total_amount]):
            score += weights['has_totals']

        if self.tax_lines:
            score += weights['has_tax_details']

        if not self.validation_errors:
            score += weights['amounts_coherent']

        return round(score, 2)

    def to_summary(self) -> Dict[str, Any]:
        """Return a summary of key information"""
        return {
            'vendor': self.vendor_name,
            'date': self.date,
            'total_ht': self.subtotal,
            'total_tva': self.tax_amount,
            'total_ttc': self.total_amount,
            'tax_rates': list(set(line.rate for line in self.tax_lines)) if self.tax_lines else [],
            'payment': self.payment_method.value if self.payment_method else None,
            'is_valid': len(self.validation_errors) == 0
        }