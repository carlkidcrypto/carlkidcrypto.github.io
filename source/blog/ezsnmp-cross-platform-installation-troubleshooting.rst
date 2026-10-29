.. meta::
   :description: Comprehensive installation and troubleshooting guide for ezsnmp across Windows, macOS, Linux distributions, and Docker. Master C++17 build prerequisites, Net-SNMP headers, and self-contained wheels.
   :keywords: Python, SNMP, ezsnmp, Net-SNMP, Installation, Troubleshooting, macOS Homebrew, Windows Wheels, Docker, Linux, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Cross-Platform Installation & Troubleshooting ezsnmp Builds
   :property=og:description: Comprehensive installation and troubleshooting guide for ezsnmp across Windows, macOS, Linux distributions, and Docker. Master C++17 build prerequisites, Net-SNMP headers, and self-contained wheels.
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-cross-platform-installation-troubleshooting.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Cross-Platform Installation & Troubleshooting ezsnmp Builds
   :name=twitter:description: Comprehensive installation and troubleshooting guide for ezsnmp across Windows, macOS, Linux distributions, and Docker. Master C++17 build prerequisites, Net-SNMP headers, and self-contained wheels.
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

==============================================================
Cross-Platform Installation & Troubleshooting ezsnmp Builds
==============================================================

.. note::

   * **Published:** October 16, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 6 minutes
   * **Tags:** `Python` • `Networking` • `DevOps` • `ezsnmp` • `Packaging` • `Troubleshooting`

Why C-Extension Builds Fail
===========================

Because `ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ interfaces directly
with the compiled Net-SNMP C runtime (versions 5.7 through 5.10) for maximum
polling performance, building the package from source requires C/C++
development headers, OpenSSL libraries, and compiler toolchains.

When developers run ``pip install ezsnmp`` in an unconfigured environment, build
failures typically trace back to one of four common issues:

* **Missing net-snmp-config Utility**: On Unix-like systems, the build script
  relies on ``net-snmp-config`` to inspect system compiler flags and library paths.
* **Missing C/C++ Header Files**: The compiler fails when core development
  headers such as ``net-snmp/net-snmp-config.h``, ``openssl/evp.h``, or
  ``Python.h`` cannot be resolved.
* **Linker Path Misconfigurations**: On macOS, tools installed via Homebrew
  live under architecture-specific prefixes (such as ``/opt/homebrew`` on Apple
  Silicon) that compilers do not always search by default.
* **Missing SWIG for Raw Git Clones**: Developers building directly from a raw
  GitHub repository clone require SWIG 4.x to generate C++ wrappers from interface
  files (standard PyPI sdist releases bundle these pre-generated).

Below is a complete installation walkthrough and diagnostic guide across Windows,
macOS, Linux, and containerized Docker environments.


Platform-Specific Installation Walkthroughs
===========================================

1. Windows: Self-Contained Binary Wheels
----------------------------------------

Historically, compiling C-based Net-SNMP wrappers on Windows was notoriously
difficult, requiring complex MSYS2 or MinGW setups.

**ezsnmp eliminates this overhead.** The project builds and publishes pre-compiled
binary wheels on PyPI using ``cibuildwheel``. These wheels bundle
``netsnmp.dll`` alongside its core Windows runtime dependencies (``advapi32``,
``ws2_32``, ``kernel32``, ``user32``) for:

* **AMD64 (x86_64)**
* **x86 (32-bit)**
* **ARM64**

On Windows, installation requires only ``pip``:

.. code-block:: powershell

    py -m pip install ezsnmp

No Visual Studio C++ compiler or external Net-SNMP installation is required for
standard wheel installs.

.. note::

   **Compiling from Source on Windows**: If you must build from source on
   Windows, install a Net-SNMP build compatible with MSVC and supply the include
   and library locations via environment variables recognized by ``build_utils.py``:
   ``EZSNMP_NETSNMP_INCLUDE_DIR``, ``EZSNMP_NETSNMP_LIB_DIR``,
   ``EZSNMP_OPENSSL_INCLUDE_DIR``, and ``EZSNMP_OPENSSL_LIB_DIR``.

2. macOS: Homebrew & Compiler Paths
-----------------------------------

On macOS (both Apple Silicon and Intel), Homebrew installs Net-SNMP into
architecture-specific prefixes (``/opt/homebrew`` for ARM64 and ``/usr/local``
for Intel).

ezsnmp explicitly rejects legacy system Net-SNMP 5.6.x (which lacks modern SNMPv3
and C++ features). Always use modern Net-SNMP (5.7+):

Option A: Dedicated Homebrew Tap (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The easiest way to install ezsnmp on macOS is via the official Homebrew tap,
which provisions the Python package and compiled C dependencies together:

.. code-block:: bash

    brew tap carlkidcrypto/ezsnmp
    brew install carlkidcrypto/ezsnmp/ezsnmp

If ``import ezsnmp`` fails after installation, run ``brew info ezsnmp`` and
follow its version-specific ``PYTHONPATH`` caveat in your shell profile
(``~/.zshrc``). Use the same Python major/minor version reported by the formula;
the compiled extension cannot be loaded by a different Python ABI.

Option B: Compiling into a Virtualenv via pip
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When installing ezsnmp inside a project virtual environment (e.g., ``venv``,
``pyenv``, or Poetry), install Net-SNMP and OpenSSL via Homebrew, then export the
required compiler and linker flags:

.. code-block:: bash

    # 1. Install required Net-SNMP and OpenSSL libraries
    brew install net-snmp openssl@3

    # 2. Export flags so clang resolves headers and libraries
    export LDFLAGS="-L$(brew --prefix net-snmp)/lib -L$(brew --prefix openssl@3)/lib"
    export CPPFLAGS="-I$(brew --prefix net-snmp)/include -I$(brew --prefix openssl@3)/include"
    export PATH="$(brew --prefix net-snmp)/bin:$PATH"

    # 3. Install ezsnmp
    pip install ezsnmp

3. Linux: Distribution Packages
-------------------------------

Linux distributions require development headers and a C++17 compiler before
building from source.

Debian / Ubuntu:
~~~~~~~~~~~~~~~~

.. code-block:: bash

    sudo apt update
    sudo apt install -y \
        build-essential \
        libsnmp-dev \
        libssl-dev \
        python3-dev \
        snmp-mibs-downloader
    pip install ezsnmp

Red Hat Enterprise Linux / Rocky / Fedora:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    sudo dnf install -y \
        gcc-c++ \
        make \
        net-snmp-devel \
        openssl-devel \
        python3-devel
    pip install ezsnmp

Alpine Linux (Musl Libc):
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sh

    apk add --no-cache \
        gcc \
        g++ \
        make \
        net-snmp-dev \
        openssl-dev \
        python3-dev
    pip install ezsnmp


Verifying Your Installation
===========================

Once installed, verify that the compiled C-extension and Net-SNMP engine link
properly by executing a quick check in Python:

.. code-block:: python

    import ezsnmp
    from ezsnmp import Session

    print(f"ezsnmp version: {ezsnmp.__version__}")

    # Query local daemon or test agent
    with Session(hostname="localhost", community="public", version=2) as session:
        (sys_descr,) = session.get("sysDescr.0")
        print(f"Connected: {sys_descr.value}")


Diagnostic Cheat Sheet: Common Error Signatures
===============================================

Error 1: "net-snmp-config: command not found"
---------------------------------------------
* **Cause**: Net-SNMP development binaries are missing from the system or not
  exported to ``$PATH``.
* **Fix**: Install ``libsnmp-dev`` (Ubuntu) or ``net-snmp-devel`` (RHEL). On
  macOS, add ``$(brew --prefix net-snmp)/bin`` to your ``$PATH``.

Error 2: "fatal error: net-snmp/net-snmp-config.h: No such file"
----------------------------------------------------------------
* **Cause**: The compiler cannot find Net-SNMP C include headers.
* **Fix**: Check the output of ``net-snmp-config --cflags`` in your terminal to
  verify the include directory, and pass ``CPPFLAGS`` to pip accordingly.

Error 3: "ld: library not found for -lnetsnmp"
----------------------------------------------
* **Cause**: The linker cannot locate ``libnetsnmp.so`` or ``libnetsnmp.dylib``.
* **Fix**: On Linux, run ``sudo ldconfig`` after installing libraries. On macOS,
  ensure ``LDFLAGS="-L$(brew --prefix net-snmp)/lib"`` is exported.

Error 4: "Cannot find -lcrypto" or OpenSSL Symbols Missing
----------------------------------------------------------
* **Cause**: Net-SNMP USM encryption routines require OpenSSL development
  libraries.
* **Fix**: Install ``libssl-dev`` (Ubuntu) or ``openssl-devel`` (RHEL/Fedora).

Error 5: Stale Build Artifacts & Corrupted Imports
--------------------------------------------------
* **Symptom**: ``ModuleNotFoundError: No module named 'ezsnmp.datatypes'`` or
  broken extension symbols.
* **Fix**: Lingering artifacts from previous partial builds can confuse pip.
  Clear build directories and force a clean reinstall:

  .. code-block:: bash

      rm -rf build/ ezsnmp.egg-info/
      pip install --force-reinstall --no-binary :all: ezsnmp

Error 6: Building from Raw Git Repository Clone
-----------------------------------------------
* **Symptom**: ``RuntimeError: SWIG failed for ezsnmp/interface/datatypes.i. Ensure SWIG is installed and on PATH.``
* **Cause**: Building from a raw ``git clone`` runs SWIG to generate C++ code
  from interface files (``.i``).
* **Fix**: Install SWIG 4.x (``sudo apt install swig`` or ``brew install swig``).
  Note: When installing via PyPI wheels or source tarballs (``sdist``), SWIG is
  not required because the C++ wrappers are pre-generated.


Best Practices for Docker Deployments
=====================================

When building containerized microservices or telemetry pollers, use multi-stage
Docker builds. This keeps production images lean while providing full
C-compilation toolchains during the build phase:

.. code-block:: dockerfile

    # Build stage
    FROM python:3.12-slim AS builder
    RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libsnmp-dev \
        libssl-dev \
        python3-dev && \
        rm -rf /var/lib/apt/lists/*
    RUN pip install --no-cache-dir --user ezsnmp

    # Final runtime stage
    FROM python:3.12-slim
    RUN apt-get update && apt-get install -y --no-install-recommends \
        libsnmp40 \
        libssl3 && \
        rm -rf /var/lib/apt/lists/*
    COPY --from=builder /root/.local /root/.local
    ENV PATH=/root/.local/bin:$PATH


Migration Notes: Build Reliability vs Legacy Easy SNMP
======================================================

Legacy ``easysnmp`` suffered from abandoned build tooling that consistently
broke on modern systems:

* **Modern setuptools & C++17**: ``ezsnmp`` replaces deprecated distutils
  constructs with modern setuptools build hooks and strict C++17 compliance.
* **Compiler Hardening**: Resolved GCC 11–14 and Clang 14+ warning-as-error
  failures, modernizing C++ type casts and memory cleanup.
* **Pre-Built Windows Wheels**: Solved the longstanding barrier for Windows
  developers by shipping pre-built wheels bundling Net-SNMP DLLs directly on PyPI.


Useful Links & Community
========================

* **Source Repository**: `carlkidcrypto/ezsnmp on GitHub <https://github.com/carlkidcrypto/ezsnmp>`_
* **PyPI Distribution**: `ezsnmp Package on PyPI <https://pypi.org/project/ezsnmp/>`_
* **Documentation**: `ezsnmp Online Documentation <https://carlkidcrypto.github.io/ezsnmp/>`_
* **Blog Index**: `Carlos Santos Blog Updates <https://carlkidcrypto.github.io/blog/>`_
