.. meta::
   :description: Containerize purpleair_data_logger with multi-architecture Docker Buildx images, non-root security, persistent volumes, and healthchecks for Raspberry Pi and NAS systems.
   :keywords: PurpleAir, Docker, Raspberry-Pi, ARM64, IoT, Data-Logger, Open-Source, Python, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Containerized Edge Deployments: Multi-Architecture Docker Builds for Raspberry Pi & NAS Systems
   :property=og:description: Containerize purpleair_data_logger with multi-architecture Docker Buildx images, non-root security, persistent volumes, and healthchecks for Raspberry Pi and NAS systems.
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/purpleair-data-logger-multiarch-docker-edge.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Containerized Edge Deployments: Multi-Architecture Docker Builds for Raspberry Pi & NAS Systems
   :name=twitter:description: Containerize purpleair_data_logger with multi-architecture Docker Buildx images, non-root security, persistent volumes, and healthchecks for Raspberry Pi and NAS systems.
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

===============================================================================================
Containerized Edge Deployments: Multi-Architecture Docker Builds for Raspberry Pi & NAS Systems
===============================================================================================

.. note::

   * **Published:** November 17, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Purpleair` • `Docker` • `Raspberry-Pi` • `Arm64` • `Iot` • `Data-Logger` • `Open-Source`

Eliminating Configuration Drift on Edge Hardware
================================================

Running `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_ (published on PyPI
as `purpleair-data-logger
<https://pypi.org/project/purpleair-data-logger/>`_) directly on a Raspberry
Pi, Synology NAS, or industrial Linux gateway is ideal for continuous local
air quality monitoring. However, managing Python virtual environments, OS-level
database drivers, and systemd units across heterogeneous hardware quickly
introduces configuration drift.

Containerizing your telemetry collector with Docker eliminates host dependency
conflicts and guarantees identical runtime behavior whether you deploy on an
``x86_64`` (``amd64``) rack server or a low-power ``ARM64`` (``aarch64``)
Raspberry Pi.

In this tutorial, we will author a minimal multi-stage ``Dockerfile``, build
multi-architecture images with ``docker buildx``, configure persistent volumes
and healthchecks in ``docker-compose.yml``, and enforce non-root container
security.

Minimal Alpine & Multi-Stage Dockerfile
=======================================

Using a slim Python base image keeps edge container footprints small—crucial
when deploying over cellular links or onto flash-backed gateways. When building
with ``psycopg2-binary`` or SQLite, a clean ``python:3.12-slim`` image avoids
heavy compilation toolchains:

.. code-block:: dockerfile

    # Dockerfile
    FROM python:3.12-slim

    # Prevent Python from writing .pyc files and buffering stdout
    ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1

    # Create non-root user for secure edge execution
    RUN groupadd -r logger && useradd -r -g logger logger

    WORKDIR /app

    # Install purpleair-data-logger and database drivers
    RUN pip install --no-cache-dir \
        purpleair-data-logger \
        psycopg2-binary

    # Copy polling entrypoint script
    COPY --chown=logger:logger entrypoint.py /app/entrypoint.py

    # Create persistent data directory
    RUN mkdir -p /data && chown -R logger:logger /data

    USER logger

    HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
        CMD python -c "import os, time; \
        assert time.time() - os.path.getmtime('/data/heartbeat') < 180"

    ENTRYPOINT ["python", "/app/entrypoint.py"]

The ``HEALTHCHECK`` instruction monitors a lightweight ``/data/heartbeat``
timestamp file touched after every successful poll cycle. If the collector
hangs on a stalled socket, Docker marks the container ``unhealthy`` so external
watchdogs can restart it cleanly.

Building Multi-Architecture Images with Buildx
==============================================

Developers typically author containers on ``amd64`` laptops before deploying
to ``arm64`` Raspberry Pi boards. Docker Buildx cross-compiles and pushes a
single manifest list supporting both architectures:

.. code-block:: bash

    # Initialize a multi-architecture builder instance
    docker buildx create --name edge-builder --use
    docker buildx inspect --bootstrap

    # Build and push unified amd64 + arm64 manifest
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        -t ghcr.io/youruser/purpleair-edge-logger:latest \
        --push .

When you run ``docker pull`` on either a Synology NAS or a Raspberry Pi 5, the
Docker daemon automatically selects the matching native binary layer.

Production Docker Compose Stack
===============================

Below is a complete ``docker-compose.yml`` configuration pairing the edge
collector with persistent local storage, log rotation, and automatic restarts:

.. code-block:: yaml

    services:
      purpleair-logger:
        image: ghcr.io/youruser/purpleair-edge-logger:latest
        container_name: purpleair-edge-logger
        restart: unless-stopped
        environment:
          - LOCAL_SENSOR_IPS=192.168.1.150,192.168.1.151
          - POLL_INTERVAL_SECONDS=60
          - DATA_DIR=/data
        volumes:
          - ./edge-data:/data
        logging:
          driver: "json-file"
          options:
            max-size: "10m"
            max-file: "3"

Edge Deployment Best Practices
==============================

When operating containerized telemetry loggers on SD cards or NAS arrays:

1. **Cap Container Log Size**: Always set ``max-size`` and ``max-file`` on the
   ``json-file`` logging driver. Unbounded container logs can fill small root
   partitions on Raspberry Pi OS within months.
2. **Use Bind Mounts or Named Volumes**: Never store SQLite databases or CSV
   archives inside the writable container layer. Bind-mounting ``./edge-data``
   preserves historical records across image upgrades.
3. **Run Read-Only Where Possible**: Combine non-root execution
   (``USER logger``) with explicit volume mounts so compromised dependencies
   cannot alter system binaries.

Summary & What's Next
=====================

Containerizing `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_ with multi-arch
Docker builds standardizes deployments across Raspberry Pi nodes, NAS boxes,
and cloud servers while adding automated health monitoring and log safety.

In our next blog post, we will rotate to `purpleair-matterbridge
<https://github.com/carlkidcrypto/purpleair-matterbridge>`_, exploring real-time
WebSocket telemetry streams and event-driven cluster updates for sub-second
smart home responsiveness.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

