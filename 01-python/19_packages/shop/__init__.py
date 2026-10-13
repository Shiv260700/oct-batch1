# Makes `shop` a package. Runs once, the first time `shop` is imported.
# Re-exporting here lets users write `from shop import add_tax`
# instead of `from shop.pricing import add_tax`.

from .inventory import Inventory
from .pricing import add_tax, apply_discount

__all__ = ["Inventory", "add_tax", "apply_discount"]  # what `from shop import *` gives
__version__ = "1.0.0"
