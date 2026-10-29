# Google Drive & Gemini Spark Agent Communication Protocol

This reference defines the bidirectional communication pattern between the **Gemini Spark Agent** and the repository publishing workflow via Google Drive.

---

## 1. Directory Structure on Google Drive

The Gemini Spark Agent and the repository skill share a root folder on Google Drive named `Blog/` (or `Gemini Spark Blog/`):

```text
Google Drive/
└── Blog/
    ├── Pending/
    │   ├── 2026-10-28-ezsnmp-performance-tuning.md
    │   └── ...
    ├── Processed/
    │   ├── 2026-10-16-ezsnmp-cross-platform-installation.rst
    │   ├── 2026-10-15-ezsnmp-high-throughput-multithreading.rst
    │   └── 2026-10-14-ezsnmp-snmpv3-deep-dive.rst
    └── Feedback/
        ├── 2026-10-16-ezsnmp-cross-platform-installation-feedback.md
        ├── 2026-10-15-ezsnmp-high-throughput-multithreading-feedback.md
        └── ...
```

---

## 2. Gemini Spark Agent Upload Specification (`Pending/`)

The Gemini Spark Agent runs on a recurring schedule (e.g. daily) and deposits a new draft into `Pending/`.

### Accepted Formats
- Markdown (`.md` or `.markdown`)
- reStructuredText (`.rst`)
- Plain text (`.txt`)
- Google Doc (exported to text/markdown)

### Recommended Frontmatter / Header in Drafts
```yaml
---
title: "Article Title"
tags: ["Python", "SNMP", "ezsnmp", "Performance"]
target_repo: "carlkidcrypto/ezsnmp"
reading_time_minutes: 5
summary: "Teaser summary for search engines and blog cards."
---
```

---

## 3. Detecting & Ingesting Drafts

When running the skill:
1. Search local Google Drive mount locations:
   - `~/Library/CloudStorage/GoogleDrive-*/My Drive/Blog/Pending/`
   - `/Volumes/GoogleDrive/My Drive/Blog/Pending/`
   - Path in environment variable `$GOOGLE_DRIVE_BLOG_DIR/Pending/`
2. Pick the newest file in `Pending/`.
3. Parse the title, summary, tags, and body.
4. Transform into the standard Sphinx `.rst` format under `source/blog/<slug>.rst`.
5. Update `source/blog/index.rst`.

---

## 4. Talking Back to Gemini Spark Agent (`Feedback/`)

Once a post is ingested and a GitHub Pull Request is opened, the skill communicates back to the Gemini Spark Agent by:

### Step 1: Move Draft to `Processed/`
Move the file:
```bash
mv "Blog/Pending/<draft-name>" "Blog/Processed/<draft-name>"
```

### Step 2: Write Feedback Document to `Feedback/`
Create `Blog/Feedback/<slug>-feedback.md` (and optionally `<slug>-status.json`):

```markdown
# Blog Post Review & Publication Feedback

- **Original Draft**: `<draft-filename>`
- **Slug**: `<slug>`
- **Publication Target**: `source/blog/<slug>.rst`
- **GitHub PR**: [PR #<PR_ID>](https://github.com/carlkidcrypto/carlkidcrypto.github.io/pull/<PR_ID>)
- **Branch**: `feature/blog-<slug>`
- **Status**: `PR_CREATED` (or `MERGED` once merged to main)
- **Timestamp**: `2026-10-28T22:50:00Z`

## Changes Applied During Ingestion
- Converted markdown headings and code blocks to standard Sphinx reStructuredText format.
- Added SEO `.. meta::` tags and OpenGraph card metadata.
- Verified Furo theme compliance (ensured zero `.. contents::` directives).
- Verified code snippets with Python 3.12/3.13.

## Reviewer & Copilot Feedback (For Future Agent Prompts)
- Avoid referencing non-existent library attributes (e.g. `ezsnmp.version`).
- Emphasize process pools over raw threads for Net-SNMP due to shared C state.
- Ensure all installation instructions clarify binary wheels vs. source builds.

## Recommended Next Topics for Gemini Spark Agent
- PurpleAir API data logger real-time MQTT streaming.
- Dockerizing Python network pollers with lightweight Alpine vs Debian images.
- Migrating legacy Net-SNMP configuration files to modern SNMPv3 USM users.
```

### Step 3: Optional JSON Status
For programmatic consumption by the Gemini Spark Agent:
```json
{
  "slug": "ezsnmp-performance-tuning",
  "status": "PR_CREATED",
  "pr_url": "https://github.com/carlkidcrypto/carlkidcrypto.github.io/pull/19",
  "branch": "feature/blog-ezsnmp-performance-tuning",
  "timestamp": "2026-10-28T22:50:00Z",
  "published_date": "October 29, 2026",
  "corrections_made": [
    "Removed in-page table of contents for Furo theme compatibility",
    "Updated version lookup to importlib.metadata"
  ]
}
```

This feedback loop ensures the Gemini Spark Agent continuously adapts to repository requirements, theme constraints, and reviewer recommendations over time.
