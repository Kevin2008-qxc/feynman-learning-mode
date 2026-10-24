#!/usr/bin/env python3
"""Render a static GeoGebra-style mathematical construction as SVG and PNG."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from render_chart import (
    FONT,
    ChartError,
    THEMES,
    Box,
    _build_html,
    _esc,
    _find_browser,
    _finite_number,
    _format_tick,
    _mapping,
    _nice_ticks,
    _render_png,
    _sequence,
    _text,
)


def _point(value: Any, field: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ChartError(f"{field} must be [x, y]")
    return (
        _finite_number(value[0], f"{field}[0]"),
        _finite_number(value[1], f"{field}[1]"),
    )


def _points(value: Any, field: str) -> list[tuple[float, float]]:
    raw_points = _sequence(value, field)
    return [_point(raw, f"{field}[]") for raw in raw_points]


def _collect_bounds(spec: dict[str, Any]) -> tuple[float, float, float, float]:
    xs: list[float] = [0.0]
    ys: list[float] = [0.0]

    for raw in spec.get("curves", []):
        curve = _mapping(raw, "curves[]")
        for x, y in _points(curve.get("points"), "curves[].points"):
            xs.append(x)
            ys.append(y)

    for raw in spec.get("segments", []):
        segment = _mapping(raw, "segments[]")
        for field in ("from", "to"):
            x, y = _point(segment.get(field), f"segments[].{field}")
            xs.append(x)
            ys.append(y)

    for raw in spec.get("vectors", []):
        vector = _mapping(raw, "vectors[]")
        for field in ("from", "to"):
            x, y = _point(vector.get(field), f"vectors[].{field}")
            xs.append(x)
            ys.append(y)

    for raw in spec.get("points", []):
        point = _mapping(raw, "points[]")
        x, y = _point(point.get("at"), "points[].at")
        xs.append(x)
        ys.append(y)

    for raw in spec.get("circles", []):
        circle = _mapping(raw, "circles[]")
        cx, cy = _point(circle.get("center"), "circles[].center")
        radius = _finite_number(circle.get("radius"), "circles[].radius")
        if radius <= 0:
            raise ChartError("circles[].radius must be positive")
        xs.extend((cx - radius, cx + radius))
        ys.extend((cy - radius, cy + radius))

    for group in ("guides",):
        for raw in spec.get(group, []):
            guide = _mapping(raw, f"{group}[]")
            orientation = _text(guide.get("orientation"), f"{group}[].orientation")
            value = _finite_number(guide.get("value"), f"{group}[].value")
            if orientation == "vertical":
                xs.append(value)
            elif orientation == "horizontal":
                ys.append(value)
            else:
                raise ChartError(f"{group}[].orientation must be vertical or horizontal")

    x_low = min(xs)
    x_high = max(xs)
    y_low = min(ys)
    y_high = max(ys)
    x_span = x_high - x_low or 2.0
    y_span = y_high - y_low or 2.0
    return (
        x_low - x_span * 0.10,
        x_high + x_span * 0.10,
        y_low - y_span * 0.12,
        y_high + y_span * 0.12,
    )


def _read_view(spec: dict[str, Any]) -> tuple[float, float, float, float]:
    raw_view = spec.get("view")
    if raw_view is None:
        return _collect_bounds(spec)
    view = _mapping(raw_view, "view")
    x_range = _sequence(view.get("x"), "view.x")
    y_range = _sequence(view.get("y"), "view.y")
    if len(x_range) != 2 or len(y_range) != 2:
        raise ChartError("view.x and view.y must each contain two values")
    x_low = _finite_number(x_range[0], "view.x[0]")
    x_high = _finite_number(x_range[1], "view.x[1]")
    y_low = _finite_number(y_range[0], "view.y[0]")
    y_high = _finite_number(y_range[1], "view.y[1]")
    if x_high <= x_low or y_high <= y_low:
        raise ChartError("view ranges must be increasing")
    return x_low, x_high, y_low, y_high


def _build_math_svg(
    spec: dict[str, Any],
    theme_name: str,
    width: float,
) -> tuple[str, float]:
    if theme_name not in THEMES:
        raise ChartError(f"unknown theme: {theme_name}")
    if width < 620:
        raise ChartError("width must be at least 620")

    theme = THEMES[theme_name]
    height = _finite_number(spec.get("height", 460), "height")
    if height < 360:
        raise ChartError("height must be at least 360")

    x_low, x_high, y_low, y_high = _read_view(spec)
    x_low, x_high, x_ticks = _nice_ticks(x_low, x_high, target=8)
    y_low, y_high, y_ticks = _nice_ticks(y_low, y_high, target=6)
    if x_high <= x_low or y_high <= y_low:
        raise ChartError("invalid x view")

    margin = 16.0
    card = Box(margin, margin, width - margin * 2, height - margin * 2)
    content = Box(card.x + 24, card.y + 18, card.width - 48, card.height - 36)
    title = _text(spec.get("title"), "title")
    subtitle = _text(spec.get("subtitle"), "subtitle")
    cursor = content.y
    if title:
        cursor += 24
    if subtitle:
        cursor += 20
    cursor += 10

    plot = Box(
        content.x + 54,
        cursor,
        content.width - 72,
        content.height - (cursor - content.y) - 54,
    )
    if plot.height < 220:
        raise ChartError("figure is too short for axes and labels")

    x_span = x_high - x_low
    y_span = y_high - y_low
    aspect = _text(spec.get("aspect"), "aspect", "auto")
    if aspect not in {"auto", "equal"}:
        raise ChartError("aspect must be auto or equal")
    if aspect == "equal":
        unit = max(x_span / plot.width, y_span / plot.height)
        x_center = (x_low + x_high) / 2
        y_center = (y_low + y_high) / 2
        x_span = plot.width * unit
        y_span = plot.height * unit
        x_low, x_high = x_center - x_span / 2, x_center + x_span / 2
        y_low, y_high = y_center - y_span / 2, y_center + y_span / 2

    def px(value: float) -> float:
        return plot.x + (value - x_low) / x_span * plot.width

    def py(value: float) -> float:
        return plot.y + plot.height - (value - y_low) / y_span * plot.height

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
        f'aria-labelledby="math-title math-desc" style="font-family:{_esc(FONT)}">',
        f'<defs><clipPath id="plot-clip"><rect x="{plot.x:.1f}" y="{plot.y:.1f}" '
        f'width="{plot.width:.1f}" height="{plot.height:.1f}"/></clipPath></defs>',
        f'<title id="math-title">{_esc(title or "数学提示图")}</title>',
        f'<desc id="math-desc">{_esc(subtitle or "静态数学构图，包含坐标轴、对象和标注")}</desc>',
        f'<rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" fill="{theme["page"]}"/>',
        f'<rect x="{card.x:.1f}" y="{card.y:.1f}" width="{card.width:.1f}" height="{card.height:.1f}" '
        f'rx="16" fill="{theme["card"]}" stroke="{theme["border"]}" stroke-width="1"/>',
    ]
    if title:
        elements.append(
            f'<text x="{content.x:.1f}" y="{content.y + 14:.1f}" fill="{theme["text"]}" '
            f'font-size="15" font-weight="500">{_esc(title)}</text>'
        )
    if subtitle:
        elements.append(
            f'<text x="{content.x:.1f}" y="{content.y + (38 if title else 14):.1f}" '
            f'fill="{theme["muted"]}" font-size="12">{_esc(subtitle)}</text>'
        )

    # Shaded regions sit below grid lines and plotted objects.
    for raw in spec.get("bands", []):
        band = _mapping(raw, "bands[]")
        orientation = _text(band.get("orientation"), "bands[].orientation")
        start = _finite_number(band.get("from"), "bands[].from")
        end = _finite_number(band.get("to"), "bands[].to")
        color = _text(band.get("color"), "bands[].color", theme["series"][0])
        opacity = _finite_number(band.get("opacity", 0.12), "bands[].opacity")
        if not 0 < opacity <= 1:
            raise ChartError("bands[].opacity must be in (0, 1]")
        if orientation == "vertical":
            left, right = sorted((px(start), px(end)))
            elements.append(
                f'<rect x="{left:.1f}" y="{plot.y:.1f}" width="{right - left:.1f}" '
                f'height="{plot.height:.1f}" fill="{_esc(color)}" opacity="{opacity:.2f}" '
                f'clip-path="url(#plot-clip)"/>'
            )
        elif orientation == "horizontal":
            top, bottom = sorted((py(start), py(end)))
            elements.append(
                f'<rect x="{plot.x:.1f}" y="{top:.1f}" width="{plot.width:.1f}" '
                f'height="{bottom - top:.1f}" fill="{_esc(color)}" opacity="{opacity:.2f}" '
                f'clip-path="url(#plot-clip)"/>'
            )
        else:
            raise ChartError("bands[].orientation must be vertical or horizontal")

    if spec.get("grid", True):
        for tick in x_ticks:
            x = px(tick)
            elements.append(
                f'<line x1="{x:.1f}" y1="{plot.y:.1f}" x2="{x:.1f}" y2="{plot.y + plot.height:.1f}" '
                f'stroke="{theme["grid"]}" stroke-width="1"/>'
            )
        for tick in y_ticks:
            y = py(tick)
            elements.append(
                f'<line x1="{plot.x:.1f}" y1="{y:.1f}" x2="{plot.x + plot.width:.1f}" y2="{y:.1f}" '
                f'stroke="{theme["grid"]}" stroke-width="1"/>'
            )

    axis_y = py(0.0)
    axis_x = px(0.0)
    elements.extend(
        [
            f'<line x1="{plot.x:.1f}" y1="{axis_y:.1f}" x2="{plot.x + plot.width:.1f}" y2="{axis_y:.1f}" stroke="{theme["muted"]}" stroke-width="1.25"/>',
            f'<polygon points="{plot.x + plot.width:.1f},{axis_y:.1f} {plot.x + plot.width - 7:.1f},{axis_y - 4:.1f} {plot.x + plot.width - 7:.1f},{axis_y + 4:.1f}" fill="{theme["muted"]}"/>',
            f'<line x1="{axis_x:.1f}" y1="{plot.y + plot.height:.1f}" x2="{axis_x:.1f}" y2="{plot.y:.1f}" stroke="{theme["muted"]}" stroke-width="1.25"/>',
            f'<polygon points="{axis_x:.1f},{plot.y:.1f} {axis_x - 4:.1f},{plot.y + 7:.1f} {axis_x + 4:.1f},{plot.y + 7:.1f}" fill="{theme["muted"]}"/>',
            f'<text x="{axis_x + 7:.1f}" y="{axis_y + 14:.1f}" fill="{theme["muted"]}" font-size="11">O</text>',
        ]
    )

    for tick in x_ticks:
        if math.isclose(tick, 0.0):
            continue
        x = px(tick)
        elements.extend(
            [
                f'<line x1="{x:.1f}" y1="{axis_y - 3:.1f}" x2="{x:.1f}" y2="{axis_y + 3:.1f}" stroke="{theme["muted"]}" stroke-width="1"/>',
                f'<text x="{x:.1f}" y="{plot.y + plot.height + 18:.1f}" text-anchor="middle" '
                f'fill="{theme["muted"]}" font-size="11">{_esc(_format_tick(tick, x_ticks))}</text>',
            ]
        )
    for tick in y_ticks:
        if math.isclose(tick, 0.0):
            continue
        y = py(tick)
        elements.extend(
            [
                f'<line x1="{axis_x - 3:.1f}" y1="{y:.1f}" x2="{axis_x + 3:.1f}" y2="{y:.1f}" stroke="{theme["muted"]}" stroke-width="1"/>',
                f'<text x="{plot.x - 10:.1f}" y="{y + 4:.1f}" text-anchor="end" '
                f'fill="{theme["muted"]}" font-size="11">{_esc(_format_tick(tick, y_ticks))}</text>',
            ]
        )

    x_label = _text(spec.get("x_label"), "x_label", "x")
    y_label = _text(spec.get("y_label"), "y_label", "y")
    elements.extend(
        [
            f'<text x="{plot.x + plot.width / 2:.1f}" y="{plot.y + plot.height + 43:.1f}" text-anchor="middle" fill="{theme["text"]}" font-size="12" font-weight="500">{_esc(x_label)}</text>',
            f'<text x="{content.x + 6:.1f}" y="{plot.y + plot.height / 2:.1f}" text-anchor="middle" transform="rotate(-90 {content.x + 6:.1f} {plot.y + plot.height / 2:.1f})" fill="{theme["text"]}" font-size="12" font-weight="500">{_esc(y_label)}</text>',
        ]
    )

    for index, raw in enumerate(spec.get("guides", [])):
        guide = _mapping(raw, f"guides[{index}]")
        orientation = _text(guide.get("orientation"), f"guides[{index}].orientation")
        value = _finite_number(guide.get("value"), f"guides[{index}].value")
        color = _text(guide.get("color"), f"guides[{index}].color", theme["muted"])
        dash = _text(guide.get("style"), f"guides[{index}].style", "dashed")
        dash_attr = ' stroke-dasharray="6 5"' if dash == "dashed" else ""
        if orientation == "vertical":
            x = px(value)
            elements.append(
                f'<line x1="{x:.1f}" y1="{plot.y:.1f}" x2="{x:.1f}" y2="{plot.y + plot.height:.1f}" '
                f'stroke="{_esc(color)}" stroke-width="1.2"{dash_attr} clip-path="url(#plot-clip)"/>'
            )
            label = _text(guide.get("label"), f"guides[{index}].label")
            if label:
                elements.append(
                    f'<text x="{x + 6:.1f}" y="{plot.y + 14:.1f}" fill="{_esc(color)}" font-size="11">{_esc(label)}</text>'
                )
        else:
            y = py(value)
            elements.append(
                f'<line x1="{plot.x:.1f}" y1="{y:.1f}" x2="{plot.x + plot.width:.1f}" y2="{y:.1f}" '
                f'stroke="{_esc(color)}" stroke-width="1.2"{dash_attr} clip-path="url(#plot-clip)"/>'
            )
            label = _text(guide.get("label"), f"guides[{index}].label")
            if label:
                elements.append(
                    f'<text x="{plot.x + plot.width - 4:.1f}" y="{y - 7:.1f}" text-anchor="end" fill="{_esc(color)}" font-size="11">{_esc(label)}</text>'
                )

    for index, raw in enumerate(spec.get("curves", [])):
        curve = _mapping(raw, f"curves[{index}]")
        points = _points(curve.get("points"), f"curves[{index}].points")
        color = _text(curve.get("color"), f"curves[{index}].color", theme["series"][index % len(theme["series"])])
        style = _text(curve.get("style"), f"curves[{index}].style", "solid")
        width_value = _finite_number(curve.get("width", 2.2), f"curves[{index}].width")
        dash_attr = ' stroke-dasharray="7 5"' if style == "dashed" else ""
        path = " ".join(
            f"{'M' if p_index == 0 else 'L'} {px(x):.1f} {py(y):.1f}"
            for p_index, (x, y) in enumerate(points)
        )
        elements.append(
            f'<path d="{path}" fill="none" stroke="{_esc(color)}" stroke-width="{width_value:.1f}" '
            f'stroke-linecap="round" stroke-linejoin="round"{dash_attr} clip-path="url(#plot-clip)"/>'
        )
        if curve.get("markers", False):
            for x, y in points:
                elements.append(
                    f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="3.3" fill="{theme["card"]}" '
                    f'stroke="{_esc(color)}" stroke-width="1.8" clip-path="url(#plot-clip)"/>'
                )
        label = _text(curve.get("label"), f"curves[{index}].label")
        if label and points:
            x, y = points[-1]
            offset = curve.get("label_offset", [8, -8])
            if not isinstance(offset, list) or len(offset) != 2:
                raise ChartError(f"curves[{index}].label_offset must be [dx, dy]")
            dx = _finite_number(offset[0], f"curves[{index}].label_offset[0]")
            dy = _finite_number(offset[1], f"curves[{index}].label_offset[1]")
            elements.append(
                f'<text x="{px(x) + dx:.1f}" y="{py(y) + dy:.1f}" fill="{_esc(color)}" '
                f'font-size="12" font-weight="500">{_esc(label)}</text>'
            )

    for index, raw in enumerate(spec.get("segments", [])):
        segment = _mapping(raw, f"segments[{index}]")
        start = _point(segment.get("from"), f"segments[{index}].from")
        end = _point(segment.get("to"), f"segments[{index}].to")
        color = _text(segment.get("color"), f"segments[{index}].color", theme["text"])
        dash_attr = ' stroke-dasharray="7 5"' if segment.get("style") == "dashed" else ""
        elements.append(
            f'<line x1="{px(start[0]):.1f}" y1="{py(start[1]):.1f}" '
            f'x2="{px(end[0]):.1f}" y2="{py(end[1]):.1f}" '
            f'stroke="{_esc(color)}" stroke-width="1.6"{dash_attr} clip-path="url(#plot-clip)"/>'
        )
        label = _text(segment.get("label"), f"segments[{index}].label")
        if label:
            elements.append(
                f'<text x="{(px(start[0]) + px(end[0])) / 2 + 6:.1f}" y="{(py(start[1]) + py(end[1])) / 2 - 8:.1f}" '
                f'fill="{_esc(color)}" font-size="11">{_esc(label)}</text>'
            )

    for index, raw in enumerate(spec.get("vectors", [])):
        vector = _mapping(raw, f"vectors[{index}]")
        start = _point(vector.get("from"), f"vectors[{index}].from")
        end = _point(vector.get("to"), f"vectors[{index}].to")
        color = _text(vector.get("color"), f"vectors[{index}].color", theme["series"][0])
        dx = px(end[0]) - px(start[0])
        dy = py(end[1]) - py(start[1])
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux
        end_x, end_y = px(end[0]), py(end[1])
        base_x, base_y = end_x - ux * 9, end_y - uy * 9
        elements.extend(
            [
                f'<line x1="{px(start[0]):.1f}" y1="{py(start[1]):.1f}" x2="{base_x:.1f}" y2="{base_y:.1f}" stroke="{_esc(color)}" stroke-width="2"/>',
                f'<polygon points="{end_x:.1f},{end_y:.1f} {base_x + nx * 4:.1f},{base_y + ny * 4:.1f} {base_x - nx * 4:.1f},{base_y - ny * 4:.1f}" fill="{_esc(color)}" clip-path="url(#plot-clip)"/>',
            ]
        )
        label = _text(vector.get("label"), f"vectors[{index}].label")
        if label:
            elements.append(
                f'<text x="{end_x + 7:.1f}" y="{end_y - 8:.1f}" fill="{_esc(color)}" font-size="12">{_esc(label)}</text>'
            )

    for index, raw in enumerate(spec.get("circles", [])):
        circle = _mapping(raw, f"circles[{index}]")
        center = _point(circle.get("center"), f"circles[{index}].center")
        radius = _finite_number(circle.get("radius"), f"circles[{index}].radius")
        color = _text(circle.get("color"), f"circles[{index}].color", theme["series"][2])
        radius_x = radius / x_span * plot.width
        radius_y = radius / y_span * plot.height
        elements.append(
            f'<ellipse cx="{px(center[0]):.1f}" cy="{py(center[1]):.1f}" '
            f'rx="{radius_x:.1f}" ry="{radius_y:.1f}" '
            f'fill="none" stroke="{_esc(color)}" stroke-width="1.8" clip-path="url(#plot-clip)"/>'
        )
        label = _text(circle.get("label"), f"circles[{index}].label")
        if label:
            elements.append(
                f'<text x="{px(center[0] + radius) + 7:.1f}" y="{py(center[1]) - 7:.1f}" '
                f'fill="{_esc(color)}" font-size="12">{_esc(label)}</text>'
            )

    for index, raw in enumerate(spec.get("points", [])):
        point = _mapping(raw, f"points[{index}]")
        x, y = _point(point.get("at"), f"points[{index}].at")
        color = _text(point.get("color"), f"points[{index}].color", theme["series"][1])
        radius = _finite_number(point.get("size", 4.2), f"points[{index}].size")
        elements.append(
            f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="{radius:.1f}" fill="{_esc(color)}" '
            f'stroke="{theme["card"]}" stroke-width="1.5" clip-path="url(#plot-clip)"/>'
        )
        label = _text(point.get("label"), f"points[{index}].label")
        if label:
            offset = point.get("label_offset", [8, -9])
            if not isinstance(offset, list) or len(offset) != 2:
                raise ChartError(f"points[{index}].label_offset must be [dx, dy]")
            dx = _finite_number(offset[0], f"points[{index}].label_offset[0]")
            dy = _finite_number(offset[1], f"points[{index}].label_offset[1]")
            elements.append(
                f'<text x="{px(x) + dx:.1f}" y="{py(y) + dy:.1f}" fill="{theme["text"]}" font-size="11">'
                f'{_esc(label)}</text>'
            )

    elements.append("</svg>")
    return "\n".join(elements), height


def render(
    spec_path: Path,
    out_dir: Path,
    theme: str,
    width: int,
    scale: int,
    browser_path: str | None,
    render_png: bool,
) -> dict[str, Path | int]:
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ChartError(f"spec file not found: {spec_path}") from exc
    except json.JSONDecodeError as exc:
        raise ChartError(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    spec = _mapping(spec, "root")
    svg, height = _build_math_svg(spec, theme, float(width))
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path = out_dir / "math.svg"
    html_path = out_dir / "math.html"
    png_path = out_dir / "math.png"
    svg_path.write_text(svg, encoding="utf-8")
    html_path.write_text(_build_html(svg, float(width), height, theme), encoding="utf-8")
    result: dict[str, Path | int] = {
        "svg": svg_path,
        "html": html_path,
        "width": width,
        "height": height,
    }
    if render_png:
        browser = _find_browser(browser_path)
        if browser is None:
            raise RuntimeError("Edge or Chrome is required for PNG output; use --no-render for SVG/HTML only")
        _render_png(browser, html_path, png_path, width, int(math.ceil(height)), scale)
        result["png"] = png_path
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("math-output"))
    parser.add_argument("--theme", choices=sorted(THEMES), default="dark")
    parser.add_argument("--width", type=int, default=760)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--browser")
    parser.add_argument("--no-render", action="store_true", help="Write SVG/HTML without PNG")
    args = parser.parse_args()
    try:
        result = render(
            args.spec,
            args.out_dir,
            args.theme,
            args.width,
            max(1, args.scale),
            args.browser,
            not args.no_render,
        )
    except (ChartError, RuntimeError, OSError) as exc:
        print(f"error: {exc}")
        return 1

    print(f"svg: {result['svg']}")
    print(f"html: {result['html']}")
    print(f"width: {result['width']}")
    print(f"height: {result['height']}")
    if "png" in result:
        print(f"png: {result['png']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
