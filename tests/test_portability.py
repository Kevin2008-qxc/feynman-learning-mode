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

    def test_workbuddy_archive_has_skill_at_root(self) -> None:
        script = ROOT / "scripts" / "package_skill.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "feynman-skill.zip"
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
                    ["SKILL.md", "agents/openai.yaml"],
                )
                self.assertNotIn("__pycache__", " ".join(names))


if __name__ == "__main__":
    unittest.main()
