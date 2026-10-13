# Card payments

from ..pricing import add_tax  # `..` goes up one package, to shop


def charge(amount: float) -> str:
    return f"Charged {add_tax(amount):.2f} to card"
