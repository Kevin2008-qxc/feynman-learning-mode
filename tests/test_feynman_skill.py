from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "feynman"
SKILL_TEXT = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
UI_TEXT = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
VISUAL_TEXT = (SKILL_DIR / "references" / "visual-hints.md").read_text(
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
        self.assertIn("\u6bcf\u6b21\u6700\u591a\u4e00\u5f20\u56fe", SKILL_TEXT)
        self.assertIn("\u56fe\u540e\u53ea\u95ee\u4e00\u4e2a\u89e3\u91ca\u6027\u95ee\u9898", SKILL_TEXT)
        self.assertIn("\u4e0d\u662f\u5b8c\u6574\u7b54\u6848", VISUAL_TEXT)
        self.assertIn("Mermaid", VISUAL_TEXT)
        self.assertIn("\u793a\u610f\u56fe", VISUAL_TEXT)

    def test_ui_metadata_invokes_skill_explicitly(self) -> None:
        self.assertIn('display_name: "\u8d39\u66fc\u5b66\u4e60"', UI_TEXT)
        self.assertIn("$feynman", UI_TEXT)
        self.assertIn("\u5c0f\u56fe", UI_TEXT)

    def test_skill_stays_within_context_budget(self) -> None:
        self.assertLess(len(SKILL_TEXT.splitlines()), 500)

    def test_publication_files_are_utf8_without_bom(self) -> None:
        for path in (SKILL_DIR / "SKILL.md", SKILL_DIR / "agents" / "openai.yaml", Path(__file__)):
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), path)
            raw.decode("utf-8")


if __name__ == "__main__":
    unittest.main()
