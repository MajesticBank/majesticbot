"""
This file provider helper function for the styling of HTML messages in Telegram
"""
from __future__ import annotations

from decimal import Decimal


def a(text: str, href: str) -> str:
    return f'<a href="{href}">{text}</a>'


def b(s: str) -> str:
    return f"<b>{s}</b>"


def i(s: str) -> str:
    return f"<i>{s}</i>"


def u(s: str) -> str:
    return f"<u>{s}</u>"


def pre(s: str | Decimal) -> str:
    return f"<pre>{s}</pre>"


def code(s: str | Decimal) -> str:
    return f"<code>{s}</code>"
