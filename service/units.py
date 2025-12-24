from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RupiahUnit:
    label: str
    divisor: float


_RUPIAH_UNITS: list[RupiahUnit] = [
    RupiahUnit("Triliun", 1_000_000_000_000.0),
    RupiahUnit("Miliar", 1_000_000_000.0),
    RupiahUnit("Juta", 1_000_000.0),
    RupiahUnit("Ribu", 1_000.0),
    RupiahUnit("Rp", 1.0),
]


def pick_rupiah_unit(max_abs_value: float | int | None) -> RupiahUnit:
    """Pick a display unit so the scaled max is >= 1 when possible."""
    if max_abs_value is None:
        return _RUPIAH_UNITS[-1]

    try:
        v = float(max_abs_value)
    except Exception:
        return _RUPIAH_UNITS[-1]

    v = abs(v)
    if v <= 0:
        return _RUPIAH_UNITS[-1]

    for u in _RUPIAH_UNITS:
        if v >= u.divisor:
            return u
    return _RUPIAH_UNITS[-1]


def pick_rupiah_unit_from_values(values: Iterable[float | int | None]) -> RupiahUnit:
    max_abs = 0.0
    for x in values:
        if x is None:
            continue
        try:
            fx = float(x)
        except Exception:
            continue
        if fx != fx:  # NaN
            continue
        max_abs = max(max_abs, abs(fx))
    return pick_rupiah_unit(max_abs)


def rupiah_unit_axis_label(unit: RupiahUnit) -> str:
    return "Nilai (Rp)" if unit.label == "Rp" else f"Nilai (Rp {unit.label})"


def rupiah_unit_suffix(unit: RupiahUnit) -> str:
    return "(Rp)" if unit.label == "Rp" else f"(Rp {unit.label})"
