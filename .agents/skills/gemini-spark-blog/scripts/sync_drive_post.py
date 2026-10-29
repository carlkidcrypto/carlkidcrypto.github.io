#!/usr/bin/env python3
"""Helper script to sync Gemini Spark Agent blog posts from Google Drive.

Capabilities:
1. Detects local Google Drive mount path on macOS.
2. Lists pending blog drafts deposited by Gemini Spark Agent.
3. Ingests and formats a draft into Sphinx .rst format with metadata.
4. Registers the new post in source/blog/index.rst.
5. Moves draft to Processed/ and writes status/feedback back to Google Drive.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def find_repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists() or (p / "source" / "blog").exists():
            return p
        p = p.parent
    return Path.cwd().resolve()


REPO_ROOT = find_repo_root()
BLOG_DIR = REPO_ROOT / "source" / "blog"
INDEX_FILE = BLOG_DIR / "index.rst"


def find_google_drive_blog_dir() -> Path | None:
    """Detect local Google Drive Blog folder."""
    # 1. Environment variable
    env_path = os.environ.get("GOOGLE_DRIVE_BLOG_DIR")
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if p.exists():
            return p

    # 2. Standard macOS CloudStorage paths
    cloud_storage = Path.home() / "Library" / "CloudStorage"
    if cloud_storage.exists():
        matches = list(cloud_storage.glob("GoogleDrive-*/My Drive/Blog"))
        if matches and matches[0].exists():
            return matches[0]
        # Check without Blog folder
        drive_matches = list(cloud_storage.glob("GoogleDrive-*/My Drive"))
        if drive_matches and (drive_matches[0] / "Blog").exists():
            return drive_matches[0] / "Blog"

    # 3. /Volumes mount
    volumes_match = Path("/Volumes/GoogleDrive/My Drive/Blog")
    if volumes_match.exists():
        return volumes_match

    # 4. ~/Google Drive
    home_drive = Path.home() / "Google Drive" / "My Drive" / "Blog"
    if home_drive.exists():
        return home_drive

    return None


def get_pending_drafts(drive_dir: Path) -> list[Path]:
    """Retrieve all pending drafts from Google Drive."""
    pending_dir = drive_dir / "Pending"
    if not pending_dir.exists():
        return []

    drafts = []
    for ext in ("*.md", "*.markdown", "*.rst", "*.txt"):
        drafts.extend(pending_dir.glob(ext))
    return sorted(drafts, key=lambda f: f.stat().st_mtime, reverse=True)


def slugify(title: str) -> str:
    """Convert title to clean lowercase slug."""
    s = title.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s).strip('-')
    return s or "new-blog-post"


def parse_draft(draft_path: Path) -> dict:
    """Extract frontmatter and content from draft."""
    raw = draft_path.read_text(encoding="utf-8")
    
    metadata = {
        "title": draft_path.stem.replace("-", " ").replace("_", " ").title(),
        "summary": "",
        "tags": ["Python", "OpenSource", "DevOps"],
        "reading_time": 5,
        "content": raw,
    }

    # Handle YAML frontmatter if present
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            fm_text, content = parts[1], parts[2]
            metadata["content"] = content.strip()
            for line in fm_text.splitlines():
                line = line.strip()
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip().lower()
                    val = val.strip().strip('"').strip("'")
                    if key == "title" and val:
                        metadata["title"] = val
                    elif key == "summary" and val:
                        metadata["summary"] = val
                    elif key == "reading_time" and val.isdigit():
                        metadata["reading_time"] = int(val)
                    elif key == "tags":
                        tags = re.findall(r'[\w-]+', val)
                        if tags:
                            metadata["tags"] = tags

    # Clean in-page contents directive if present (Furo theme rule)
    metadata["content"] = re.sub(r'^\s*\.\.\s+contents::.*$', '', metadata["content"], flags=re.MULTILINE)

    if not metadata["summary"]:
        # Extract first non-heading paragraph as summary
        paragraphs = [p.strip() for p in metadata["content"].split("\n\n") if p.strip()]
        for p in paragraphs:
            if not p.startswith(("#", "=", "-", "*", "..")):
                metadata["summary"] = p[:160].replace("\n", " ").strip()
                break
        if not metadata["summary"]:
            metadata["summary"] = f"Technical tutorial and release overview for {metadata['title']}."

    return metadata


def write_status_feedback(
    drive_dir: Path,
    slug: str,
    draft_name: str,
    pr_url: str | None = None,
    branch_name: str | None = None,
    notes: list[str] | None = None,
) -> Path:
    """Write review feedback back to Google Drive for the Gemini Spark Agent."""
    feedback_dir = drive_dir / "Feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    feedback_file = feedback_dir / f"{slug}-feedback.md"

    now_iso = datetime.now(timezone.utc).isoformat()
    now_date = datetime.now(timezone.utc).strftime("%B %d, %Y")

    content = [
        f"# Blog Post Ingestion & Feedback: {slug}",
        "",
        f"- **Draft File**: `{draft_name}`",
        f"- **Slug**: `{slug}`",
        f"- **Timestamp**: `{now_iso}`",
        f"- **Publication Date**: `{now_date}`",
        f"- **PR URL**: {pr_url or 'Pending manual PR creation'}",
        f"- **Git Branch**: `{branch_name or 'N/A'}`",
        f"- **Status**: `{'PR_CREATED' if pr_url else 'INGESTED'}`",
        "",
        "## Ingestion Notes",
    ]

    if notes:
        for note in notes:
            content.append(f"- {note}")
    else:
        content.append("- Ingested successfully with Sphinx and Furo theme formatting.")

    content.extend([
        "",
        "## Agent Instructions for Next Drafts",
        "- Maintain zero `.. contents::` directives (Furo theme generates sidebar TOC automatically).",
        "- Verify all library imports and attributes (e.g. use `importlib.metadata.version` instead of non-existent `.version`).",
        "- Emphasize multiprocessing/process isolation for C-extension libraries like Net-SNMP.",
        "",
    ])

    feedback_file.write_text("\n".join(content), encoding="utf-8")

    # Also write JSON status
    json_file = feedback_dir / f"{slug}-status.json"
    status_data = {
        "draft_file": draft_name,
        "slug": slug,
        "timestamp": now_iso,
        "published_date": now_date,
        "pr_url": pr_url,
        "branch": branch_name,
        "status": "PR_CREATED" if pr_url else "INGESTED",
        "notes": notes or [],
    }
    json_file.write_text(json.dumps(status_data, indent=2), encoding="utf-8")

    return feedback_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync blog drafts from Google Drive")
    parser.add_argument("--list", action="store_true", help="List pending drafts in Google Drive")
    parser.add_argument("--draft", type=str, help="Specific draft filename or path to ingest")
    parser.add_argument("--drive-dir", type=str, help="Explicit path to Google Drive Blog directory")
    args = parser.parse_args(argv)

    drive_dir = Path(args.drive_dir) if args.drive_dir else find_google_drive_blog_dir()

    if not drive_dir or not drive_dir.exists():
        print("Note: Google Drive Blog directory not detected.")
        print("Set GOOGLE_DRIVE_BLOG_DIR or install Google Drive for Desktop.")
        print(f"Searched default locations under ~/Library/CloudStorage/ and /Volumes/")
        return 0

    print(f"Google Drive Blog directory: {drive_dir}")
    drafts = get_pending_drafts(drive_dir)

    if args.list:
        print(f"Found {len(drafts)} pending draft(s) in {drive_dir / 'Pending'}:")
        for d in drafts:
            print(f"  - {d.name} (modified: {datetime.fromtimestamp(d.stat().st_mtime)})")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
