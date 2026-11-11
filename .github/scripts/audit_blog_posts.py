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
    index_content = (
        INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else ""
    )

    post_files = [
        f
        for f in sorted(BLOG_DIR.glob("*"))
        if f.name != "index.rst" and f.suffix in (".rst", ".md")
    ]

    print(f"Auditing {len(post_files)} blog post(s) in {BLOG_DIR}...")

    for post in post_files:
        content = post.read_text(encoding="utf-8")
        slug = post.stem

        # Rule 1: No '.. contents::' in Furo documentation
        if re.search(r"^\s*\.\.\s+contents::", content, re.MULTILINE):
            errors.append(
                f"[{post.name}] Found '.. contents::' directive. "
                "Furo theme generates the sidebar table of contents automatically. "
                "In-page '.. contents::' triggers Furo's red theme error banner and must be removed."
            )

        # Rule 2: Metadata block validation
        if not re.search(r"\*\s+\*\*Published:\*\*", content):
            errors.append(
                f"[{post.name}] Missing '* **Published:**' in metadata block."
            )

        if not re.search(r"\*\s+\*\*Authors:\*\*", content):
            errors.append(f"[{post.name}] Missing '* **Authors:**' in metadata block.")

        # Rule 3: Registration in index.rst
        if not re.search(rf"\b{re.escape(slug)}\b", index_content):
            errors.append(
                f"[{post.name}] Slug '{slug}' is not registered in source/blog/index.rst (toctree or grid card)."
            )

        # Rule 4: Code block syntax and ezsnmp API compliance
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from validate_blog_code import validate_post

            code_issues = validate_post(post, run_tests=True)
            for iss in code_issues:
                if iss.severity == "ERROR":
                    errors.append(
                        f"[{post.name}:Line {iss.line_number}] Code validation error: {iss.message}"
                    )
        except Exception as exc:
            errors.append(
                f"[{post.name}] Validator execution failed: {type(exc).__name__}: {exc}"
            )

        # Rule 5: Mandatory AI disclaimer footer
        if not re.search(
            r"\.\.\s+warning::\s*\n\s+.*(?:misinformation|mistakes)",
            content,
            re.IGNORECASE,
        ):
            errors.append(
                f"[{post.name}] Missing AI disclaimer footer ('.. warning:: AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.')."
            )

        # Rule 6: Prohibit legacy EasySNMP* exception names in ezsnmp architecture, diagrams, or code
        for line_no, line in enumerate(content.splitlines(), start=1):
            if re.search(r"\bEasySNMP\w*Error\b", line):
                # Allow strictly in migration comparison tables (lines starting with '- ``EasySNMP')
                # or comments showing legacy code ('# from easysnmp import' / '# Legacy easysnmp')
                s_line = line.strip()
                if (
                    s_line.startswith("- ``EasySNMP")
                    or s_line.startswith("# from easysnmp")
                    or s_line.startswith("# Legacy easysnmp")
                ):
                    continue
                errors.append(
                    f"[{post.name}:Line {line_no}] Invalid legacy exception in '{line.strip()}'. "
                    f"ezsnmp does NOT prefix exceptions with 'EasySNMP' (e.g. 'EasySNMPUndeterminedTypeError' does not exist). "
                    f"Use the modern exception from ezsnmp.exceptions (e.g. 'UndeterminedTypeError', 'GenericError', 'TimeoutError')."
                )

        # Rule 7: Verify example scripts extraction and download links
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from validate_blog_code import extract_code_blocks

            py_blocks = [
                b
                for b in extract_code_blocks(post)
                if b.language == "python"
                and len(b.code.splitlines()) >= 4
                and any(
                    kw in b.code
                    for kw in ["import ", "def ", "class ", "Session(", "PurpleAir"]
                )
            ]
            if py_blocks:
                script_dir = REPO_ROOT / "example_scripts" / slug
                if not script_dir.exists() or not list(script_dir.glob("*.py")):
                    errors.append(
                        f"[{post.name}] Missing example_scripts directory: {script_dir}. "
                        "Run 'python3 .github/scripts/validate_blog_code.py --save-examples' to extract scripts."
                    )
                if not re.search(
                    r"📥\s+`Download this script:\s*[^<]+<https://raw\.githubusercontent\.com/[^>]+/example_scripts/",
                    content,
                ):
                    errors.append(
                        f"[{post.name}] Missing script download link under example code blocks. "
                        "Run 'python3 .github/scripts/validate_blog_code.py --save-examples' to add download links."
                    )
        except Exception as exc:
            errors.append(
                f"[{post.name}] Example script audit failed: {type(exc).__name__}: {exc}"
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
