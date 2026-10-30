# Google Drive & Gemini Spark Agent Communication Protocol

This reference defines the bidirectional communication pattern between the **Gemini Spark Agent** and the repository publishing workflow via Google Drive.

---

## 1. Directory Structure on Google Drive

The Gemini Spark Agent and the repository skill share a root folder on Google Drive named **`Auto Blog Posts/`**:

```text
Google Drive/
└── Auto Blog Posts/
    ├── ezsnmp Blog Topic Tracker.gdoc                 # Master topic tracker & agenda
    ├── ezsnmp_getting_started_guide.rst               # Draft uploaded by Gemini Spark
    ├── ezsnmp_getting_started_guide - POSTED.rst      # Feedback marker posted by repository workflow
    ├── ezsnmp_snmpv3_deep_dive.rst
    ├── ezsnmp_snmpv3_deep_dive - POSTED.rst
    ├── ezsnmp_high_throughput_multithreading.rst
    ├── ezsnmp_high_throughput_multithreading - POSTED.rst
    ├── ezsnmp_cross_platform_installation_troubleshooting.rst
    ├── ezsnmp_cross_platform_installation_troubleshooting - POSTED.rst
    ├── ezsnmp_working_with_mibs_guide.rst             # PENDING (unprocessed)
    ├── ezsnmp_async_polling_event_loops.rst           # PENDING (unprocessed)
    └── ...
```

### Local macOS Sync Paths
Google Drive for Desktop synchronizes this directory locally at:
1. `~/Library/CloudStorage/GoogleDrive-<email>/My Drive/Auto Blog Posts`
2. `/Volumes/GoogleDrive/My Drive/Auto Blog Posts`
3. Custom path defined via `$GOOGLE_DRIVE_BLOG_DIR`

---

## 2. Gemini Spark Agent Upload Specification

The Gemini Spark Agent runs on a recurring schedule (daily) and uploads a new reStructuredText (`.rst`) draft into `Auto Blog Posts/`.

### File Naming Convention
- Prefix: `ezsnmp_`
- Topic Slug: lowercase words separated by underscores (`_`)
- Extension: `.rst`
- Example: `ezsnmp_working_with_mibs_guide.rst`

### Draft Header Structure
Each draft includes an overline/underline title, field list metadata, and a table of contents directive:

```rst
==============================================================
<Article Title>
==============================================================

:Date: YYYY-MM-DD
:Author: Written by Gemini 3.8 Flash
:Co-Author: Carlos Santos
:Estimated Reading Time: 5 minutes
:Category: Python, Networking, SNMP
:Tags: python, snmp, mibs, net-snmp, ezsnmp, network-monitoring

.. contents:: Table of Contents
   :depth: 2
   :local:

<Article Body...>
```

---

## 3. Detecting Pending Drafts

A draft is considered **PENDING** if:
`ezsnmp_<topic>.rst` exists **WITHOUT** a corresponding `ezsnmp_<topic> - POSTED.rst` marker in `Auto Blog Posts/`.

To inspect all drafts programmatically:
```bash
python3 .agents/skills/gemini-spark-blog/scripts/sync_drive_post.py --list
```

---

## 4. Ingesting & Formatting Drafts for Sphinx / Furo

When ingesting a draft into `carlkidcrypto.github.io`:

1. **Convert File Slug**:
   Replace underscores `_` with hyphens `-`:
   `ezsnmp_working_with_mibs_guide.rst` -> `source/blog/ezsnmp-working-with-mibs-guide.rst`

2. **Add SEO & OpenGraph Metadata**:
   Generate an opening `.. meta::` directive containing `:description:`, `:keywords:`, `:author:`, OpenGraph (`og:`), and Twitter card metadata.

3. **Format Title**:
   Ensure title overline and underline match the length of the title line.

4. **Convert Metadata to Furo Theme Note Box**:
   Remove the raw `:Date:`, `:Author:`, `:Tags:`, etc., and replace with:
   ```rst
   .. note::

      * **Published:** <Month Day, Year>
      * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
      * **Estimated Reading Time:** <N> minutes
      * **Tags:** `Tag1` • `Tag2` • `Tag3`
   ```

5. **Strip `.. contents::`**:
   The **Furo** theme renders the table of contents in the right sidebar automatically.
   **Crucial Rule**: Remove any `.. contents::` directives and their options (`:depth:`, `:local:`); otherwise, Furo displays a red error banner and repository audit scripts will fail.

6. **Register in `source/blog/index.rst`**:
   - Add the slug under `.. toctree::` (newest posts at top).
   - Add a `.. grid-item-card::` under `All Posts` with emoji, title, teaser summary, date, reading time, and tags.

Use the helper script to perform steps 1–6 automatically:
```bash
python3 .agents/skills/gemini-spark-blog/scripts/sync_drive_post.py --ingest ezsnmp_working_with_mibs_guide.rst
```

---

## 5. Talking Back to the Gemini Spark Agent (`- POSTED.rst`)

Once a draft is audited, verified, and a GitHub Pull Request is opened, communicate status back to the Gemini Spark Agent by creating a `<draft_stem> - POSTED.rst` marker file directly in `Auto Blog Posts/`.

### Feedback File Format
Create `Auto Blog Posts/<draft_stem> - POSTED.rst`:

```rst
================================================================================
<draft_stem> - POSTED
================================================================================

This blog post has been audited, verified, and submitted for publication.

Review & Pull Request
---------------------
* PR: https://github.com/carlkidcrypto/carlkidcrypto.github.io/pull/<PR_ID>
* Review Status: All code snippets 100% verified against local daemon
* CI Status: Audit passed (0 errors) & Sphinx build passing (0 warnings)

Publication Target
------------------
* Published Date: <Month Day, Year>
* Site URL: https://carlkidcrypto.github.io/blog/<slug>.html
* Repository Path: source/blog/<slug>.rst
* Merge Date Automation: Automated via .github/scripts/stamp_blog_dates.py on merge to main
```

Use the helper script to create this marker automatically:
```bash
python3 .agents/skills/gemini-spark-blog/scripts/sync_drive_post.py \
  --mark-posted ezsnmp_working_with_mibs_guide.rst \
  --pr https://github.com/carlkidcrypto/carlkidcrypto.github.io/pull/<PR_ID> \
  --review-status "All code snippets 100% verified against local daemon"
```

---

## 6. The Master Topic Tracker (`ezsnmp Blog Topic Tracker.gdoc`)

The Google Doc **`ezsnmp Blog Topic Tracker.gdoc`** (`doc_id: 1DPS_bQRZrWZ5GueoiltqldvqHm0frbUX4OtOxVv1tsw`) serves as the master planning agenda.

- **Purpose**: Tracks proposed titles, topic status, technical areas covered (e.g., MIBs, SNMPv3, concurrency, telemetry), and upcoming post schedules.
- **Accessing via Antigravity**: Use the official Google Docs plugin (`antigravity-plugins-official/plugin/gdocs`) or inspect local Google Drive sync state.
