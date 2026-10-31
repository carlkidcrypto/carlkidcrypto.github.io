# Blog Post Format & Style Guide for carlkidcrypto.github.io

This reference details the exact syntax, metadata standards, and theme rules required for all blog posts on [carlkidcrypto.github.io](https://carlkidcrypto.github.io).

---

## 1. File Naming and Placement

- **Directory**: `source/blog/`
- **Filename**: `<slug>.rst` (or `<slug>.md` if authored in MyST Markdown).
- **Slug convention**: Lowercase, hyphen-delimited, descriptive of the topic.
  - *Good*: `ezsnmp-cross-platform-installation-troubleshooting.rst`
  - *Good*: `ezsnmp-high-throughput-multithreading.rst`
  - *Avoid*: `post1.rst`, `blog_oct28.rst`

---

## 2. Complete reStructuredText Template

```rst
.. meta::
   :description: <1-2 sentence search engine description, ~150 chars>
   :keywords: <Comma-separated keywords for SEO>
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: <Post Title>
   :property=og:description: <1-2 sentence search engine description>
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/<slug>.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: <Post Title>
   :name=twitter:description: <1-2 sentence search engine description>
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

==============================================================
<Post Title with Overline and Underline Matching Length>
==============================================================

.. note::

   * **Published:** <Month Day, Year>
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** <N> minutes
   * **Tags:** `Tag1` • `Tag2` • `Tag3`

<Section Heading 1>
===================

Opening introduction explaining why the topic matters, the technical context,
and who benefits from reading this guide.

<Subsection Heading>
--------------------

Detailed walkthrough with code snippets, terminal commands, or architecture diagrams.

.. code-block:: python

    from importlib.metadata import version
    from ezsnmp import Session

    print(f"ezsnmp version: {version('ezsnmp')}")

    with Session(hostname="localhost", community="public", version=2) as session:
        system_descr = session.get("sysDescr.0")
        print(system_descr[0].value)

Useful Links & Community
========================

* **Source Repository**: `carlkidcrypto/<repo> on GitHub <https://github.com/carlkidcrypto/<repo>>`_
* **PyPI Distribution**: `<package> on PyPI <https://pypi.org/project/<package>/>`_
* **Documentation**: `Official Documentation <https://carlkidcrypto.github.io/<repo>/>`_
* **Blog Index**: `Carlos Santos Blog Updates <https://carlkidcrypto.github.io/blog/>`_
```

---

## 3. Strict Furo Theme Compliance Rules

### A. Zero In-Page Table of Contents (`.. contents::`)
The **Furo** theme dynamically renders the document's section hierarchy in the right sidebar under the heading **"On this page"**.
If a blog post includes an explicit `.. contents::` directive:
- Furo will display a prominent red error banner: *"Secondary sidebar contents already rendered"*.
- The automated repository check in `.github/scripts/audit_blog_posts.py` will reject the commit.

### B. Headings Hierarchy
Docutils requires consistent adornment characters across the file. Use:
1. Document Title: Overline and Underline with `=` (`===...===`)
2. H1 Section: Underline with `=` (`===...===`)
3. H2 Subsection: Underline with `-` (`---...---`)
4. H3 Sub-subsection: Underline with `~` (`~~~...~~~`)

### C. Reading Time Calculation
Estimate reading time at approximately 200–250 words per minute plus 1 minute per complex code sample.

---

## 4. `source/blog/index.rst` Registration Pattern

Each new post must be registered in two places in `source/blog/index.rst`:

### A. Toctree (Navigation hierarchy)
Add the slug at the top of the `Articles:` toctree:
```rst
.. toctree::
   :maxdepth: 1
   :caption: Articles:

   <new-slug>
   <previous-slug-1>
   <previous-slug-2>
```

### B. Responsive Grid Card
Add a `.. grid-item-card::` under the `All Posts` section:
```rst
   .. grid-item-card:: <Emoji> <Title>
      :link: <new-slug>
      :link-type: doc

      <Teaser summary highlighting key takeaways and real-world utility.>

      +++
      📅 *<Month Day, Year>* • ⏱️ *<N> min read* • `<Tag1>` `<Tag2>` `<Tag3>`
```

---

## 5. Technical Accuracy Checklist

Before publishing, verify against the common issues identified in Copilot/human reviews:

- **Library Versioning**: Do not call `ezsnmp.version` (attribute does not exist). Use `from importlib.metadata import version; version('ezsnmp')`.
- **Concurrency Models**: Clarify that Net-SNMP C library maintains global C state, so multi-processing (`ProcessPoolExecutor`) provides thread-safe process isolation, whereas high-concurrency multi-threading (>4 threads) can risk race conditions.
- **Packaging & Builds**: When explaining C-extensions, distinguish between pre-built binary wheels (which bundle compiled DLLs on Windows) versus source distributions (`sdist`), which require SWIG and compilers.
- **Code Snippet Reproducibility**: All code samples should be syntactically valid and runnable against real or mock endpoints.
