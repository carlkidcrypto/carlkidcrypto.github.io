#!/usr/bin/env python3
"""Automatically stamp publication dates on blog posts on merge to main.

This script identifies newly added blog posts or posts marked as 'Pending' /
'Unreleased', and stamps them with the current UTC date (or a specified date)
both in the article file itself and in source/blog/index.rst.

Usage:
    python3 .github/scripts/stamp_blog_dates.py --auto
    python3 .github/scripts/stamp_blog_dates.py --slug ezsnmp-getting-started-guide --date "October 14, 2026"
    python3 .github/scripts/stamp_blog_dates.py --auto --dry-run
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
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


def get_current_date_formatted() -> str:
    """Return today's date formatted as 'Month Day, Year' (e.g. 'October 14, 2026')."""
    now = datetime.now(timezone.utc)
    return now.strftime("%B %d, %Y")


def get_added_or_modified_posts_from_git() -> list[Path]:
    """Find blog post files added in the latest git commit."""
    try:
        # Check files added in HEAD
        cmd = [
            "git",
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "--diff-filter=A",
            "-r",
            "HEAD",
        ]
        result = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=True
        )
        added_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        
        posts = []
        for f in added_files:
            path = REPO_ROOT / f
            if (
                path.parent == BLOG_DIR
                and path.name != "index.rst"
                and path.suffix in (".rst", ".md")
                and path.exists()
            ):
                posts.append(path)
        return posts
    except Exception as e:
        print(f"Warning: git diff-tree failed ({e}). Checking for pending posts by content.")
        return []


def get_pending_posts_by_content() -> list[Path]:
    """Find blog posts with 'Pending' or 'Unreleased' in their Published field."""
    pending = []
    if not BLOG_DIR.exists():
        return pending

    pending_pattern = re.compile(
        r'\*\s+\*\*Published:\*\*\s*(Pending|Unreleased|TODO|Draft)',
        re.IGNORECASE,
    )

    for path in BLOG_DIR.glob("*"):
        if path.name == "index.rst" or path.suffix not in (".rst", ".md"):
            continue
        try:
            content = path.read_text(encoding="utf-8")
            if pending_pattern.search(content):
                pending.append(path)
        except OSError:
            pass
    return pending


def stamp_post_file(path: Path, new_date: str, dry_run: bool = False) -> bool:
    """Update the Published date in the blog post file."""
    try:
        original = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Error reading {path}: {e}")
        return False

    # Matches '* **Published:** <anything up to end of line>'
    post_pattern = re.compile(r'(\*\s+\*\*Published:\*\*)\s+[^\n]+')
    if not post_pattern.search(original):
        print(f"  Note: No '* **Published:**' pattern found in {path.name}")
        return False

    updated = post_pattern.sub(rf'\1 {new_date}', original)
    if updated == original:
        print(f"  {path.name} already has date '{new_date}'")
        return False

    if dry_run:
        print(f"  [DRY-RUN] Would update {path.name} to Published: {new_date}")
    else:
        path.write_text(updated, encoding="utf-8")
        print(f"  Updated {path.name} -> Published: {new_date}")
    return True


def stamp_index_file(slug: str, new_date: str, dry_run: bool = False) -> bool:
    """Update the date badge in the card corresponding to slug in source/blog/index.rst."""
    if not INDEX_FILE.exists():
        print(f"Index file {INDEX_FILE} not found.")
        return False

    try:
        original = INDEX_FILE.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Error reading index file: {e}")
        return False

    # Match the card referencing the slug and its 📅 *<date>* badge
    card_pattern = re.compile(
        rf'(:link:\s+{re.escape(slug)}\b[\s\S]*?📅\s+\*)([^*]+)(\*)'
    )
    if not card_pattern.search(original):
        print(f"  Note: No card for slug '{slug}' with '📅 *date*' found in index.rst")
        return False

    updated = card_pattern.sub(rf'\g<1>{new_date}\g<3>', original)
    if updated == original:
        print(f"  index.rst card for '{slug}' already up to date")
        return False

    if dry_run:
        print(f"  [DRY-RUN] Would update index.rst card for '{slug}' to '{new_date}'")
    else:
        INDEX_FILE.write_text(updated, encoding="utf-8")
        print(f"  Updated index.rst card for '{slug}' -> {new_date}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stamp publication date on blog posts on merge to main."
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically detect added posts from latest git commit or 'Pending' placeholders.",
    )
    parser.add_argument(
        "--slug",
        type=str,
        help="Specific post slug to stamp (without extension).",
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date string to stamp (defaults to current UTC date, e.g. 'October 14, 2026').",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to disk.",
    )
    args = parser.parse_args(argv)

    date_to_stamp = args.date or get_current_date_formatted()

    posts_to_process: set[Path] = set()

    if args.slug:
        post_path = BLOG_DIR / f"{args.slug}.rst"
        if not post_path.exists():
            post_path = BLOG_DIR / f"{args.slug}.md"
        if not post_path.exists():
            print(f"Error: Could not find post file for slug '{args.slug}' under {BLOG_DIR}")
            return 1
        posts_to_process.add(post_path)

    if args.auto:
        # Check newly added files in git commit
        git_added = get_added_or_modified_posts_from_git()
        posts_to_process.update(git_added)

        # Also check any posts with Pending/Unreleased placeholders
        pending = get_pending_posts_by_content()
        posts_to_process.update(pending)

    if not posts_to_process:
        print("No blog posts to stamp.")
        return 0

    print(f"Stamping date '{date_to_stamp}' on {len(posts_to_process)} post(s)...")
    modified = False

    for post_path in sorted(posts_to_process):
        slug = post_path.stem
        post_modified = stamp_post_file(post_path, date_to_stamp, dry_run=args.dry_run)
        index_modified = stamp_index_file(slug, date_to_stamp, dry_run=args.dry_run)
        if post_modified or index_modified:
            modified = True

    if modified:
        print("All date stamps applied successfully.")
    else:
        print("No file changes required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
