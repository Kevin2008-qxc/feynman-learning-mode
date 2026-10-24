from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "feynman"
SKILL_TEXT = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
UI_TEXT = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
VISUAL_TEXT = (SKILL_DIR / "references" / "visual-hints.md").read_text(
    encoding="utf-8"
)
CHART_SPEC_TEXT = (SKILL_DIR / "references" / "chart-spec.md").read_text(
    encoding="utf-8"
)
MATH_FIGURE_TEXT = (SKILL_DIR / "references" / "math-figures.md").read_text(
    encoding="utf-8"
)
MEDICAL_TEXT = (SKILL_DIR / "references" / "medical-concepts.md").read_text(
    encoding="utf-8"
)
MEDICAL_MECHANISMS_TEXT = (
    SKILL_DIR / "references" / "medical-mechanisms.md"
).read_text(encoding="utf-8")
MEDICAL_ATTRIBUTION_TEXT = (
    SKILL_DIR / "assets" / "medical" / "ATTRIBUTION.md"
).read_text(encoding="utf-8")
MINDMAP_TEXT = (SKILL_DIR / "references" / "mindmaps.md").read_text(
    encoding="utf-8"
)


class FeynmanSkillContractTests(unittest.TestCase):
    def test_frontmatter_has_trigger_and_safe_scope(self) -> None:
        match = re.match(r"---\n(.*?)\n---", SKILL_TEXT, re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1)
        self.assertIn("name: feynman", frontmatter)
        self.assertIn("\u8d39\u66fc", frontmatter)
        self.assertIn("Do not use", frontmatter)
        self.assertNotIn("TODO", SKILL_TEXT)

    def test_starts_in_character_without_rule_dump(self) -> None:
        self.assertIn("\u76f4\u63a5\u5f00\u59cb\u5bf9\u8bdd", SKILL_TEXT)
        self.assertIn("\u4e0d\u4ecb\u7ecd\u89c4\u5219", SKILL_TEXT)

    def test_limits_each_turn_to_one_focus(self) -> None:
        self.assertIn("\u6bcf\u8f6e\u53ea\u8ffd\u4e00\u4e2a\u6700\u5173\u952e\u7684\u95ee\u9898", SKILL_TEXT)
        self.assertIn("\u53ea\u4fdd\u7559\u4e00\u4e2a\u660e\u786e\u7684\u65b0\u624b\u731c\u6d4b", SKILL_TEXT)
        self.assertIn("\u4e00\u5230\u4e09\u53e5\u8bdd", SKILL_TEXT)

    def test_scopes_skill_to_basic_concept_reinforcement(self) -> None:
        self.assertIn("\u57fa\u7840\u6982\u5ff5\u5f3a\u5316", SKILL_TEXT)
        self.assertIn("\u4e0d\u627f\u62c5\u5b8c\u6574\u8bfe\u7a0b\u89c4\u5212", SKILL_TEXT)
        self.assertIn("\u5957\u9898\u8bad\u7ec3", SKILL_TEXT)

    def test_requires_marked_and_non_repeated_misconceptions(self) -> None:
        self.assertIn("\u65b0\u624b\u731c\u6d4b\u5fc5\u987b\u8868\u73b0\u4e3a\u731c\u6d4b", SKILL_TEXT)
        self.assertIn("\u4e0d\u80fd\u628a\u9519\u8bef\u5185\u5bb9\u5199\u6210\u786e\u5b9a\u4e8b\u5b9e", SKILL_TEXT)
        self.assertIn("\u5df2\u7ecf\u7ea0\u6b63\u8fc7\u7684\u9519\u8bef\u4e0d\u5f97\u91cd\u590d\u4f7f\u7528", SKILL_TEXT)

    def test_has_exit_mode_and_transfer_check(self) -> None:
        self.assertIn("\u7ed3\u675f\u4e0e\u9a8c\u6536", SKILL_TEXT)
        self.assertIn("\u8fc1\u79fb\u68c0\u67e5", SKILL_TEXT)
        self.assertIn("\u4f60\u8bf4\u6b63\u786e\u7b54\u6848", SKILL_TEXT)

    def test_has_safety_and_runtime_privacy_boundaries(self) -> None:
        self.assertIn("\u5b89\u5168\u63d0\u9192", SKILL_TEXT)
        self.assertIn("\u77ed\u6682\u8df3\u51fa\u89d2\u8272", SKILL_TEXT)
        self.assertIn("\u4e0d\u5199\u5165\u957f\u671f\u8bb0\u5fc6", SKILL_TEXT)
        self.assertIn("\u4e0d\u8bfb\u53d6\u65e0\u5173\u6587\u4ef6", SKILL_TEXT)

    def test_visual_hints_are_conditional_and_inquiry_driven(self) -> None:
        self.assertIn("references/visual-hints.md", SKILL_TEXT)
        self.assertIn("references/chart-spec.md", SKILL_TEXT)
        self.assertIn("\u81ea\u9002\u5e94\u53ef\u89c6\u5316", SKILL_TEXT)
        self.assertIn("\u5355\u6b21\u8f93\u51fa\u5982\u679c\u914d\u56fe", SKILL_TEXT)
        self.assertIn("\u540c\u4e00\u5173\u7cfb\u4e0d\u5f97\u91cd\u590d\u753b", SKILL_TEXT)
        self.assertIn("\u56fe\u540e\u53ea\u95ee\u4e00\u4e2a\u89e3\u91ca\u6027\u95ee\u9898", SKILL_TEXT)
        self.assertIn("\u4e0d\u662f\u5b8c\u6574\u7b54\u6848", VISUAL_TEXT)
        self.assertIn("Mermaid", VISUAL_TEXT)
        self.assertIn("\u793a\u610f\u56fe", VISUAL_TEXT)
        self.assertIn("render_chart.py", CHART_SPEC_TEXT)

    def test_chart_renderer_generates_svg_and_html(self) -> None:
        renderer = SKILL_DIR / "scripts" / "render_chart.py"
        spec = {
            "kind": "line",
            "math_axes": True,
            "x_labels": ["1", "2", "3", "4"],
            "x_values": [1, 2, 3, 4],
            "x_label": "离散序号",
            "y_label": "误差",
            "series": [
                {"label": "A", "values": [1, 0.5, 0.3333, 0.25]},
                {"label": "B", "values": [-1, 0.5, -0.3333, 0.25]},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path = temp / "chart.json"
            spec_path.write_text(
                json.dumps(spec),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(renderer),
                    str(spec_path),
                    "--out-dir",
                    str(temp / "out"),
                    "--no-render",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            svg_path = temp / "out" / "chart.svg"
            self.assertTrue(svg_path.is_file())
            self.assertTrue((temp / "out" / "chart.html").is_file())
            svg = svg_path.read_text(encoding="utf-8")
            self.assertIn("离散序号", svg)
            self.assertIn("误差", svg)
            self.assertNotIn(">chart</text>", svg)
        self.assertIn(">O</text>", svg)
        self.assertGreaterEqual(svg.count("<polygon"), 2)

    def test_allows_only_one_adjacent_extension(self) -> None:
        self.assertIn("\u4e00\u6b65\u77e5\u8bc6\u5ef6\u4f38", SKILL_TEXT)
        self.assertIn("\u4e00\u6b21\u53ea\u9009\u4e00\u4e2a\u5173\u7cfb", SKILL_TEXT)
        self.assertIn("\u82e5\u7528\u6237\u65e0\u6cd5\u8bf4\u660e\u8fde\u63a5", SKILL_TEXT)
        self.assertIn("\u4e0d\u81ea\u52a8\u5c55\u5f00\u8bfe\u7a0b", SKILL_TEXT)

    def test_medical_adapter_has_safety_and_causal_structure(self) -> None:
        self.assertIn("references/medical-concepts.md", SKILL_TEXT)
        self.assertIn("references/medical-mechanisms.md", SKILL_TEXT)
        self.assertIn("\u7ed3\u6784\u2014\u529f\u80fd\u2014\u635f\u4f24\u2014\u540e\u679c", SKILL_TEXT)
        self.assertIn("\u4e0d\u8fdb\u884c\u4e2a\u4eba\u8bca\u65ad", MEDICAL_TEXT)
        self.assertIn("\u4e0d\u5f97\u51ed\u8bb0\u5fc6\u7f16\u9020", MEDICAL_TEXT)
        self.assertIn("\u4e2d\u67a2/\u521d\u7ea7\u514d\u75ab\u5668\u5b98", MEDICAL_TEXT)
        self.assertIn("\u5916\u5468/\u6b21\u7ea7\u514d\u75ab\u5668\u5b98", MEDICAL_TEXT)
        self.assertIn("\u7cbe\u51c6\u6027\u5e95\u7ebf", MEDICAL_MECHANISMS_TEXT)
        self.assertIn("\u533a\u5ba4", MEDICAL_MECHANISMS_TEXT)
        self.assertIn("\u52a8\u4f5c\u8bed\u4e49", MEDICAL_MECHANISMS_TEXT)
        self.assertIn("\u4e0d\u5f97\u590d\u5236\u5176\u56fe\u6807", MEDICAL_MECHANISMS_TEXT)

    def test_mindmap_renderer_builds_svg_and_mermaid(self) -> None:
        renderer = SKILL_DIR / "scripts" / "render_mindmap.py"
        self.assertIn("references/mindmaps.md", SKILL_TEXT)
        self.assertIn("render_mindmap.py", SKILL_TEXT)
        self.assertIn("\u56db\u5c42", MINDMAP_TEXT)
        self.assertIn("\u57fa\u7840\u6982\u5ff5\u56fe\u4f18\u5148\u6a21\u677f", MINDMAP_TEXT)
        self.assertIn("\u662f\u4ec0\u4e48", MINDMAP_TEXT)
        self.assertIn("\u6761\u4ef6\u4e0e\u8fb9\u754c", MINDMAP_TEXT)
        self.assertIn("\u6613\u6df7\u4e0e\u53cd\u4f8b", MINDMAP_TEXT)
        outline = (
            "- 免疫系统\n"
            "  - 中枢器官\n"
            "    - 骨髓\n"
            "    - 胸腺\n"
            "  - 外周器官\n"
            "    - 淋巴结\n"
            "    - 脾\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "mindmap.md"
            source.write_text(outline, encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    str(renderer),
                    str(source),
                    "--out-dir",
                    str(temp / "out"),
                    "--no-render",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            svg = (temp / "out" / "mindmap.svg").read_text(encoding="utf-8")
            mermaid = (temp / "out" / "mindmap.mmd").read_text(encoding="utf-8")
            self.assertIn("免疫系统", svg)
            self.assertIn("中枢器官", svg)
            self.assertTrue(mermaid.startswith("mindmap\n"))
            self.assertIn("胸腺", mermaid)

    def test_medical_assets_are_licensed_and_traceable(self) -> None:
        medical_root = SKILL_DIR / "assets" / "medical"
        anatomy = medical_root / "openstax" / "lymphatic-system-anatomy.jpg"
        self.assertTrue(anatomy.is_file())
        self.assertTrue(anatomy.read_bytes().startswith(b"\xff\xd8\xff"))
        self.assertFalse((medical_root / "immune-organs.svg").exists())

        self.assertIn("CC BY 3.0", MEDICAL_ATTRIBUTION_TEXT)
        self.assertIn("CC BY 4.0", MEDICAL_ATTRIBUTION_TEXT)
        self.assertIn(
            "No BioGDP",
            (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8"),
        )

        for filename, stable_id in {
            "immune-system-overview.svg": "R-HSA-168256",
            "innate-immune-system.svg": "R-HSA-168249",
            "adaptive-immune-system.svg": "R-HSA-1280218",
        }.items():
            image = medical_root / "reactome" / filename
            self.assertTrue(image.is_file())
            svg = image.read_text(encoding="utf-8")
            ET.fromstring(svg)
            self.assertIn(f'id="{stable_id}"', svg)
            self.assertGreater(len(svg), 400_000)
            preview = image.with_suffix(".png")
            self.assertTrue(preview.is_file())
            self.assertTrue(preview.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_math_figure_renderer_supports_geometric_objects(self) -> None:
        renderer = SKILL_DIR / "scripts" / "render_math_figure.py"
        self.assertIn("render_math_figure.py", SKILL_TEXT)
        self.assertIn("references/math-figures.md", SKILL_TEXT)
        self.assertIn("GeoGebra", MATH_FIGURE_TEXT)
        spec = {
            "title": "切线示意",
            "aspect": "equal",
            "x_label": "x",
            "y_label": "y",
            "view": {"x": [-2, 2], "y": [-2, 2]},
            "curves": [
                {
                    "label": "f",
                    "points": [[-1, 1], [0, 0], [1, 1]],
                }
            ],
            "segments": [
                {
                    "from": [-1, 0],
                    "to": [1, 2],
                    "style": "dashed",
                    "label": "切线",
                }
            ],
            "vectors": [
                {
                    "from": [0, 0],
                    "to": [1, 1],
                    "label": "v",
                }
            ],
            "circles": [
                {
                    "center": [0, 0],
                    "radius": 1,
                }
            ],
            "points": [
                {
                    "at": [0, 0],
                    "label": "O",
                }
            ],
            "guides": [
                {
                    "orientation": "vertical",
                    "value": 1,
                    "label": "N",
                }
            ],
            "bands": [
                {
                    "orientation": "horizontal",
                    "from": -0.2,
                    "to": 0.2,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            spec_path = temp / "math.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    str(renderer),
                    str(spec_path),
                    "--out-dir",
                    str(temp / "out"),
                    "--no-render",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            svg = (temp / "out" / "math.svg").read_text(encoding="utf-8")
            self.assertIn('clip-path="url(#plot-clip)"', svg)
            self.assertIn(">O</text>", svg)
            self.assertIn("切线", svg)

    def test_ui_metadata_invokes_skill_explicitly(self) -> None:
        self.assertIn('display_name: "\u8d39\u66fc\u6982\u5ff5\u5f3a\u5316"', UI_TEXT)
        self.assertIn("$feynman", UI_TEXT)
        self.assertIn("\u6309\u9700\u56fe\u89e3", UI_TEXT)

    def test_skill_stays_within_context_budget(self) -> None:
        self.assertLess(len(SKILL_TEXT.splitlines()), 500)

    def test_publication_files_are_utf8_without_bom(self) -> None:
        for path in (
            SKILL_DIR / "SKILL.md",
            SKILL_DIR / "agents" / "openai.yaml",
            SKILL_DIR / "assets" / "medical" / "ATTRIBUTION.md",
            SKILL_DIR / "references" / "medical-concepts.md",
            SKILL_DIR / "references" / "medical-mechanisms.md",
            SKILL_DIR / "references" / "mindmaps.md",
            Path(__file__),
        ):
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), path)
            raw.decode("utf-8")


if __name__ == "__main__":
    unittest.main()
