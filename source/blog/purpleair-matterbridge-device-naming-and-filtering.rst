.. meta::
   :description: When you first deploy `purpleair-matterbridge <https://github.com/carlkidcrypto/purpleair-matterbridge>`_ in a smart home environment, exposing every...
   :keywords: Purpleair, Matter, Matterbridge, Smart-Home, Filtering, Iot, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Customizing Matter Bridge Device Naming & Sensor Filtering
   :property=og:description: When you first deploy `purpleair-matterbridge <https://github.com/carlkidcrypto/purpleair-matterbridge>`_ in a smart home environment, exposing every...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/purpleair-matterbridge-device-naming-and-filtering.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Customizing Matter Bridge Device Naming & Sensor Filtering
   :name=twitter:description: When you first deploy `purpleair-matterbridge <https://github.com/carlkidcrypto/purpleair-matterbridge>`_ in a smart home environment, exposing every...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

============================================================
Customizing Matter Bridge Device Naming & Sensor Filtering
============================================================

.. note::

   * **Published:** November 24, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 7 minutes
   * **Tags:** `Purpleair` • `Matter` • `Matterbridge` • `Smart-Home` • `Filtering` • `Iot`

When you first deploy `purpleair-matterbridge
<https://github.com/carlkidcrypto/purpleair-matterbridge>`_ in a smart home
environment, exposing every discovered PurpleAir sensor works well for a
single backyard monitor. However, once your telemetry feed tracks multiple
indoor units, outdoor sensors, and neighborhood stations, uncurated device
discovery quickly clutters Apple Home, Google Home, and Home Assistant.

Without explicit device filtering and deterministic naming rules:

- **Duplicate or Cryptic Names**: Generic names like ``PurpleAir Sensor``
  collide across rooms, making voice commands ("Hey Siri, what is the air
  quality?") ambiguous.
- **Unwanted Neighborhood Stations**: Bounding-box or group feeds may include
  external sensors that should not trigger your home ERV or purifier
  automations.
- **Fabric Identity Churn**: Renaming a bridged node carelessly can cause
  Matter controllers to treat it as a brand-new accessory, breaking existing
  rooms and automations.

In this tutorial, we will configure ``whiteList`` and ``blackList`` filtering
in Matterbridge, enforce deterministic MAC-based and postfix device naming,
and preserve stable Matter node identities across container restarts.

How Matterbridge Device Filtering Works
=======================================

`Matterbridge <https://github.com/Luligu/matterbridge>`_ plugins evaluate
device selection rules before registering bridged endpoints onto the Matter
server node. Understanding the evaluation order prevents surprises when
combining inclusion and exclusion lists:

1. **Allowlist Evaluation (``whiteList``)**:

   - When ``whiteList`` is empty (``[]``), all discovered sensors from the
     PurpleAir feed are eligible for bridging.
   - When ``whiteList`` contains one or more entries, *only* sensors matching
     an entry in ``whiteList`` are exposed to Matter controllers.

2. **Blocklist Evaluation (``blackList``)**:

   - Any sensor matching ``blackList`` is excluded, even if it also appears in
     ``whiteList`` or matches a broader feed filter.
   - Use ``blackList`` to suppress offline test units, noisy indoor kitchen
     monitors, or third-party neighborhood stations.

Configuring Allowlists and Blocklists
=====================================

You can manage filtering directly in the Matterbridge web UI or inside your
plugin configuration JSON (e.g., ``purpleair-matterbridge.config.json``):

.. code-block:: json

    {
      "name": "purpleair-matterbridge",
      "type": "DynamicPlatform",
      "feedUrl": "http://127.0.0.1:9855/matter/sensors",
      "pollIntervalSeconds": 30,
      "whiteList": [
        "purple-air-84-a1-4b",
        "purple-air-9c-2e-10"
      ],
      "blackList": [
        "purple-air-de-ad-01"
      ],
      "unregisterOnShutdown": false,
      "logLevel": "info"
    }

Notice ``"unregisterOnShutdown": false``. Keeping this disabled ensures that
temporary container restarts or Docker image upgrades do not instruct Apple
Home or Home Assistant to delete your paired sensor tiles and automations.

Deterministic MAC-Based Naming & Unique IDs
===========================================

In Matterbridge, every bridged device requires two distinct identifiers:

- **``deviceName`` (Display Name)**: The human-friendly label shown in Apple
  Home or Google Home (for example, ``Backyard Air Quality``).
- **``serialNumber`` / ``uniqueId``**: The immutable hardware identifier used
  by Matter controllers to track the device across reboots.

PurpleAir LAN sensors expose their Wi-Fi MAC address in ``/json`` payloads,
while cloud sensors expose a permanent ``sensor_index``. Deriving
``uniqueId`` from the MAC address or ``sensor_index``—never from a mutable
display label—lets you safely rename rooms or labels without losing controller
history.

Implementing Custom Naming & Filtering in TypeScript
----------------------------------------------------

Below is a clean TypeScript helper illustrating how a Matterbridge plugin
applies deterministic naming, ``namePostfix`` collision avoidance, and
allow/block filtering before calling ``registerDevice()``:

.. code-block:: typescript

    export interface SensorRecord {
      sensor_index: number;
      mac_address?: string;
      name: string;
    }

    export interface FilterConfig {
      whiteList: string[];
      blackList: string[];
      namePostfix?: string;
    }

    export function buildDeterministicName(
      sensor: SensorRecord,
      postfix = ""
    ): string {
      const macSuffix = sensor.mac_address
        ? sensor.mac_address.toLowerCase().replace(/:/g, "-").slice(-8)
        : String(sensor.sensor_index);

      const baseName = sensor.name?.trim() || `purple-air-${macSuffix}`;
      return postfix ? `${baseName} ${postfix}` : baseName;
    }

    export function shouldExposeSensor(
      sensor: SensorRecord,
      displayName: string,
      cfg: FilterConfig
    ): boolean {
      const identifiers = new Set([
        displayName,
        sensor.name,
        String(sensor.sensor_index),
        sensor.mac_address ?? "",
      ]);

      const inBlackList = cfg.blackList.some((entry) =>
        identifiers.has(entry)
      );
      if (inBlackList) {
        return false;
      }

      if (cfg.whiteList.length > 0) {
        return cfg.whiteList.some((entry) => identifiers.has(entry));
      }

      return true;
    }

Multi-Instance Postfixing & Docker Persistence
==============================================

If you run multiple Matterbridge instances on the same LAN (for example, one
dedicated child bridge for outdoor monitors and another for indoor sensors):

1. **Set ``namePostfix``**:

   - Configure a distinct ``namePostfix`` (such as ``(Outdoor)``) so mDNS
     advertisements and Matter ``BridgedDeviceBasicInformation`` serial
     numbers never collide across instances.

2. **Preserve ``network_mode: host`` and Volumes**:

   - Always run Docker with ``network_mode: host`` so mDNS (UDP port 5353) and
     IPv6 neighbor discovery packets reach Apple Home and Home Assistant.
   - Persist ``/root/.matterbridge`` on a bind mount or named volume to retain
     fabric certificates and endpoint mappings across upgrades.

3. **Respect 32-Byte mDNS Name Limits**:

   - Keep bridged device names concise (under 32 UTF-8 bytes) so Matter
     commissionable advertisements and mobile controller UIs never truncate
     room identifiers.

Summary & What's Next
=====================

Combining ``whiteList``/``blackList`` filtering with deterministic MAC and
``sensor_index`` identifiers keeps `purpleair-matterbridge
<https://github.com/carlkidcrypto/purpleair-matterbridge>`_ clean, predictable,
and resilient across multi-sensor households.

In our next blog post, we will rotate to `ezsnmp
<https://github.com/carlkidcrypto/ezsnmp>`_, exploring how to audit Spanning
Tree Protocol (STP/RSTP) topology changes and root bridge stability across
campus switching fabrics using ``BRIDGE-MIB`` and ``Q-BRIDGE-MIB``.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does
   review this, but we are only human.
