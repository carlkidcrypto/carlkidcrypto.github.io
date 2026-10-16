#!/usr/bin/env python3
"""Audit blog posts for structural standards, SEO metadata, and theme compatibility.

Checks:
1. Rejects any '.. contents::' directives (Furo theme renders sidebar TOC automatically;
   in-page contents triggers Furo's red theme error banner).
2. Verifies required metadata block fields (* **Published:**, * **Authors:**, etc.).
3. Verifies registration in source/blog/index.rst.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

def find_repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists() or (p / "source" / "blog").exists():
            return p
        p = p.parent
    cwd = Path.cwd().resolve()
    if (cwd / ".git").exists() or (cwd / "source" / "blog").exists():
        return cwd
    return Path(__file__).resolve().parents[2]


REPO_ROOT = find_repo_root()
BLOG_DIR = REPO_ROOT / "source" / "blog"
INDEX_FILE = BLOG_DIR / "index.rst"


def audit_posts() -> int:
    if not BLOG_DIR.exists():
        print(f"Error: Blog directory not found at {BLOG_DIR}")
        return 1

    errors: list[str] = []
    index_content = INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else ""

    post_files = [
        f for f in sorted(BLOG_DIR.glob("*"))
        if f.name != "index.rst" and f.suffix in (".rst", ".md")
    ]

    print(f"Auditing {len(post_files)} blog post(s) in {BLOG_DIR}...")

    for post in post_files:
        content = post.read_text(encoding="utf-8")
        slug = post.stem

        # Rule 1: No '.. contents::' in Furo documentation
        if re.search(r'^\s*\.\.\s+contents::', content, re.MULTILINE):
            errors.append(
                f"[{post.name}] Found '.. contents::' directive. "
                "Furo theme generates the sidebar table of contents automatically. "
                "In-page '.. contents::' triggers Furo's red theme error banner and must be removed."
            )

        # Rule 2: Metadata block validation
        if not re.search(r'\*\s+\*\*Published:\*\*', content):
            errors.append(f"[{post.name}] Missing '* **Published:**' in metadata block.")

        if not re.search(r'\*\s+\*\*Authors:\*\*', content):
            errors.append(f"[{post.name}] Missing '* **Authors:**' in metadata block.")

        # Rule 3: Registration in index.rst
        if slug not in index_content:
            errors.append(
                f"[{post.name}] Slug '{slug}' is not registered in source/blog/index.rst (toctree or grid card)."
            )

    if errors:
        print("\n" + "=" * 60)
        print("BLOG POST AUDIT FAILED:")
        for err in errors:
            print(f"  ERROR: {err}")
        print("=" * 60 + "\n")
        return 1

    print("All blog posts passed audit successfully (0 errors).")
    return 0


if __name__ == "__main__":
    sys.exit(audit_posts())
