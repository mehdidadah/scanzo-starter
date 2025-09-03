RECEIPT_EXTRACTION_PROMPT = """
Extract receipt information focusing on VENDOR, TOTALS and TAX DETAILS.

IGNORE the items/products section - focus only on financial totals and tax breakdown.

CRITICAL FOR TAX EXTRACTION:
Look for tax tables/sections showing multiple lines like:
  B TVA 10.00    50.55    5.05    55.60
  C TVA 10.00    22.09    2.21    24.30
Each line is a SEPARATE tax entry - extract ALL lines even if same rate!

Also look for single tax mentions like:
  TVA 10%: 6.95€ (69.55€HT / 76.50€TTC)

Return this JSON:

{
    "vendor": {
        "name": "vendor name",
        "address": "address if shown",
        "siret": "SIRET/registration number"
    },
    "transaction": {
        "date": "YYYY-MM-DD",
        "time": "HH:MM",
        "receipt_number": "number"
    },
    "tax_lines": [
        // EXTRACT EVERY TAX LINE YOU SEE
        {
            "label": "B/C/* or null",
            "rate": 10.0,
            "base_ht": 50.55,
            "tva": 5.05,
            "ttc": 55.60
        }
        // Add more lines if you see them
    ],
    "totals": {
        "total_ht": sum of all HT or subtotal,
        "total_tva": sum of all TVA,
        "total_ttc": final total amount
    },
    "payment": {
        "method": "CARD/CASH or null"
    }
}

RULES:
- Extract ALL tax lines, don't combine them
- Numbers as decimals (10.50 not "10,50")
- Focus on the bottom of receipt for tax details
- If you see 2 tax lines, return 2 entries in tax_lines
"""
