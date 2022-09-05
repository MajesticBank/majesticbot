"""
This file defines a custom decimal class which uses some functionality of the decimal.Decimal() but applies fixed
precision set to 8 decimal places throughout the entire process
"""

from __future__ import annotations

from decimal import Decimal as D, InvalidOperation


def octa_deci(n: float | str | D) -> D:
    quant = D(D(10) ** -8)
    return D(n).quantize(quant)


def is_numeric(n: float | str | D) -> bool:
    try:
        D(n)
        return True
    except InvalidOperation:
        return False


DECIMAL_REGEX = "^\d*\.?\d+$"
