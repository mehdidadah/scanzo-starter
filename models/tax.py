from pydantic import BaseModel, Field, computed_field
from typing import Optional, List
from enum import Enum

class TaxRateType(str, Enum):
    """Types de taux de TVA standards"""
    SUPER_REDUCED = "super_reduced"  # 2.1%
    REDUCED = "reduced"              # 5.5%
    INTERMEDIATE = "intermediate"    # 10%
    STANDARD = "standard"            # 20%
    CUSTOM = "custom"                # Autres

class TaxLine(BaseModel):
    """
    Représente une ligne de taxe unique.
    Peut y avoir plusieurs lignes avec le même taux.
    """
    label: Optional[str] = Field(None, description="Identifiant de ligne (A, B, C, *)")
    rate: float = Field(..., ge=0, le=100, description="Taux en pourcentage")
    base_amount: float = Field(..., description="Montant HT/base")
    tax_amount: float = Field(..., description="Montant de taxe")
    total_with_tax: Optional[float] = Field(None, description="Montant TTC")
    
    @computed_field
    @property
    def calculated_total(self) -> float:
        """Calcule le total si non fourni"""
        if self.total_with_tax is not None:
            return self.total_with_tax
        return round(self.base_amount + self.tax_amount, 2)
    
    @computed_field
    @property
    def rate_type(self) -> TaxRateType:
        """Détermine le type de taux"""
        if 2 <= self.rate <= 2.5:
            return TaxRateType.SUPER_REDUCED
        elif 5 <= self.rate <= 6:
            return TaxRateType.REDUCED
        elif 9 <= self.rate <= 11:
            return TaxRateType.INTERMEDIATE
        elif 19 <= self.rate <= 21:
            return TaxRateType.STANDARD
        return TaxRateType.CUSTOM
    
    def is_valid(self) -> bool:
        """Vérifie la cohérence de la ligne"""
        calculated = round(self.base_amount + self.tax_amount, 2)
        if self.total_with_tax:
            return abs(calculated - self.total_with_tax) <= 0.02
        return True

class TaxSummary(BaseModel):
    """Résumé des taxes"""
    lines: List[TaxLine] = Field(default_factory=list)
    total_ht: Optional[float] = None
    total_tax: Optional[float] = None
    total_ttc: Optional[float] = None
    
    def calculate_totals(self):
        """Calcule les totaux depuis les lignes"""
        if self.lines:
            self.total_ht = sum(line.base_amount for line in self.lines)
            self.total_tax = sum(line.tax_amount for line in self.lines)
            self.total_ttc = sum(line.calculated_total for line in self.lines)
    
    def validate_coherence(self) -> bool:
        """Vérifie la cohérence des totaux"""
        if self.total_ht and self.total_tax and self.total_ttc:
            calculated = round(self.total_ht + self.total_tax, 2)
            return abs(calculated - self.total_ttc) <= 0.02
        return True
