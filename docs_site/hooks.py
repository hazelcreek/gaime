"""
Build hook to stage documentation sources into docs_site before MkDocs runs.

This copies:
- repo README.md -> docs_site/project-readme.md
- docs/ -> docs_site/docs/
- planning/ -> docs_site/planning/
- ideas/ -> docs_site/ideas/

Content is refreshed on each build/serve to keep pages in sync with source.
"""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "docs_site"


def _copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def sync_docs(config) -> None:  # noqa: D401
    """Hook: copy source markdown into docs_site before build."""
    _copy_tree(ROOT / "docs", DEST / "docs")
    _copy_tree(ROOT / "planning", DEST / "planning")
    _copy_tree(ROOT / "ideas", DEST / "ideas")

    readme_dest = DEST / "project-readme.md"
    shutil.copyfile(ROOT / "README.md", readme_dest)
