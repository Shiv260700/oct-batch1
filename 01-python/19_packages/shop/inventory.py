# Stock tracking

from .pricing import add_tax  # relative import: from this package


class Inventory:
    def __init__(self) -> None:
        self.items: dict[str, tuple[float, int]] = {}  # name -> (price, qty)

    def add(self, name: str, price: float, qty: int) -> None:
        self.items[name] = (price, qty)

    def total_value(self) -> float:
        return sum(add_tax(price) * qty for price, qty in self.items.values())
