# Pricing rules

TAX_RATE = 0.18


def apply_discount(price: float, percent: float) -> float:
    return round(price * (1 - percent / 100), 2)


def add_tax(price: float) -> float:
    return round(price * (1 + TAX_RATE), 2)
