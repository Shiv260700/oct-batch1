# Packages: a folder of modules with an __init__.py
#
#   19_packages/
#   ├── main.py              <- you are here (run this)
#   └── shop/                <- a package
#       ├── __init__.py
#       ├── pricing.py
#       ├── inventory.py
#       └── payments/        <- a subpackage
#           ├── __init__.py
#           └── card.py

import shop                          # the package (runs shop/__init__.py)
from shop import Inventory, add_tax  # names re-exported by __init__.py
from shop.payments.card import charge  # full dotted path into a subpackage
from shop.pricing import TAX_RATE    # a name __init__.py didn't re-export

print(shop.__version__)
print(add_tax(100), TAX_RATE)
print(shop.apply_discount(200, 10))

stock = Inventory()
stock.add("pen", 10, 5)
stock.add("book", 100, 2)
print(stock.total_value())

print(charge(50))
