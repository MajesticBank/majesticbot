"""
This file defines a custom decimal class which uses some functionality of the decimal.Decimal() but applies fixed
precision set to 8 decimal places throughout the entire process
"""

from __future__ import annotations

import decimal


class Decimal:
    REGEX = '^\d*\.?\d+$'

    def __init__(self, n: float | str | decimal.Decimal):
        n = str(n)
        stop_idx = n.find(".")

        if stop_idx == -1:
            self.n = n
        else:
            integer = n[:stop_idx]
            fractional = n[stop_idx + 1:stop_idx + 9]
            self.n = f"{integer}.{fractional}"

    def explode(self):
        if self.is_int():
            return [self.n, None]
        else:
            stop_idx = self.stop_idx()
            integer = self.n[:stop_idx]
            fractional = self.n[stop_idx + 1:stop_idx + 9]
            return [integer, fractional]

    def stop_idx(self):
        return self.n.find(".")

    def is_int(self):
        stop_idx = self.stop_idx()
        if stop_idx == -1:
            return True
        return False

    def __str__(self):
        if self.is_int():
            return self.n

        integer, fractional = self.explode()
        fractional.ljust(8, "0")
        return f"{integer}.{fractional}"

    def numeric(self) -> bool:
        try:
            decimal.Decimal(self.n)
            return True
        except decimal.InvalidOperation:
            return False
