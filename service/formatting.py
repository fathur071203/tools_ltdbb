from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math
import numbers
import re
from typing import Any


_CURRENCY_RE = re.compile(r"(?i)rp\.?")
_KEEP_RE = re.compile(r"[^0-9eE+\-.,]")
_SCIENTIFIC_RE = re.compile(r"(?P<mant>[0-9]*[.,]?[0-9]+)[eE](?P<exp>[+-]?[0-9]+)")


def parse_number(value: Any, *, none: float | None = None) -> float | None:
    """Parse a single cell into a float, per value (never per column).

    Excel exports for this project mix real numbers with human-typed text such as
    ``'742.580.600'`` (Indonesian grouping) or ``'248,294,749,080'`` (English
    grouping). Deciding the separator meaning from a whole column is unsafe: one
    text cell would change how every genuine float in that column is read. So the
    rules below are applied to each value on its own, and values that are already
    numeric are returned untouched instead of being round-tripped through text.

    Separator rules for text values:
      - both ``.`` and ``,`` present -> the rightmost one is the decimal mark;
      - a single separator kind, repeated -> thousands grouping;
      - exactly one separator with a 3-digit tail -> thousands grouping;
      - exactly one separator with any other tail -> decimal mark.
    """
    if value is None:
        return none

    if isinstance(value, bool):
        return float(value)

    # numpy scalars register as numbers.Number, so this covers them too.
    if isinstance(value, (Decimal, numbers.Number)):
        try:
            f = float(value)
        except (TypeError, ValueError, OverflowError):
            return none
        return none if math.isnan(f) else f

    s = str(value).strip()
    if not s:
        return none

    s = s.replace(" ", "").replace(" ", "")
    s = _CURRENCY_RE.sub("", s)
    s = s.replace(" ", "").strip()
    if not s:
        return none

    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    if s.endswith("%"):
        s = s[:-1]
    if s.startswith("+"):
        s = s[1:]
    elif s.startswith("-"):
        negative = True
        s = s[1:]

    s = _KEEP_RE.sub("", s)
    if not s:
        return none

    m = _SCIENTIFIC_RE.fullmatch(s)
    if m:
        try:
            f = float(m.group("mant").replace(",", ".")) * (10 ** int(m.group("exp")))
        except (ValueError, OverflowError):
            return none
        return -f if negative else f

    s = s.replace("+", "").replace("-", "")

    positions = [(i, ch) for i, ch in enumerate(s) if ch in ".,"]
    if positions:
        last_idx, last_ch = positions[-1]
        tail = s[last_idx + 1:]
        one_kind = len({ch for _, ch in positions}) == 1

        if len(positions) == 1 and tail.isdigit() and len(tail) != 3:
            s = s[:last_idx] + "." + tail
        elif one_kind:
            s = s.replace(last_ch, "")
        else:
            s = s[:last_idx].replace(".", "").replace(",", "") + "." + tail

    try:
        f = float(s)
    except (ValueError, OverflowError):
        return none
    if math.isnan(f):
        return none
    return -f if negative else f


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
