# rule_registry.py (extrait)
from .rules.tva_parenthetical import TvaParentheticalRule   # 70
from .rules.tva_inline_cols   import TvaInlineColsRule      # 68
from .rules.tva_vertical      import TvaVerticalRule        # 66
from .rules.tva_inline_any    import TvaInlineAnyRule       # 65
from .rules.totals_line       import TotalsLineRule         # 50
from .rules.payment_total     import PaymentTotalRule       # 40
from .rules.total_ttc         import TotalTTCRule           # 30

def get_amount_rules():
    return [
        TvaParentheticalRule(),  # '(69,55 HT / 76,50 TTC)'
        TvaInlineColsRule(),     # HT | TVA | TTC en colonnes
        TvaVerticalRule(),       # blocs verticaux
        TvaInlineAnyRule(),      # inline + cas OCR collés/suffixes
        TotalsLineRule(),        # 'Total TTC ...'
        TotalTTCRule(),          # TTC seul
        PaymentTotalRule(),      # fallback
    ]