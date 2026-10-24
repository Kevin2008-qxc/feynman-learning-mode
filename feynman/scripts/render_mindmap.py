#!/usr/bin/env python3
"""Render a compact Markdown-outline mind map as SVG, HTML, and PNG."""

from __future__ import annotations

import argparse
import math
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from render_chart import (
    FONT,
    MONO,
    ChartError,
    THEMES,
    _build_html,
    _esc,
    _find_browser,
    _render_png,
)


MAX_BRANCHES = 7
MAX_DEPTH = 3
LEAF_SPACING = 62.0
COLUMN_GAP = 205.0
MAX_LABEL_WIDTH = 168.0
OUTLINE_PATTERN = re.compile(r"^(?P<indent>\s*)[-*+]\s+(?P<label>.+?)\s*$")


@dataclass
class MindNode:
    label: str
    depth: int = 0
    children: list["MindNode"] = field(default_factory=list)
    parent: "MindNode | None" = None
    branch_index: int = 0
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    lines: list[str] = field(default_factory=list)

    @property
    def leaf_count(self) -> int:
        if not self.children:
            return 1
        return sum(child.leaf_count for child in self.children)


def _plain_label(value: str) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value.strip())
    value = value.replace("**", "").replace("__", "").replace("`", "")
    value = value.strip("*_ ")
    if not value:
        raise ChartError("mind map labels cannot be empty")
    return value


def parse_outline(text: str) -> MindNode:
    roots: list[tuple[int, MindNode]] = []
    stack: list[tuple[int, MindNode]] = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        expanded = raw_line.expandtabs(2)
        match = OUTLINE_PATTERN.match(expanded)
        if not match:
            raise ChartError(
                f"line {line_number} is not a Markdown bullet: {raw_line!r}"
            )
        indent = len(match.group("indent"))
        label = _plain_label(match.group("label"))

        while stack and indent <= stack[-1][0]:
            stack.pop()

        if not stack:
            if roots:
                raise ChartError("mind map must have exactly one root bullet")
            node = MindNode(label=label, depth=0)
            roots.append((indent, node))
            stack = [(indent, node)]
            continue

        parent = stack[-1][1]
        node = MindNode(label=label, depth=parent.depth + 1, parent=parent)
        parent.children.append(node)
        stack.append((indent, node))

    if not roots:
        raise ChartError("mind map has no root bullet")
    root = roots[0][1]
    _validate_tree(root)
    return root


def _validate_tree(root: MindNode) -> None:
    def visit(node: MindNode) -> None:
        if len(node.children) > MAX_BRANCHES:
            raise ChartError(
                f"node {node.label!r} has {len(node.children)} children; "
                f"split the map so each node has at most {MAX_BRANCHES}"
            )
        if node.depth > MAX_DEPTH:
            raise ChartError(
                f"mind map exceeds depth {MAX_DEPTH}; split it into focused maps"
            )
        for child in node.children:
            visit(child)

    if len(root.children) < 2:
        raise ChartError("root must have at least two main branches")
    visit(root)


def _wrap_label(label: str, max_width: float, font_size: float) -> list[str]:
    lines: list[str] = []
    current = ""
    current_width = 0.0
    for char in label:
        char_width = (
            font_size
            if unicodedata.east_asian_width(char) in {"W", "F"}
            else font_size * 0.58
        )
        if current and current_width + char_width > max_width:
            lines.append(current.rstrip())
            current = char.lstrip()
            current_width = char_width
        else:
            current += char
            current_width += char_width
    if current.strip():
        lines.append(current.strip())
    if len(lines) > 2:
        raise ChartError(
            f"label {label!r} is too long; shorten it to at most two lines"
        )
    return lines or [label]


def _prepare_nodes(root: MindNode) -> None:
    stack = [root]
    while stack:
        node = stack.pop()
        if node.depth == 0:
            font_size = 16.0
            max_width = 180.0
            min_width = 152.0
        elif node.depth == 1:
            font_size = 14.0
            max_width = MAX_LABEL_WIDTH
            min_width = 126.0
        else:
            font_size = 12.5
            max_width = 156.0
            min_width = 106.0
        node.lines = _wrap_label(node.label, max_width, font_size)
        measured = 0.0
        for line in node.lines:
            measured = max(
                measured,
                sum(
                    font_size
                    if unicodedata.east_asian_width(char) in {"W", "F"}
                    else font_size * 0.58
                    for char in line
                ),
            )
        node.width = max(min_width, min(max_width + 24, measured + 28))
        node.height = max(38.0, 22.0 + len(node.lines) * 18.0)
        stack.extend(reversed(node.children))


def _split_branches(children: list[MindNode]) -> tuple[list[MindNode], list[MindNode]]:
    total = sum(child.leaf_count for child in children)
    best_index = 1
    best_difference = total
    running = 0
    for index, child in enumerate(children[:-1], start=1):
        running += child.leaf_count
        difference = abs(total - running * 2)
        if difference < best_difference:
            best_difference = difference
            best_index = index
    return children[:best_index], children[best_index:]


def _assign_colors(root: MindNode, theme: dict[str, Any]) -> None:
    palette = list(theme["series"])
    for index, child in enumerate(root.children):
        stack = [child]
        while stack:
            node = stack.pop()
            node.branch_index = index % len(palette)
            stack.extend(node.children)


def _layout(
    root: MindNode,
    width: float,
) -> tuple[float, list[tuple[MindNode, MindNode]]]:
    left, right = _split_branches(root.children)
    side_leaves = {
        "left": sum(branch.leaf_count for branch in left),
        "right": sum(branch.leaf_count for branch in right),
    }
    max_leaves = max(side_leaves.values())
    header = 100.0
    footer = 48.0
    height = max(560.0, header + footer + max_leaves * LEAF_SPACING)
    root.x = width / 2
    root.y = header + (height - header - footer) / 2

    def layout_side(branches: list[MindNode], side: str) -> None:
        if not branches:
            return
        leaf_count = sum(branch.leaf_count for branch in branches)
        top = root.y - (leaf_count - 1) * LEAF_SPACING / 2
        cursor = [top]

        def place(node: MindNode) -> None:
            if side == "left":
                node.x = root.x - 150 - (node.depth - 1) * COLUMN_GAP
            else:
                node.x = root.x + 150 + (node.depth - 1) * COLUMN_GAP
            if not node.children:
                node.y = cursor[0]
                cursor[0] += LEAF_SPACING
                return
            for child in node.children:
                place(child)
            node.y = (node.children[0].y + node.children[-1].y) / 2

        for branch in branches:
            place(branch)

    layout_side(left, "left")
    layout_side(right, "right")

    edges: list[tuple[MindNode, MindNode]] = []

    def collect_edges(node: MindNode) -> None:
        for child in node.children:
            edges.append((node, child))
            collect_edges(child)

    collect_edges(root)
    return height, edges


def _node_style(
    node: MindNode,
    theme: dict[str, Any],
) -> tuple[str, str, float, str]:
    color = theme["series"][node.branch_index % len(theme["series"])]
    if node.depth == 0:
        return "#253133", theme["text"], 1.6, "15"
    if node.depth == 1:
        return "#20292B", color, 1.4, "500"
    return "#1D2426", color, 1.0, "400"


def _draw_node(node: MindNode, theme: dict[str, Any]) -> list[str]:
    fill, stroke, stroke_width, font_weight = _node_style(node, theme)
    radius = 17 if node.depth == 0 else 11
    x = node.x - node.width / 2
    y = node.y - node.height / 2
    elements = [
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{node.width:.1f}" height="{node.height:.1f}" '
        f'rx="{radius}" fill="{fill}" stroke="{_esc(stroke)}" stroke-width="{stroke_width}"/>'
    ]
    font_size = 16 if node.depth == 0 else 14 if node.depth == 1 else 12.5
    text_color = theme["text"] if node.depth == 0 else stroke
    first_y = node.y - (len(node.lines) - 1) * 9 + font_size * 0.34
    for index, line in enumerate(node.lines):
        elements.append(
            f'<text x="{node.x:.1f}" y="{first_y + index * 18:.1f}" text-anchor="middle" '
            f'fill="{_esc(text_color)}" font-size="{font_size:.1f}" '
            f'font-weight="{font_weight}">{_esc(line)}</text>'
        )
    return elements


def _mermaid_source(root: MindNode) -> str:
    lines = ["mindmap", f"  root(({root.label}))"]

    def add(node: MindNode, depth: int, index: int = 0) -> None:
        for child_index, child in enumerate(node.children, start=1):
            prefix = "  " * (depth + 1)
            label = child.label.replace('"', "&quot;")
            lines.append(f'{prefix}n{index}_{child_index}["{label}"]')
            add(child, depth + 1, index * 10 + child_index)

    add(root, 0)
    return "\n".join(lines) + "\n"


def _build_svg(root: MindNode, theme_name: str, width: float) -> tuple[str, float]:
    if theme_name not in THEMES:
        raise ChartError(f"unknown theme: {theme_name}")
    if width < 900:
        raise ChartError("width must be at least 900")

    theme = THEMES[theme_name]
    _prepare_nodes(root)
    _assign_colors(root, theme)
    height, edges = _layout(root, width)

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-labelledby="map-title map-desc" '
        f'style="font-family:{_esc(FONT)}">',
        f'<title id="map-title">{_esc(root.label)}</title>',
        f'<desc id="map-desc">由 Markdown 大纲生成的双栏思维导图</desc>',
        f'<rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" fill="{theme["page"]}"/>',
        f'<rect x="18" y="18" width="{width - 36:.0f}" height="{height - 36:.0f}" rx="22" '
        f'fill="{theme["card"]}" stroke="{theme["border"]}"/>',
        f'<text x="44" y="54" fill="{theme["muted"]}" font-family="{_esc(MONO)}" '
        f'font-size="11">CONCEPT MAP</text>',
    ]

    for parent, child in edges:
        color = theme["series"][child.branch_index % len(theme["series"])]
        if child.x > parent.x:
            start_x = parent.x + parent.width / 2
            end_x = child.x - child.width / 2
        else:
            start_x = parent.x - parent.width / 2
            end_x = child.x + child.width / 2
        start_y, end_y = parent.y, child.y
        bend = abs(end_x - start_x) * 0.48
        direction = 1 if end_x > start_x else -1
        stroke_width = max(1.2, 3.7 - child.depth * 0.8)
        elements.append(
            f'<path d="M {start_x:.1f} {start_y:.1f} '
            f'C {start_x + direction * bend:.1f} {start_y:.1f}, '
            f'{end_x - direction * bend:.1f} {end_y:.1f}, '
            f'{end_x:.1f} {end_y:.1f}" fill="none" stroke="{_esc(color)}" '
            f'stroke-width="{stroke_width:.1f}" stroke-linecap="round" opacity=".9"/>'
        )

    stack = [root]
    while stack:
        node = stack.pop()
        elements.extend(_draw_node(node, theme))
        stack.extend(reversed(node.children))

    elements.extend(
        [
            f'<text x="44" y="{height - 34:.1f}" fill="{theme["hint"]}" font-size="11">'
            f'由 Markdown 大纲生成本地思维导图 · 不是穷尽式知识清单</text>',
            "</svg>",
        ]
    )
    return "\n".join(elements), height


def render(
    source: Path,
    out_dir: Path,
    theme: str,
    width: int,
    scale: int,
    browser_path: str | None,
    render_png: bool,
) -> dict[str, Path | int]:
    try:
        text = source.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ChartError(f"outline file not found: {source}") from exc
    root = parse_outline(text)
    svg, height = _build_svg(root, theme, float(width))
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path = out_dir / "mindmap.svg"
    html_path = out_dir / "mindmap.html"
    png_path = out_dir / "mindmap.png"
    mmd_path = out_dir / "mindmap.mmd"
    svg_path.write_text(svg, encoding="utf-8")
    html_path.write_text(_build_html(svg, float(width), height, theme), encoding="utf-8")
    mmd_path.write_text(_mermaid_source(root), encoding="utf-8")
    result: dict[str, Path | int] = {
        "svg": svg_path,
        "html": html_path,
        "mermaid": mmd_path,
        "width": width,
        "height": height,
    }
    if render_png:
        browser = _find_browser(browser_path)
        if browser is None:
            raise RuntimeError(
                "Edge or Chrome is required for PNG output; "
                "use --no-render for SVG/HTML/Mermaid only"
            )
        _render_png(browser, html_path, png_path, width, int(math.ceil(height)), scale)
        result["png"] = png_path
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outline", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("mindmap-output"))
    parser.add_argument("--theme", choices=sorted(THEMES), default="dark")
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--browser")
    parser.add_argument("--no-render", action="store_true", help="Write SVG/HTML/Mermaid without PNG")
    args = parser.parse_args()
    try:
        result = render(
            args.outline,
            args.out_dir,
            args.theme,
            args.width,
            max(1, args.scale),
            args.browser,
            not args.no_render,
        )
    except (ChartError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"svg: {result['svg']}")
    print(f"html: {result['html']}")
    print(f"mermaid: {result['mermaid']}")
    print(f"width: {result['width']}")
    print(f"height: {result['height']}")
    if "png" in result:
        print(f"png: {result['png']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
