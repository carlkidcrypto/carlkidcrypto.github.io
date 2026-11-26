.. meta::
   :description: Maintaining a single open source repository requires a handful of GitHub Actions workflows for linting, unit testing, and package publishing. However, once...
   :keywords: Github-Actions, Cicd, Shared-Workflows, Python, Nodejs, Devops, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Standardizing Multi-Repo CI/CD with Reusable GitHub Actions
   :property=og:description: Maintaining a single open source repository requires a handful of GitHub Actions workflows for linting, unit testing, and package publishing. However, once...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/shared-workflows-reusable-github-actions-cicd.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Standardizing Multi-Repo CI/CD with Reusable GitHub Actions
   :name=twitter:description: Maintaining a single open source repository requires a handful of GitHub Actions workflows for linting, unit testing, and package publishing. However, once...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

============================================================
Standardizing Multi-Repo CI/CD with Reusable GitHub Actions
============================================================

.. note::

   * **Published:** November 21, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 7 minutes
   * **Tags:** `Github-Actions` • `Cicd` • `Shared-Workflows` • `Python` • `Nodejs` • `Devops`

Maintaining a single open source repository requires a handful of GitHub Actions
workflows for linting, unit testing, and package publishing. However, once your
portfolio expands across six or more active repositories—spanning C++17 Python
extensions (`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_), Python data
pipelines (`purpleair_api <https://github.com/carlkidcrypto/purpleair_api>`_,
`ezsnmp_data_logger <https://github.com/carlkidcrypto/ezsnmp_data_logger>`_),
and TypeScript smart home plugins (`purpleair-matterbridge
<https://github.com/carlkidcrypto/purpleair-matterbridge>`_)—copy-pasting YAML
files across repositories creates severe maintenance drift.

Updating a pinned action version, tightening a security scanner, or adding a
new Python release target means opening six identical pull requests.

The `shared-workflows <https://github.com/carlkidcrypto/shared-workflows>`_
repository solves this by centralizing reusable GitHub Actions ``workflow_call``
templates and composite actions in one versioned source of truth. Downstream
repositories invoke battle-tested CI/CD pipelines with just a few lines of
YAML.

In this tutorial, we will examine the architecture of reusable
``workflow_call`` pipelines, design parameterized Python and Node.js CI
templates, manage secrets and permissions safely, and version shared workflows
using immutable release tags.

How Reusable ``workflow_call`` Pipelines Work
=============================================

GitHub Actions supports two primary mechanisms for sharing automation across
repositories:

- **Composite Actions (``action.yml``)**: Bundle a sequence of shell or setup
  steps that execute inside a caller's existing job. Ideal for repetitive
  environment setup (e.g., installing Net-SNMP headers or caching ``pip``).
- **Reusable Workflows (``on: workflow_call``)**: Encapsulate complete jobs,
  matrix strategies, runner selections, and artifact uploads. Caller
  repositories delegate entire test suites or PyPI/npm releases with a single
  ``uses:`` reference.

Centralizing CI logic in ``shared-workflows`` enforces uniform quality gates—
such as ``ruff``, ``black``, ``pytest``, and ``eslint``—across every project
automatically.

Designing a Parameterized Python CI Workflow
============================================

Below is a reusable workflow stored in
``.github/workflows/python-ci.yml`` inside ``shared-workflows``. It accepts
typed inputs for the Python matrix, optional system dependencies, and test
commands:

.. code-block:: yaml

    name: Reusable Python CI

    on:
      workflow_call:
        inputs:
          python-versions:
            description: "JSON array of Python versions to test"
            required: false
            type: string
            default: '["3.10", "3.11", "3.12"]'
          apt-packages:
            description: "Space-separated apt packages to install"
            required: false
            type: string
            default: ""
          pytest-args:
            description: "Extra arguments passed to pytest"
            required: false
            type: string
            default: "-v --tb=short"
        secrets:
          CODECOV_TOKEN:
            required: false

    jobs:
      lint-and-test:
        runs-on: ubuntu-latest
        strategy:
          fail-fast: false
          matrix:
            python-version: ${{ fromJSON(inputs.python-versions) }}

        steps:
          - name: Checkout caller repository
            uses: actions/checkout@v4

          - name: Install system dependencies
            if: inputs.apt-packages != ''
            run: |
              sudo apt-get update
              sudo apt-get install -y ${{ inputs.apt-packages }}

          - name: Set up Python ${{ matrix.python-version }}
            uses: actions/setup-python@v5
            with:
              python-version: ${{ matrix.python-version }}
              cache: "pip"

          - name: Install package and test dependencies
            run: |
              python -m pip install --upgrade pip
              pip install -e ".[dev,test]"

          - name: Run Ruff linter
            run: ruff check .

          - name: Run pytest suite
            run: pytest ${{ inputs.pytest-args }}

Notice the ``fromJSON(inputs.python-versions)`` pattern. Because
``workflow_call`` inputs do not natively accept YAML list types, passing a JSON
string lets each caller customize its Python matrix cleanly.

Calling the Shared Workflow from Downstream Repos
=================================================

In a downstream repository such as ``ezsnmp_data_logger`` or
``purpleair_api``, the entire CI configuration shrinks to a concise caller file
in ``.github/workflows/ci.yml``:

.. code-block:: yaml

    name: CI

    on:
      push:
        branches: [main]
      pull_request:
        branches: [main]

    permissions:
      contents: read

    jobs:
      ci:
        uses: carlkidcrypto/shared-workflows/.github/workflows/python-ci.yml@v1
        with:
          python-versions: '["3.11", "3.12", "3.13"]'
          apt-packages: "libsnmp-dev snmp"
          pytest-args: "-v --cov=ezsnmp_data_logger"
        secrets: inherit

Key security and architectural details in the caller:

1. **Least-Privilege ``permissions``**:

   - Declare ``contents: read`` explicitly at the workflow level so the
     ``GITHUB_TOKEN`` cannot mutate repository state during pull request runs.

2. **Explicit Secret Passing**:

   - Use ``secrets: inherit`` only for trusted internal repositories, or pass
     individual secrets explicitly when working with external contributors.

Versioning & Release Automation Best Practices
==============================================

Modifying a shared workflow on ``main`` immediately impacts every repository
that points to ``@main``. To prevent broken builds across your entire
portfolio:

1. **Pin Callers to Semantic Major Tags**:

   - Tag stable releases in ``shared-workflows`` (e.g., ``v1.2.0``) and move
     a floating major tag (``v1``) only after verifying backward compatibility.
   - Use ``@v2`` when introducing breaking input renames or dropping legacy
     Python versions.

2. **Centralize Trusted Publishing (OIDC)**:

   - For PyPI and npm releases, configure reusable release workflows using
     ``id-token: write`` OpenID Connect (OIDC) Trusted Publishing. This
     eliminates long-lived ``PYPI_API_TOKEN`` secrets across repositories.

3. **Lint Workflows with ``actionlint``**:

   - Run ``actionlint`` inside ``shared-workflows`` itself on every pull
     request to catch invalid expression syntax, mismatched input types, and
     deprecated runner images before downstream repos consume them.

Summary & What's Next
=====================

Centralizing CI/CD templates inside `shared-workflows
<https://github.com/carlkidcrypto/shared-workflows>`_ eliminates duplicated YAML
across Python, C++, and Node.js repositories while enforcing consistent
linting, testing, and security boundaries.

In our next blog post, we will rotate back to `purpleair_api
<https://github.com/carlkidcrypto/purpleair_api>`_, exploring automated sensor
health auditing to detect dual-channel optical drift and hardware degradation.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does
   review this, but we are only human.
