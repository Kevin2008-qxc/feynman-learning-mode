from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "feynman"
DEFAULT_OUTPUT = ROOT / "dist" / "feynman-skill-portable.zip"
EXCLUDED_NAMES = {"__pycache__", ".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def build_skill_package(
    source: Path,
    output: Path,
    include_codex_metadata: bool = False,
) -> Path:
    source = source.resolve()
    output = output.resolve()
    skill_file = source / "SKILL.md"

    if not skill_file.is_file():
        raise FileNotFoundError(f"SKILL.md not found under {source}")
    if output == source or source in output.parents:
        raise ValueError("Output archive must be outside the Skill directory")

    files = sorted(
        path
        for path in source.rglob("*")
        if path.is_file()
        and not any(part in EXCLUDED_NAMES for part in path.parts)
        and path.suffix not in EXCLUDED_SUFFIXES
        and (
            include_codex_metadata
            or "agents" not in path.relative_to(source).parts
        )
    )
    for path in files:
        if path.is_symlink():
            raise ValueError(f"Refusing to package symbolic link: {path}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            archive.write(path, path.relative_to(source).as_posix())

    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a portable Agent Skill ZIP with SKILL.md at its root."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--include-codex-metadata",
        action="store_true",
        help="Include the optional agents/openai.yaml Codex UI metadata.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    archive = build_skill_package(
        args.source,
        args.output,
        include_codex_metadata=args.include_codex_metadata,
    )
    print(archive)


if __name__ == "__main__":
    main()
