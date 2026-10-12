"""Create deterministic, intentionally unconfigured project profiles.

Project scaffolding is an operator-side configuration operation; benchmark
executor models never receive filesystem or repository access.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "projects" / "_template"


def _substitute(value, slug: str, name: str):
    if isinstance(value, str):
        return value.replace("__PROJECT_SLUG__", slug).replace("__PROJECT_NAME__", name)
    if isinstance(value, list):
        return [_substitute(item, slug, name) for item in value]
    if isinstance(value, dict):
        return {key: _substitute(item, slug, name) for key, item in value.items()}
    return value


def create_project(projects_dir: Path, slug: str, name: str | None = None) -> Path:
    """Copy the blank, versioned profile without overwriting an existing project.

    The same slug/name and template produce byte-identical files. Generated
    placeholders intentionally cannot pass scenario preflight until configured.
    """
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", slug) or slug.endswith("-"):
        raise ValueError("Project slug must be lower-case letters/digits/hyphens, start with a letter, and not end with a hyphen")
    name = name or slug
    if not name.strip() or len(name) > 100 or "\n" in name or "\r" in name:
        raise ValueError("Project name must be a nonempty single line of up to 100 characters")
    projects_dir = Path(projects_dir)
    destination = projects_dir / slug
    if destination.exists():
        raise FileExistsError(f"Project already exists: {destination}")
    if not TEMPLATE_ROOT.is_dir():
        raise FileNotFoundError(f"Missing scaffold template: {TEMPLATE_ROOT}")
    projects_dir.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".sqbf-new-project-", dir=projects_dir))
    try:
        for source in sorted(TEMPLATE_ROOT.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(TEMPLATE_ROOT)
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.suffix == ".json":
                document = json.loads(source.read_text(encoding="utf-8"))
                rendered = _substitute(document, slug, name)
                target.write_text(json.dumps(rendered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            else:
                rendered = _substitute(source.read_text(encoding="utf-8"), slug, name)
                target.write_text(rendered, encoding="utf-8")
        if destination.exists():
            raise FileExistsError(f"Project already exists: {destination}")
        temporary.rename(destination)
        return destination
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
