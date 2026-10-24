from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "feynman"
SKILL_NAME = "feynman"

TARGETS = {
    "workbuddy": {
        "user": Path(".workbuddy") / "skills",
        "project": Path(".workbuddy") / "skills",
        "codex_metadata": False,
    },
    "deepseek-harness": {
        "user": Path(".dsh") / "skills",
        "project": Path(".dsh") / "skills",
        "codex_metadata": False,
    },
    "codebuddy": {
        "user": Path(".codebuddy") / "skills",
        "project": Path(".codebuddy") / "skills",
        "codex_metadata": False,
    },
    "agents": {
        "user": Path(".agents") / "skills",
        "project": Path(".agents") / "skills",
        "codex_metadata": False,
    },
    "codex": {
        "user": Path(".codex") / "skills",
        "project": Path(".agents") / "skills",
        "codex_metadata": True,
    },
}


def resolve_target(host: str, scope: str, project_dir: Path) -> Path:
    config = TARGETS[host]
    base = Path.home() if scope == "user" else project_dir.resolve()
    return base / config[scope] / SKILL_NAME


def copy_skill(
    source: Path,
    target: Path,
    *,
    include_codex_metadata: bool,
    force: bool,
) -> Path:
    source = source.resolve()
    target = target.resolve()
    if not (source / "SKILL.md").is_file():
        raise FileNotFoundError(f"SKILL.md not found under {source}")
    if source == target:
        raise ValueError("Source and installation target must differ")
    if target.exists() and not force:
        raise FileExistsError(
            f"Target already exists: {target}. Re-run with --force to replace it."
        )

    ignored_names = {"__pycache__", ".DS_Store"}
    ignored_suffixes = {".pyc", ".pyo"}

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {
            name
            for name in names
            if name in ignored_names or Path(name).suffix in ignored_suffixes
        }
        if Path(directory).resolve() == source and not include_codex_metadata:
            ignored.add("agents")
        return ignored

    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=target.parent,
        prefix=f".{SKILL_NAME}-install-",
    ) as temp_dir:
        staged = Path(temp_dir) / SKILL_NAME
        shutil.copytree(source, staged, ignore=ignore)
        for path in staged.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"Refusing to install symbolic link: {path}")

        if target.exists():
            if target.name != SKILL_NAME:
                raise ValueError(f"Refusing to replace unexpected target: {target}")
            shutil.rmtree(target)
        os.replace(staged, target)

    return target


def install(host: str, scope: str, project_dir: Path, source: Path, force: bool) -> Path:
    config = TARGETS[host]
    target = resolve_target(host, scope, project_dir)
    return copy_skill(
        source,
        target,
        include_codex_metadata=bool(config["codex_metadata"]),
        force=force,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the Feynman Skill for a supported Agent host."
    )
    parser.add_argument("host", nargs="?", choices=sorted(TARGETS))
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--list", action="store_true", help="List supported hosts.")
    args = parser.parse_args()
    if not args.list and args.host is None:
        parser.error("host is required unless --list is used")
    return args


def main() -> None:
    args = parse_args()
    if args.list:
        for host, config in sorted(TARGETS.items()):
            print(f"{host}: {config['user']}")
        return

    target = install(
        args.host,
        args.scope,
        args.project_dir,
        args.source,
        args.force,
    )
    print(target)


if __name__ == "__main__":
    main()
