# carlkidcrypto.github.io

Personal website and developer portfolio for Carlos ([@carlkidcrypto](https://github.com/carlkidcrypto)), built with [Sphinx](https://www.sphinx-doc.org/), [Furo](https://pradyunsg.me/furo/), and [sphinx-design](https://sphinx-design.readthedocs.io/).

Styled to match the look and feel of [@carlkidcrypto](https://github.com/carlkidcrypto)'s open source projects ([ezsnmp](https://github.com/carlkidcrypto/ezsnmp), [purpleair_api](https://github.com/carlkidcrypto/purpleair_api), [purpleair_data_logger](https://github.com/carlkidcrypto/purpleair_data_logger), [purpleair-matterbridge](https://github.com/carlkidcrypto/purpleair-matterbridge), and [os-specific-runner](https://github.com/carlkidcrypto/os-specific-runner)).

Hosted on GitHub Pages at [https://carlkidcrypto.github.io](https://carlkidcrypto.github.io).

## Features

- **Furo Theme:** Clean, modern developer documentation theme with light and dark mode support, matching the ecosystem's visual identity.
- **Single Sphinx Project:** Unified single-project configuration (`conf.py` under `source/`).
- **sphinx-design Cards:** Responsive project grids, skill badges, and article cards styled in reStructuredText (`.rst`).
- **MyST-Parser:** Full support for authoring content in both `.rst` and standard Markdown (`.md`).
- **Automated CI/CD:** GitHub Actions workflow builds and deploys directly to GitHub Pages on push to `main`.
- **Dependabot:** Weekly dependency updates for GitHub Actions and Python requirements.

## Local Development

### Prerequisites

- Python 3.10+
- `pip`

### Setup & Build

1. Clone the repository:
   ```bash
   git clone https://github.com/carlkidcrypto/carlkidcrypto.github.io.git
   cd carlkidcrypto.github.io
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

4. Build the site:
   ```bash
   make html
   ```

5. View the output by opening `_build/html/index.html` in your web browser.

## Adding a Blog Post

Create a new `.rst` or `.md` file under `source/blog/` (e.g. `source/blog/my-new-post.rst`):

```rst
My Post Title
=============

*Published on October 10, 2026 by Carlos (@carlkidcrypto)*

----

First paragraph of the post...
```

Add the post filename (without extension) to the `toctree` and card grid in `source/blog/index.rst`.
