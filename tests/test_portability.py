from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "feynman"


class PortableSkillTests(unittest.TestCase):
    def test_frontmatter_uses_only_portable_required_fields(self) -> None:
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"---\n(.*?)\n---", text, re.DOTALL)
        self.assertIsNotNone(match)
        keys = {
            line.split(":", 1)[0].strip()
            for line in match.group(1).splitlines()
            if line.strip() and not line.startswith((" ", "\t"))
        }
        self.assertEqual(keys, {"name", "description"})

    def test_portable_archive_has_skill_at_root(self) -> None:
        script = ROOT / "scripts" / "package_skill.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "feynman-skill-portable.zip"
            subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--source",
                    str(SKILL_DIR),
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            with zipfile.ZipFile(output) as archive:
                names = sorted(archive.namelist())
                self.assertEqual(
                    names,
                    [
                        "SKILL.md",
                        "assets/medical/immune-organs.svg",
                        "references/chart-spec.md",
                        "references/math-figures.md",
                        "references/medical-concepts.md",
                        "references/mindmaps.md",
                        "references/visual-hints.md",
                        "scripts/render_chart.py",
                        "scripts/render_math_figure.py",
                        "scripts/render_mindmap.py",
                    ],
                )
                self.assertNotIn("__pycache__", " ".join(names))
                self.assertFalse(any(name.startswith("agents/") for name in names))

    def test_codex_archive_can_include_ui_metadata(self) -> None:
        script = ROOT / "scripts" / "package_skill.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "feynman-skill-codex.zip"
            subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--source",
                    str(SKILL_DIR),
                    "--output",
                    str(output),
                    "--include-codex-metadata",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    [
                        "SKILL.md",
                        "agents/openai.yaml",
                        "assets/medical/immune-organs.svg",
                        "references/chart-spec.md",
                        "references/math-figures.md",
                        "references/medical-concepts.md",
                        "references/mindmaps.md",
                        "references/visual-hints.md",
                        "scripts/render_chart.py",
                        "scripts/render_math_figure.py",
                        "scripts/render_mindmap.py",
                    ],
                )

    def test_domestic_agent_project_installers(self) -> None:
        script = ROOT / "scripts" / "install_skill.py"
        expected_roots = {
            "workbuddy": Path(".workbuddy") / "skills",
            "deepseek-harness": Path(".dsh") / "skills",
            "zcode": Path(".zcode") / "skills",
            "kimi": Path(".kimi") / "skills",
            "codebuddy": Path(".codebuddy") / "skills",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            for host, relative_root in expected_roots.items():
                with self.subTest(host=host):
                    project = Path(temp_dir) / host
                    project.mkdir()
                    subprocess.run(
                        [
                            sys.executable,
                            str(script),
                            host,
                            "--scope",
                            "project",
                            "--project-dir",
                            str(project),
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    target = project / relative_root / "feynman"
                    self.assertTrue((target / "SKILL.md").is_file())
                    self.assertTrue(
                        (target / "references" / "visual-hints.md").is_file()
                    )
                    self.assertTrue(
                        (target / "references" / "chart-spec.md").is_file()
                    )
                    self.assertTrue(
                        (target / "references" / "medical-concepts.md").is_file()
                    )
                    self.assertTrue(
                        (target / "references" / "mindmaps.md").is_file()
                    )
                    self.assertTrue(
                        (
                            target
                            / "assets"
                            / "medical"
                            / "immune-organs.svg"
                        ).is_file()
                    )
                    self.assertTrue(
                        (target / "scripts" / "render_chart.py").is_file()
                    )
                    self.assertTrue(
                        (target / "scripts" / "render_math_figure.py").is_file()
                    )
                    self.assertTrue(
                        (target / "scripts" / "render_mindmap.py").is_file()
                    )
                    self.assertFalse((target / "agents" / "openai.yaml").exists())

    def test_installer_refuses_overwrite_without_force(self) -> None:
        script = ROOT / "scripts" / "install_skill.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            command = [
                sys.executable,
                str(script),
                "codebuddy",
                "--scope",
                "project",
                "--project-dir",
                str(project),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--force", result.stderr)


if __name__ == "__main__":
    unittest.main()
