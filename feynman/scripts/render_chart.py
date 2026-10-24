#!/usr/bin/env python3
"""Render quiet conversation-native charts as SVG, HTML, and PNG."""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote


FONT = "'Segoe UI','Microsoft YaHei UI','Noto Sans SC','PingFang SC',sans-serif"
MONO = "'Cascadia Mono','Consolas','SFMono-Regular',monospace"

THEMES: dict[str, dict[str, Any]] = {
    "dark": {
        "page": "#1A1B1C",
        "card": "#202122",
        "border": "#343638",
        "text": "#D7DADC",
        "muted": "#9AA0A6",
        "hint": "#747A80",
        "grid": "#FFFFFF14",
        "axis": "#FFFFFF26",
        "series": ["#1D9E75", "#EF9F27", "#378ADD", "#7F77DD", "#888780"],
    },
    "light": {
        "page": "#F5F5F3",
        "card": "#FFFFFF",
        "border": "#DEDDD8",
        "text": "#2C2C2A",
        "muted": "#6F706B",
        "hint": "#8C8D87",
        "grid": "#00000014",
        "axis": "#00000026",
        "series": ["#1D9E75", "#BA7517", "#185FA5", "#534AB7", "#5F5E5A"],
    },
}


class ChartError(ValueError):
    """Raised when a chart spec cannot produce an honest visual."""


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ChartError(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ChartError(f"{field} must be finite")
    return result


def _text(value: Any, field: str, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ChartError(f"{field} must be a string")
    return value.strip()


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ChartError(f"{field} must be an object")
    return value


def _sequence(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise ChartError(f"{field} must be a non-empty array")
    return value


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _fmt_number(value: float, decimals: int | None = None) -> str:
    if decimals is None:
        decimals = 0 if abs(value - round(value)) < 1e-9 else 2
    text = f"{value:,.{decimals}f}"
    return text.rstrip("0").rstrip(".") if decimals else text


def _nice_ticks(low: float, high: float, target: int = 6) -> tuple[float, float, list[float]]:
    if not math.isfinite(low) or not math.isfinite(high):
        raise ChartError("axis bounds must be finite")
    if high < low:
        low, high = high, low
    if math.isclose(low, high):
        if low == 0:
            high = 1.0
        else:
            pad = abs(low) * 0.1
            low, high = min(0.0, low - pad), max(0.0, high + pad)
    span = high - low
    raw_step = span / max(1, target)
    exponent = math.floor(math.log10(raw_step)) if raw_step > 0 else 0
    fraction = raw_step / (10**exponent)
    if fraction <= 1:
        nice = 1.0
    elif fraction <= 2:
        nice = 2.0
    elif fraction <= 2.5:
        nice = 2.5
    elif fraction <= 5:
        nice = 5.0
    else:
        nice = 10.0
    step = nice * (10**exponent)
    tick_low = math.floor(low / step) * step
    tick_high = math.ceil(high / step) * step
    count = int(round((tick_high - tick_low) / step))
    ticks = [tick_low + i * step for i in range(count + 1)]
    return tick_low, tick_high, ticks


def _padded_nice_axis(
    values: Iterable[float],
    ratio: float = 0.10,
    target: int = 5,
) -> tuple[float, float, list[float]]:
    raw = list(values)
    low = min(raw)
    high = max(raw)
    span = high - low
    if math.isclose(span, 0):
        span = abs(low) * 0.1 or 1.0
    pad = span * ratio
    padded_low = low - pad
    if low >= 0 and padded_low < 0:
        padded_low = 0.0
    return _nice_ticks(padded_low, high + pad, target=target)


def _tick_decimals(ticks: Iterable[float]) -> int:
    for tick in ticks:
        if not math.isclose(tick, round(tick), abs_tol=1e-8):
            return 1 if max(abs(t) for t in ticks) < 100 else 2
    return 0


def _format_tick(
    value: float,
    ticks: list[float],
    prefix: str = "",
    suffix: str = "",
) -> str:
    decimals = _tick_decimals(ticks)
    number = f"{value:,.{decimals}f}"
    if decimals:
        number = number.rstrip("0").rstrip(".")
    return f"{prefix}{number}{suffix}"


def _fmt_value(value: float, spec: dict[str, Any], axis: str = "") -> str:
    decimals = spec.get(f"value_decimals_{axis}") if axis else None
    if decimals is None:
        decimals = spec.get("value_decimals")
    if decimals is not None:
        if isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
            raise ChartError(f"value_decimals_{axis} must be a non-negative integer")
    else:
        decimals = 0 if math.isclose(value, round(value), abs_tol=1e-9) else 2
    prefix = _text(spec.get(f"value_prefix_{axis}"), f"value_prefix_{axis}")
    suffix = _text(spec.get(f"value_suffix_{axis}"), f"value_suffix_{axis}")
    if not prefix and axis != "y":
        prefix = _text(spec.get("value_prefix"), "value_prefix")
    if not suffix and axis != "y":
        suffix = _text(spec.get("value_suffix"), "value_suffix")
    return f"{prefix}{value:,.{decimals}f}{suffix}"


def _unique_colors(values: Iterable[str], palette: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    for color in palette:
        if color not in result:
            result.append(color)
    return result


def _text_width(value: str, font_size: float = 12.0) -> float:
    width = 0.0
    for char in value:
        if unicodedata.east_asian_width(char) in {"W", "F"}:
            width += font_size
        elif char.isspace():
            width += font_size * 0.36
        else:
            width += font_size * 0.60
    return width


def _legend_rows(entries: list[dict[str, str]], x: float, y: float, max_width: float) -> tuple[list[str], float]:
    rows: list[list[dict[str, str]]] = [[]]
    widths: list[float] = [0.0]
    for entry in entries:
        entry_width = _text_width(entry["label"]) + 15
        extra = entry_width if not rows[-1] else entry_width + 18
        if rows[-1] and widths[-1] + extra > max_width:
            rows.append([])
            widths.append(0.0)
            extra = entry_width
        rows[-1].append(entry)
        widths[-1] += extra

    output: list[str] = []
    cursor_y = y
    for row in rows:
        cursor_x = x
        for entry in row:
            output.append(
                f'<rect x="{cursor_x:.1f}" y="{cursor_y - 9:.1f}" width="10" height="10" '
                f'rx="2" fill="{_esc(entry["color"])}"/>'
            )
            output.append(
                f'<text x="{cursor_x + 15:.1f}" y="{cursor_y:.1f}" fill="__MUTED__" '
                f'font-size="12" font-weight="400">{_esc(entry["label"])}</text>'
            )
            cursor_x += _text_width(entry["label"]) + 33
        cursor_y += 20
    return output, len(rows) * 20


def _series_entries(series: list[dict[str, Any]], palette: list[str]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for index, item in enumerate(series):
        label = _text(item.get("label"), f"series[{index}].label")
        if not label:
            raise ChartError(f"series[{index}].label is required")
        color = _text(item.get("color"), f"series[{index}].color", palette[index % len(palette)])
        if not color.startswith("#"):
            raise ChartError(f"series[{index}].color must be a hex color")
        entries.append({"label": label, "color": color})
    return entries


def _render_bar_h(spec: dict[str, Any], theme: dict[str, Any], canvas: Box, content: Box, top: float) -> tuple[list[str], float]:
    items = _sequence(spec.get("items"), "items")
    palette = theme["series"]
    parsed: list[dict[str, Any]] = []
    for index, raw in enumerate(items):
        item = _mapping(raw, f"items[{index}]")
        label = _text(item.get("label"), f"items[{index}].label")
        if not label:
            raise ChartError(f"items[{index}].label is required")
        value = _finite_number(item.get("value"), f"items[{index}].value")
        if value < 0:
            raise ChartError("bar_h values must be non-negative; split negative values into a second chart")
        color = _text(item.get("color"), f"items[{index}].color", palette[0])
        parsed.append({"label": label, "value": value, "color": color})

    explicit_height = spec.get("height")
    chart_height = (
        _finite_number(explicit_height, "height")
        if explicit_height is not None
        else max(310.0, len(parsed) * 48.0 + 74.0)
    )
    if chart_height < 220:
        raise ChartError("height must be at least 220")

    plot_left = content.x + min(250.0, max(150.0, content.width * 0.34))
    plot_right = content.x + content.width - 16
    plot_top = top + 12
    axis_y = plot_top + chart_height - 66
    plot_width = plot_right - plot_left
    max_value = max(item["value"] for item in parsed)
    tick_low, tick_high, ticks = _nice_ticks(0.0, max_value, target=7)
    if tick_low != 0:
        tick_low = 0.0

    def x_for(value: float) -> float:
        return plot_left + (value - tick_low) / (tick_high - tick_low) * plot_width

    elements: list[str] = []
    for tick in ticks:
        x = x_for(tick)
        elements.append(
            f'<line x1="{x:.1f}" y1="{plot_top:.1f}" x2="{x:.1f}" y2="{axis_y:.1f}" '
            f'stroke="{theme["grid"]}" stroke-width="1"/>'
        )
        elements.append(
            f'<text x="{x:.1f}" y="{axis_y + 19:.1f}" text-anchor="middle" '
            f'fill="{theme["muted"]}" font-size="11">'
            f'{_esc(_format_tick(tick, ticks, _text(spec.get("tick_prefix"), "tick_prefix"), _text(spec.get("tick_suffix"), "tick_suffix")))}</text>'
        )
    elements.append(
        f'<line x1="{plot_left:.1f}" y1="{axis_y:.1f}" x2="{plot_right:.1f}" y2="{axis_y:.1f}" '
        f'stroke="{theme["axis"]}" stroke-width="1"/>'
    )

    row_height = (axis_y - plot_top) / max(1, len(parsed))
    bar_height = min(22.0, max(14.0, row_height * 0.45))
    show_values = bool(spec.get("show_values", False))
    for index, item in enumerate(parsed):
        center_y = plot_top + (index + 0.5) * row_height
        end_x = x_for(item["value"])
        elements.append(
            f'<text x="{plot_left - 14:.1f}" y="{center_y + 4:.1f}" text-anchor="end" '
            f'fill="{theme["text"]}" font-size="11.5">{_esc(item["label"])}</text>'
        )
        elements.append(
            f'<rect x="{plot_left:.1f}" y="{center_y - bar_height / 2:.1f}" '
            f'width="{max(1.0, end_x - plot_left):.1f}" height="{bar_height:.1f}" '
            f'rx="3" fill="{_esc(item["color"])}"/>'
        )
        if show_values:
            elements.append(
                f'<text x="{end_x + 8:.1f}" y="{center_y + 4:.1f}" '
                f'fill="{theme["muted"]}" font-size="11">{_esc(_fmt_value(item["value"], spec))}</text>'
            )

    x_label = _text(spec.get("x_label"), "x_label")
    if x_label:
        elements.append(
            f'<text x="{(plot_left + plot_right) / 2:.1f}" y="{axis_y + 45:.1f}" '
            f'text-anchor="middle" fill="{theme["muted"]}" font-size="11">{_esc(x_label)}</text>'
        )
    return elements, chart_height


def _render_bar_v(spec: dict[str, Any], theme: dict[str, Any], canvas: Box, content: Box, top: float) -> tuple[list[str], float]:
    items = _sequence(spec.get("items"), "items")
    palette = theme["series"]
    parsed: list[dict[str, Any]] = []
    for index, raw in enumerate(items):
        item = _mapping(raw, f"items[{index}]")
        label = _text(item.get("label"), f"items[{index}].label")
        if not label:
            raise ChartError(f"items[{index}].label is required")
        value = _finite_number(item.get("value"), f"items[{index}].value")
        if value < 0:
            raise ChartError("bar_v values must be non-negative")
        parsed.append(
            {
                "label": label,
                "value": value,
                "color": _text(item.get("color"), f"items[{index}].color", palette[0]),
            }
        )
    chart_height = _finite_number(spec.get("height", 300), "height")
    if chart_height < 240:
        raise ChartError("height must be at least 240")
    plot_left = content.x + 50
    plot_right = content.x + content.width - 16
    plot_top = top + 12
    axis_y = plot_top + chart_height - 78
    max_value = max(item["value"] for item in parsed)
    tick_low, tick_high, ticks = _nice_ticks(0.0, max_value, target=5)
    if tick_low != 0:
        tick_low = 0.0

    def y_for(value: float) -> float:
        return axis_y - (value - tick_low) / (tick_high - tick_low) * (axis_y - plot_top)

    elements: list[str] = []
    for tick in ticks:
        y = y_for(tick)
        elements.append(
            f'<line x1="{plot_left:.1f}" y1="{y:.1f}" x2="{plot_right:.1f}" y2="{y:.1f}" '
            f'stroke="{theme["grid"]}" stroke-width="1"/>'
        )
        elements.append(
            f'<text x="{plot_left - 10:.1f}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="{theme["muted"]}" font-size="11">'
            f'{_esc(_format_tick(tick, ticks, _text(spec.get("tick_prefix"), "tick_prefix"), _text(spec.get("tick_suffix"), "tick_suffix")))}</text>'
        )
    elements.append(
        f'<line x1="{plot_left:.1f}" y1="{axis_y:.1f}" x2="{plot_right:.1f}" y2="{axis_y:.1f}" '
        f'stroke="{theme["axis"]}" stroke-width="1"/>'
    )
    slot = (plot_right - plot_left) / max(1, len(parsed))
    bar_width = min(42.0, slot * 0.48)
    for index, item in enumerate(parsed):
        center_x = plot_left + (index + 0.5) * slot
        end_y = y_for(item["value"])
        elements.append(
            f'<rect x="{center_x - bar_width / 2:.1f}" y="{end_y:.1f}" '
            f'width="{bar_width:.1f}" height="{max(1.0, axis_y - end_y):.1f}" '
            f'rx="3" fill="{_esc(item["color"])}"/>'
        )
        elements.append(
            f'<text x="{center_x:.1f}" y="{axis_y + 19:.1f}" text-anchor="middle" '
            f'fill="{theme["text"]}" font-size="11">{_esc(item["label"])}</text>'
        )
    x_label = _text(spec.get("x_label"), "x_label")
    if x_label:
        elements.append(
            f'<text x="{(plot_left + plot_right) / 2:.1f}" y="{axis_y + 45:.1f}" '
            f'text-anchor="middle" fill="{theme["muted"]}" font-size="11">{_esc(x_label)}</text>'
        )
    return elements, chart_height


def _render_grouped_bar(
    spec: dict[str, Any], theme: dict[str, Any], canvas: Box, content: Box, top: float
) -> tuple[list[dict[str, str]], list[str], float]:
    categories = [_text(item, "categories[]") for item in _sequence(spec.get("categories"), "categories")]
    if not all(categories):
        raise ChartError("categories cannot contain empty labels")
    series = _sequence(spec.get("series"), "series")
    if len(series) > 4:
        raise ChartError("use at most four series per grouped chart")
    entries = _series_entries(series, theme["series"])
    values: list[list[float]] = []
    for s_index, raw in enumerate(series):
        item = _mapping(raw, f"series[{s_index}]")
        raw_values = _sequence(item.get("values"), f"series[{s_index}].values")
        if len(raw_values) != len(categories):
            raise ChartError("each series must have one value per category")
        row = [_finite_number(value, f"series[{s_index}].values[]") for value in raw_values]
        if any(value < 0 for value in row):
            raise ChartError("grouped bars must be non-negative")
        values.append(row)

    chart_height = _finite_number(spec.get("height", len(categories) * 58 + 76), "height")
    if chart_height < 240:
        raise ChartError("height must be at least 240")
    plot_left = content.x + min(250.0, max(170.0, content.width * 0.34))
    plot_right = content.x + content.width - 16
    plot_top = top + 12
    axis_y = plot_top + chart_height - 66
    max_value = max(value for row in values for value in row)
    tick_low, tick_high, ticks = _nice_ticks(0.0, max_value, target=7)
    if tick_low != 0:
        tick_low = 0.0

    def x_for(value: float) -> float:
        return plot_left + value / tick_high * (plot_right - plot_left)

    elements: list[str] = []
    for tick in ticks:
        x = x_for(tick)
        elements.append(
            f'<line x1="{x:.1f}" y1="{plot_top:.1f}" x2="{x:.1f}" y2="{axis_y:.1f}" '
            f'stroke="{theme["grid"]}" stroke-width="1"/>'
        )
        elements.append(
            f'<text x="{x:.1f}" y="{axis_y + 19:.1f}" text-anchor="middle" '
            f'fill="{theme["muted"]}" font-size="11">'
            f'{_esc(_format_tick(tick, ticks, _text(spec.get("tick_prefix"), "tick_prefix"), _text(spec.get("tick_suffix"), "tick_suffix")))}</text>'
        )
    elements.append(
        f'<line x1="{plot_left:.1f}" y1="{axis_y:.1f}" x2="{plot_right:.1f}" y2="{axis_y:.1f}" '
        f'stroke="{theme["axis"]}" stroke-width="1"/>'
    )
    row_height = (axis_y - plot_top) / max(1, len(categories))
    bar_height = min(14.0, max(8.0, row_height * 0.18))
    group_gap = 3.0
    group_height = len(series) * (bar_height + group_gap) - group_gap
    for c_index, category in enumerate(categories):
        center_y = plot_top + (c_index + 0.5) * row_height
        elements.append(
            f'<text x="{plot_left - 14:.1f}" y="{center_y + 4:.1f}" text-anchor="end" '
            f'fill="{theme["text"]}" font-size="11.5">{_esc(category)}</text>'
        )
        group_top = center_y - group_height / 2
        for s_index, entry in enumerate(entries):
            value = values[s_index][c_index]
            end_x = x_for(value)
            y = group_top + s_index * (bar_height + group_gap)
            elements.append(
                f'<rect x="{plot_left:.1f}" y="{y:.1f}" width="{max(1.0, end_x - plot_left):.1f}" '
                f'height="{bar_height:.1f}" rx="3" fill="{_esc(entry["color"])}"/>'
            )
    x_label = _text(spec.get("x_label"), "x_label")
    if x_label:
        elements.append(
            f'<text x="{(plot_left + plot_right) / 2:.1f}" y="{axis_y + 45:.1f}" '
            f'text-anchor="middle" fill="{theme["muted"]}" font-size="11">{_esc(x_label)}</text>'
        )
    return entries, elements, chart_height


def _render_line_or_scatter(
    spec: dict[str, Any], theme: dict[str, Any], canvas: Box, content: Box, top: float
) -> tuple[list[str], float]:
    kind = spec["kind"]
    series = _sequence(spec.get("series"), "series")
    entries = _series_entries(series, theme["series"])
    math_axes = bool(spec.get("math_axes", False))
    chart_height = _finite_number(spec.get("height", 300), "height")
    if chart_height < 240:
        raise ChartError("height must be at least 240")

    plot = Box(content.x + 66, top + 12, content.width - 82, chart_height - 92)
    parsed: list[list[tuple[float, float]]] = []
    x_values: list[float] | None = None
    if kind == "line":
        x_labels = [_text(item, "x_labels[]") for item in _sequence(spec.get("x_labels"), "x_labels")]
        if not all(x_labels):
            raise ChartError("x_labels cannot contain empty labels")
        if spec.get("x_values") is not None:
            x_values = [
                _finite_number(item, "x_values[]")
                for item in _sequence(spec.get("x_values"), "x_values")
            ]
            if len(x_values) != len(x_labels):
                raise ChartError("x_values and x_labels must have the same length")
        if math_axes and x_values is None:
            raise ChartError("math_axes requires numeric x_values on line charts")
        for s_index, raw in enumerate(series):
            item = _mapping(raw, f"series[{s_index}]")
            raw_values = _sequence(item.get("values"), f"series[{s_index}].values")
            expected = len(x_values) if x_values is not None else len(x_labels)
            if len(raw_values) != expected:
                raise ChartError("each line series must have one value per x position")
            positions = x_values if x_values is not None else [float(index) for index in range(len(raw_values))]
            points = [
                (position, _finite_number(value, f"series[{s_index}].values[]"))
                for position, value in zip(positions, raw_values)
            ]
            parsed.append(points)
        if x_values is None:
            x_ticks = list(range(len(x_labels)))
            x_labels_out = x_labels
    else:
        x_labels_out = []
        for s_index, raw in enumerate(series):
            item = _mapping(raw, f"series[{s_index}]")
            raw_points = _sequence(item.get("points"), f"series[{s_index}].points")
            points: list[tuple[float, float]] = []
            for p_index, raw_point in enumerate(raw_points):
                if not isinstance(raw_point, list) or len(raw_point) != 2:
                    raise ChartError(f"series[{s_index}].points[{p_index}] must be [x,y]")
                points.append(
                    (
                        _finite_number(raw_point[0], f"series[{s_index}].points[{p_index}][0]"),
                        _finite_number(raw_point[1], f"series[{s_index}].points[{p_index}][1]"),
                    )
                )
            parsed.append(points)
        x_ticks = []

    ys = [y for points in parsed for _, y in points]
    xs = [x for points in parsed for x, _ in points]
    domain_ys = ys + ([0.0] if math_axes else [])
    y_low, y_high, y_ticks = _padded_nice_axis(domain_ys, ratio=0.10 if math_axes else 0.10, target=5)
    if kind == "line":
        if x_values is not None:
            domain_xs = xs + ([0.0] if math_axes else [])
            x_low, x_high, x_ticks = _padded_nice_axis(domain_xs, ratio=0.05, target=6)
            x_labels_out = [
                _format_tick(
                    tick,
                    x_ticks,
                    _text(spec.get("tick_prefix_x"), "tick_prefix_x"),
                    _text(spec.get("tick_suffix_x"), "tick_suffix_x"),
                )
                for tick in x_ticks
            ]
        else:
            raw_x_high = float(max(1, len(x_labels) - 1))
            x_low, x_high = -raw_x_high * 0.10, raw_x_high * 1.10
    else:
        domain_xs = xs + ([0.0] if math_axes else [])
        x_low, x_high, x_ticks = _padded_nice_axis(domain_xs, ratio=0.10, target=6)
    x_step = x_high - x_low or 1.0
    y_step = y_high - y_low or 1.0

    def px(value: float) -> float:
        return plot.x + (value - x_low) / x_step * plot.width

    def py(value: float) -> float:
        return plot.y + plot.height - (value - y_low) / y_step * plot.height

    elements: list[str] = []
    for tick in y_ticks:
        y = py(tick)
        elements.append(
            f'<line x1="{plot.x:.1f}" y1="{y:.1f}" x2="{plot.x + plot.width:.1f}" y2="{y:.1f}" '
            f'stroke="{theme["grid"]}" stroke-width="1"/>'
        )
        elements.append(
            f'<text x="{plot.x - 10:.1f}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="{theme["muted"]}" font-size="11">'
            f'{_esc(_format_tick(tick, y_ticks, _text(spec.get("tick_prefix_y"), "tick_prefix_y"), _text(spec.get("tick_suffix_y"), "tick_suffix_y")))}</text>'
        )

    if kind == "line" and x_values is None:
        for tick, label in zip(x_ticks, x_labels_out):
            x = px(float(tick))
            elements.append(
                f'<text x="{x:.1f}" y="{plot.y + plot.height + 19:.1f}" text-anchor="middle" '
                f'fill="{theme["muted"]}" font-size="11">{_esc(label)}</text>'
            )
    else:
        for tick in x_ticks:
            x = px(tick)
            elements.append(
                f'<line x1="{x:.1f}" y1="{plot.y:.1f}" x2="{x:.1f}" y2="{plot.y + plot.height:.1f}" '
                f'stroke="{theme["grid"]}" stroke-width="1"/>'
            )
            elements.append(
                f'<text x="{x:.1f}" y="{plot.y + plot.height + 19:.1f}" text-anchor="middle" '
                f'fill="{theme["muted"]}" font-size="11">'
                f'{_esc(_format_tick(tick, x_ticks, _text(spec.get("tick_prefix_x"), "tick_prefix_x"), _text(spec.get("tick_suffix_x"), "tick_suffix_x")))}</text>'
            )

    if math_axes:
        axis_y = py(0.0)
        axis_x = px(0.0)
        elements.extend(
            [
                f'<line x1="{plot.x:.1f}" y1="{axis_y:.1f}" x2="{plot.x + plot.width:.1f}" y2="{axis_y:.1f}" stroke="{theme["muted"]}" stroke-width="1.3"/>',
                f'<polygon points="{plot.x + plot.width:.1f},{axis_y:.1f} {plot.x + plot.width - 7:.1f},{axis_y - 4:.1f} {plot.x + plot.width - 7:.1f},{axis_y + 4:.1f}" fill="{theme["muted"]}"/>',
                f'<line x1="{axis_x:.1f}" y1="{plot.y + plot.height:.1f}" x2="{axis_x:.1f}" y2="{plot.y:.1f}" stroke="{theme["muted"]}" stroke-width="1.3"/>',
                f'<polygon points="{axis_x:.1f},{plot.y:.1f} {axis_x - 4:.1f},{plot.y + 7:.1f} {axis_x + 4:.1f},{plot.y + 7:.1f}" fill="{theme["muted"]}"/>',
                f'<text x="{axis_x + 7:.1f}" y="{axis_y + 14:.1f}" fill="{theme["muted"]}" font-size="11">O</text>',
            ]
        )
    else:
        elements.append(
            f'<line x1="{plot.x:.1f}" y1="{plot.y + plot.height:.1f}" '
            f'x2="{plot.x + plot.width:.1f}" y2="{plot.y + plot.height:.1f}" '
            f'stroke="{theme["axis"]}" stroke-width="1"/>'
        )
    for points, entry in zip(parsed, entries):
        coords = [(px(x), py(y)) for x, y in points]
        if kind == "line":
            path = " ".join(f"{'M' if index == 0 else 'L'} {x:.1f} {y:.1f}" for index, (x, y) in enumerate(coords))
            elements.append(
                f'<path d="{path}" fill="none" stroke="{_esc(entry["color"])}" '
                f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
            )
            for x, y in coords:
                elements.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{theme["card"]}" '
                    f'stroke="{_esc(entry["color"])}" stroke-width="2"/>'
                )
        else:
            for x, y in coords:
                elements.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{_esc(entry["color"])}" '
                    f'stroke="{theme["card"]}" stroke-width="1.5"/>'
                )

    y_label = _text(spec.get("y_label"), "y_label")
    x_label = _text(spec.get("x_label"), "x_label")
    if y_label:
        elements.append(
            f'<text x="{content.x + 4:.1f}" y="{plot.y + plot.height / 2:.1f}" text-anchor="middle" '
            f'transform="rotate(-90 {content.x + 4:.1f} {plot.y + plot.height / 2:.1f})" '
            f'fill="{theme["muted"]}" font-size="11">{_esc(y_label)}</text>'
        )
    if x_label:
        elements.append(
            f'<text x="{plot.x + plot.width / 2:.1f}" y="{plot.y + plot.height + 45:.1f}" '
            f'text-anchor="middle" fill="{theme["muted"]}" font-size="11">{_esc(x_label)}</text>'
        )
    return entries, elements, chart_height


def _build_svg(spec: dict[str, Any], theme_name: str, width: float) -> tuple[str, float]:
    if theme_name not in THEMES:
        raise ChartError(f"unknown theme: {theme_name}")
    theme = THEMES[theme_name]
    kind = _text(spec.get("kind"), "kind")
    allowed = {"bar_h", "bar_v", "bar_h_grouped", "line", "scatter"}
    if kind not in allowed:
        raise ChartError(f"kind must be one of: {', '.join(sorted(allowed))}")
    width_value = _finite_number(width, "width")
    if width_value < 620:
        raise ChartError("width must be at least 620")

    margin = 16.0
    content_pad_x = 24.0
    card = Box(margin, margin, width_value - margin * 2, 0.0)
    content = Box(card.x + content_pad_x, card.y + 18.0, card.width - content_pad_x * 2, 0.0)
    cursor = content.y
    show_chip = bool(spec.get("show_type_chip", False))
    if show_chip:
        cursor += 26.0

    title = _text(spec.get("title"), "title")
    subtitle = _text(spec.get("subtitle"), "subtitle")
    if title:
        cursor += 27.0
    if subtitle:
        cursor += 20.0

    legend: list[dict[str, str]] = []
    if spec.get("legend"):
        for index, raw in enumerate(_sequence(spec.get("legend"), "legend")):
            entry = _mapping(raw, f"legend[{index}]")
            label = _text(entry.get("label"), f"legend[{index}].label")
            color = _text(entry.get("color"), f"legend[{index}].color", theme["series"][index % len(theme["series"])])
            if not label:
                raise ChartError(f"legend[{index}].label is required")
            legend.append({"label": label, "color": color})

    chart_elements: list[str]
    chart_height: float
    if kind == "bar_h":
        if not legend:
            colors = _unique_colors(
                [
                    _text(_mapping(raw, "items[]").get("color"), "items[].color")
                    for raw in _sequence(spec.get("items"), "items")
                ],
                theme["series"],
            )
            legend = [{"label": "Data", "color": colors[0]}]
        legend_elements, legend_height = _legend_rows(legend, content.x, cursor + 7, content.width)
        cursor += legend_height
        chart_elements, chart_height = _render_bar_h(spec, theme, card, content, cursor)
    elif kind == "bar_v":
        if not legend:
            legend = [{"label": "Data", "color": theme["series"][0]}]
        legend_elements, legend_height = _legend_rows(legend, content.x, cursor + 7, content.width)
        cursor += legend_height
        chart_elements, chart_height = _render_bar_v(spec, theme, card, content, cursor)
    elif kind == "bar_h_grouped":
        entries, chart_elements, chart_height = _render_grouped_bar(spec, theme, card, content, cursor + 24)
        legend_elements, legend_height = _legend_rows(entries, content.x, cursor + 7, content.width)
    else:
        entries, chart_elements, chart_height = _render_line_or_scatter(spec, theme, card, content, cursor + 24)
        legend_elements, legend_height = _legend_rows(entries, content.x, cursor + 7, content.width)

    content_height = cursor - content.y + chart_height + 16
    card_height = content_height + 18
    canvas_height = card_height + margin * 2
    if canvas_height < 260:
        raise ChartError("generated canvas is unexpectedly short")

    summary = title or _text(spec.get("x_label"), "x_label", "Data chart")
    description = _text(spec.get("aria_description"), "aria_description")
    if not description:
        description = f"{summary}。图表采用 {kind} 布局。"

    elements: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_value:.0f}" height="{canvas_height:.0f}" '
        f'viewBox="0 0 {width_value:.0f} {canvas_height:.0f}" role="img" '
        f'aria-labelledby="chart-title chart-desc" style="font-family:{_esc(FONT)}">',
        f'<title id="chart-title">{_esc(summary)}</title>',
        f'<desc id="chart-desc">{_esc(description)}</desc>',
        f'<rect x="0" y="0" width="{width_value:.0f}" height="{canvas_height:.0f}" fill="{theme["page"]}"/>',
        f'<rect x="{margin:.1f}" y="{margin:.1f}" width="{card.width:.1f}" height="{card_height:.1f}" '
        f'rx="16" fill="{theme["card"]}" stroke="{theme["border"]}" stroke-width="1"/>',
    ]
    if show_chip:
        chip_label = _text(spec.get("type_chip_label"), "type_chip_label", "chart")
        elements.append(
            f'<text x="{content.x:.1f}" y="{content.y + 12:.1f}" fill="{theme["hint"]}" '
            f'font-family="{_esc(MONO)}" font-size="12">{_esc(chip_label)}</text>'
        )

    title_y = content.y + (26 if show_chip else 0) + 17
    if title:
        elements.append(
            f'<text x="{content.x:.1f}" y="{title_y:.1f}" fill="{theme["text"]}" '
            f'font-size="15" font-weight="500">{_esc(title)}</text>'
        )
    if subtitle:
        elements.append(
            f'<text x="{content.x:.1f}" y="{title_y + 20:.1f}" fill="{theme["muted"]}" '
            f'font-size="12" font-weight="400">{_esc(subtitle)}</text>'
        )

    for element in legend_elements:
        elements.append(element.replace("__MUTED__", theme["muted"]))
    elements.extend(chart_elements)
    elements.append("</svg>")
    svg = "\n".join(elements)
    return svg, canvas_height


def _build_html(svg: str, width: float, height: float, theme_name: str) -> str:
    theme = THEMES[theme_name]
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Comfortable chart</title>
  <style>
    html,body{{margin:0;background:{theme["page"]};}}
    body{{width:{width:.0f}px;height:{height:.0f}px;overflow:hidden;}}
    svg{{display:block;}}
  </style>
</head>
<body>
{svg}
</body>
</html>
"""


def _find_browser(explicit: str | None) -> str | None:
    if explicit:
        path = Path(explicit)
        return str(path) if path.is_file() else None
    for command in ("msedge", "chrome", "chromium", "google-chrome"):
        found = shutil.which(command)
        if found:
            return found
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def _render_png(
    browser: str,
    html_path: Path,
    png_path: Path,
    width: int,
    height: int,
    scale: int,
) -> None:
    profile = Path(tempfile.mkdtemp(prefix="comfortable-chart-edge-", dir=str(png_path.parent)))
    try:
        command = [
            browser,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-gpu-sandbox",
            "--disable-software-rasterizer",
            "--hide-scrollbars",
            "--no-first-run",
            "--disable-extensions",
            "--disable-breakpad",
            "--disable-crash-reporter",
            "--disable-dev-shm-usage",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=1200",
            f"--force-device-scale-factor={scale}",
            f"--window-size={width},{height}",
            f"--user-data-dir={profile}",
            f"--screenshot={png_path.resolve()}",
            html_path.resolve().as_uri(),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
        )
        if result.returncode != 0 or not png_path.is_file() or png_path.stat().st_size == 0:
            detail = (result.stderr or result.stdout or "no browser output").strip()
            raise RuntimeError(f"browser rasterization failed: {detail[-800:]}")
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def render(spec_path: Path, out_dir: Path, theme: str, width: int, scale: int, browser_path: str | None, render_png: bool) -> dict[str, Path | int]:
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ChartError(f"spec file not found: {spec_path}") from exc
    except json.JSONDecodeError as exc:
        raise ChartError(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    spec = _mapping(spec, "root")
    out_dir.mkdir(parents=True, exist_ok=True)
    svg, canvas_height = _build_svg(spec, theme, float(width))
    svg_path = out_dir / "chart.svg"
    html_path = out_dir / "chart.html"
    png_path = out_dir / "chart.png"
    svg_path.write_text(svg, encoding="utf-8")
    html_path.write_text(
        _build_html(svg, float(width), canvas_height, theme),
        encoding="utf-8",
    )
    result: dict[str, Path | int] = {
        "svg": svg_path,
        "html": html_path,
        "width": int(width),
        "height": int(round(canvas_height)),
    }
    if render_png:
        browser = _find_browser(browser_path)
        if not browser:
            raise RuntimeError("Edge or Chrome is required for PNG output; use --no-render for SVG/HTML only")
        _render_png(
            browser,
            html_path,
            png_path,
            int(width),
            int(round(canvas_height)),
            max(1, scale),
        )
        result["png"] = png_path
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="Path to the JSON chart spec")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory")
    parser.add_argument("--theme", choices=sorted(THEMES), default="dark")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--scale", type=int, default=2, help="Browser device scale factor")
    parser.add_argument("--browser", default=None, help="Explicit Edge/Chrome executable")
    parser.add_argument("--no-render", action="store_true", help="Write SVG/HTML without PNG")
    args = parser.parse_args()
    out_dir = args.out_dir or args.spec.parent / "chart-output"
    try:
        result = render(
            args.spec,
            out_dir,
            args.theme,
            args.width,
            args.scale,
            args.browser,
            not args.no_render,
        )
    except (ChartError, RuntimeError) as exc:
        print(f"chart error: {exc}", file=sys.stderr)
        return 2
    for name, value in result.items():
        print(f"{name}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
