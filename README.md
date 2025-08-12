# Scanzo Starter (FastAPI + Google Vision + Regex)

Starter propre et modulaire pour un SaaS qui scanne des **receipts** (tickets) et extrait **HT / TVA / TTC**, sans YAML, avec **regex en Python**, règles métier et **confiance** par champ.

## ✨ Features
- FastAPI `POST /api/scan` (JPEG/PDF) → JSON `Receipt`
- OCR : **Google Vision** (hints FR)
- Parsing : **regex structurées** (Python), priorités intégrées
- Multi-TVA (somme des bases), fallback **HT = TTC - TVA**
- Confiance par champ + score global
- Tests d’intégration avec vrais OCR textes

## 🧱 Structure
```
scanzo-starter/
├─ app/api/...
├─ core/
│  ├─ ocr/
│  ├─ text/
│  ├─ parsing/ (regex_registry + extractors)
│  ├─ services/ (ExtractionService)
│  ├─ validators/
│  ├─ models/ (Receipt, TaxLine, ExtractionResult, Confidence)
│  └─ utils/
└─ tests/integration/ (samples OCR .txt)
```

## 🚀 Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Optionnel : Configurer GOOGLE_APPLICATION_CREDENTIALS pour Vision
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
uvicorn app.api.main:app --reload
```

## 🔎 Tests
```bash
pytest -q
```

## 📦 Endpoint
`POST /api/scan` — body: `multipart/form-data` avec `file` (image/pdf).
Réponse: `Receipt` JSON avec `tva_details[]`, `confidence`, `coherent`.

## 🧠 Confiance
- Source du champ (table TVA, totals line, fallback…)
- Bonus si `TTC ≈ HT + TVA`
- Score global pondéré

## 🧩 Personnalisation
- Ajoute des règles dans `core/parsing/regex_registry.py`
- Logique d’agrégation dans `core/parsing/extractors/amounts.py`
- Nettoyage du texte dans `core/text/cleaner.py`
