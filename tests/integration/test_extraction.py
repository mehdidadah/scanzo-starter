import os

from core.extraction_service import ExtractionService

BASE = os.path.dirname(__file__)
SAMPLES = os.path.join(BASE, "samples")

def load(name: str) -> str:
    with open(os.path.join(SAMPLES, name), encoding="utf-8") as f:
        return f.read()

def test_paradis_du_fruit():
    svc = ExtractionService()
    r = svc.extract(load("paradis_du_fruit.txt")).document
    print(f"result paradis {r}")
    assert r is not None
    assert "PARADIS" in r.vendor.upper()
    assert abs(r.total_ttc - 79.90) <= 0.1
    assert abs(r.total_ht - 72.64) <= 0.1
    assert abs(r.tva_amount - 7.26) <= 0.1
    assert len(r.tva_details) >= 2
    assert r.coherent is True
    assert r.confidence is not None and r.confidence > 0.75

    # Tests spécifiques pour les taux de TVA
    assert all(tax_line.rate == 10.0 for tax_line in r.tva_details), \
        f"Tous les taux de TVA devraient être 10.0%, trouvés: {[tl.rate for tl in r.tva_details]}"

    # Validation des montants HT de chaque ligne TVA
    expected_ht_amounts = [50.55, 22.09]
    actual_ht_amounts = [tl.base_ht for tl in r.tva_details]
    for expected, actual in zip(expected_ht_amounts, actual_ht_amounts):
        assert abs(actual - expected) <= 0.01, \
            f"Montant HT attendu: {expected}, trouvé: {actual}"

def test_sushi_charles():
    svc = ExtractionService()
    r = svc.extract(load("sushi_charles.txt")).document
    print(f"result sushi charles {r}")
    assert r is not None
    assert "SUSHI CHARLES" in r.vendor.upper()
    assert abs(r.total_ttc - 26.80) <= 0.1
    assert abs(r.total_ht - 24.36) <= 0.1
    assert abs(r.tva_amount - 2.44) <= 0.1
    assert r.coherent is True

    # Tests spécifiques pour les taux de TVA
    assert len(r.tva_details) == 1, f"Une seule ligne TVA attendue, trouvées: {len(r.tva_details)}"
    assert r.tva_details[0].rate == 10.0, f"Taux TVA attendu: 10.0%, trouvé: {r.tva_details[0].rate}%"
    assert abs(r.tva_details[0].base_ht - 24.36) <= 0.01
    assert abs(r.tva_details[0].tva - 2.44) <= 0.01
    assert abs(r.tva_details[0].ttc - 26.80) <= 0.01

def test_storia():
    svc = ExtractionService()
    r = svc.extract(load("storia.txt")).document
    print(f"result storia {r}")
    assert r is not None
    assert r.total_ttc == 33.00
    assert r.total_ht == 30.00
    assert r.tva_amount == 3.00
    assert r.coherent is True

    # Tests spécifiques pour les taux de TVA
    assert len(r.tva_details) == 1, f"Une seule ligne TVA attendue, trouvées: {len(r.tva_details)}"
    assert r.tva_details[0].rate == 10.0, f"Taux TVA attendu: 10.0%, trouvé: {r.tva_details[0].rate}%"
    assert r.tva_details[0].base_ht == 30.00
    assert r.tva_details[0].tva == 3.00
    assert r.tva_details[0].ttc == 33.00

def test_namaste():
    svc = ExtractionService()
    r = svc.extract(load("namaste_indien.txt")).document
    print(f"result namaste {r}")
    assert r is not None
    assert r.total_ttc == 76.50
    assert r.total_ht == 69.55
    assert r.tva_amount == 6.95
    assert r.coherent is True

    # Tests spécifiques pour les taux de TVA
    assert len(r.tva_details) == 1, f"Une seule ligne TVA attendue, trouvées: {len(r.tva_details)}"
    assert r.tva_details[0].rate == 10.0, f"Taux TVA attendu: 10.0%, trouvé: {r.tva_details[0].rate}%"
    assert abs(r.tva_details[0].base_ht - 69.55) <= 0.01
    assert abs(r.tva_details[0].tva - 6.95) <= 0.01
    assert abs(r.tva_details[0].ttc - 76.50) <= 0.01

def test_paris_istanbul():
    svc = ExtractionService()
    r = svc.extract(load("paris_istanbul.txt")).document
    print(f"result paris istanbul {r}")
    assert r is not None
    assert r.total_ttc == 13.00
    assert r.total_ht == 11.82
    assert r.tva_amount == 1.18
    assert r.coherent is True

    # Tests spécifiques pour les taux de TVA
    assert len(r.tva_details) == 1, f"Une seule ligne TVA attendue, trouvées: {len(r.tva_details)}"
    assert r.tva_details[0].rate == 10.0, f"Taux TVA attendu: 10.0%, trouvé: {r.tva_details[0].rate}%"
    assert abs(r.tva_details[0].base_ht - 11.82) <= 0.01
    assert abs(r.tva_details[0].tva - 1.18) <= 0.01
    assert abs(r.tva_details[0].ttc - 13.00) <= 0.01
