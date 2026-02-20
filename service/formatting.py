from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math
from typing import Any


def _as_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    # Avoid surprises: bool is subclass of int
    if isinstance(value, bool):
        return Decimal(int(value))

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def quantize_half_up(value: Any, decimals: int) -> Decimal | None:
    d = _as_decimal(value)
    if d is None:
        return None

    try:
        decimals_int = int(decimals)
    except Exception:
        decimals_int = 0
    if decimals_int < 0:
        decimals_int = 0

    exp = Decimal("1").scaleb(-decimals_int)  # e.g. 1E-2
    try:
        return d.quantize(exp, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None


def _format_decimal_en(
    value: Any,
    *,
    decimals: int = 2,
    show_sign: bool = False,
    grouping: bool = False,
) -> str | None:
    q = quantize_half_up(value, decimals)
    if q is None:
        return None

    sign = "+" if show_sign else ""
    group = "," if grouping else ""
    fmt = f"{sign}{group}.{int(decimals)}f"
    return format(q, fmt)


def format_id_decimal(value: Any, *, decimals: int = 1, none: str = "-") -> str:
    """Format number with Indonesian separators (thousands '.', decimal ',')."""
    s = _format_decimal_en(value, decimals=decimals, show_sign=False, grouping=True)
    if s is None:
        return none
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def format_id_percent(
    value: Any,
    *,
    decimals: int = 2,
    show_sign: bool = True,
    none: str = "-",
    space_before_percent: bool = False,
) -> str:
    """Format percent with Indonesian decimal separator.

    Examples:
      - show_sign=True  -> "+1,23%"
      - show_sign=False -> "1,23%"
    """
    s = _format_decimal_en(value, decimals=decimals, show_sign=show_sign, grouping=False)
    if s is None:
        return none
    s = s.replace(".", ",")
    sp = " " if space_before_percent else ""
    return f"{s}{sp}%"


def format_en_percent(
    value: Any,
    *,
    decimals: int = 2,
    show_sign: bool = False,
    none: str = "",
) -> str:
    """Format percent with '.' decimal separator (useful for Plotly annotations)."""
    s = _format_decimal_en(value, decimals=decimals, show_sign=show_sign, grouping=False)
    if s is None:
        return none
    return f"{s}%"


def format_en_decimal(
    value: Any,
    *,
    decimals: int = 2,
    show_sign: bool = False,
    grouping: bool = True,
    none: str = "-",
) -> str:
    """Format number with English-style separators (thousands ',', decimal '.')."""
    s = _format_decimal_en(value, decimals=decimals, show_sign=show_sign, grouping=grouping)
    if s is None:
        return none
    return s


def format_id_int_thousands(value: Any, *, none: str = "") -> str:
    """Format integer with Indonesian thousands separator (.). Uses HALF_UP rounding."""
    q = quantize_half_up(value, 0)
    if q is None:
        return none
    try:
        n = int(q)
    except Exception:
        return none
    return f"{n:,}".replace(",", ".")


def qround_float(value: Any, *, decimals: int = 2, none: float | None = None) -> float | None:
    """Quantize with HALF_UP and return float (for numeric tables/charts).

    Use this when the UI component insists on numeric types but you still want
    consistent rounding behavior.
    """
    if value is None:
        return none
    try:
        if isinstance(value, float) and math.isnan(value):
            return none
    except Exception:
        pass

    q = quantize_half_up(value, decimals)
    if q is None:
        return none
    try:
        return float(q)
    except Exception:
        return none
