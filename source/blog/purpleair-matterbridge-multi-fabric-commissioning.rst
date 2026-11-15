.. meta::
   :description: Share a single purpleair-matterbridge instance concurrently across Apple Home and Google Home using Matter Multi-Admin and Enhanced Commissioning Windows.
   :keywords: PurpleAir, Matterbridge, Matter, Apple-Home, Google-Home, Multi-Fabric, Multi-Admin, Smart-Home
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Multi-Fabric Commissioning: Sharing PurpleAir Matterbridge with Apple Home and Google Home Concurrently
   :property=og:description: Share a single purpleair-matterbridge instance concurrently across Apple Home and Google Home using Matter Multi-Admin and Enhanced Commissioning Windows.
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/purpleair-matterbridge-multi-fabric-commissioning.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Multi-Fabric Commissioning: Sharing PurpleAir Matterbridge with Apple Home and Google Home Concurrently
   :name=twitter:description: Share a single purpleair-matterbridge instance concurrently across Apple Home and Google Home using Matter Multi-Admin and Enhanced Commissioning Windows.
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

=======================================================================================================
Multi-Fabric Commissioning: Sharing PurpleAir Matterbridge with Apple Home and Google Home Concurrently
=======================================================================================================

.. note::

   * **Published:** November 14, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `PurpleAir` • `Matterbridge` • `Matter` • `Apple-Home` • `Google-Home` • `Multi-Fabric`

Modern households rarely standardize on a single smart home ecosystem. One
family member might check outdoor air quality on an iPhone using Apple Home,
while another relies on Google Nest Hub displays in the kitchen or Home
Assistant dashboards on a local tablet.

Before Matter, supporting multiple platforms required running redundant
software bridges or relying on cloud-to-cloud connectors that introduced
latency and privacy trade-offs. Matter solves this natively through
**Multi-Admin** (also known as **Multi-Fabric Commissioning**).

With Multi-Admin, a single Matter node—such as `purpleair-matterbridge
<https://github.com/carlkidcrypto/purpleair-matterbridge>`_—can belong to
several independent cryptographic fabrics simultaneously. Each controller
communicates directly with the bridge over your local IPv6 network, receiving
real-time PM2.5, AQI, temperature, and humidity updates without a cloud relay.

In this tutorial, we will examine how Matter fabrics isolate credentials, walk
through pairing ``purpleair-matterbridge`` with Apple Home first, open an
Enhanced Commissioning Window to share the bridge with Google Home, and
troubleshoot multi-fabric mDNS and IPv6 networking.

How Matter Multi-Fabric Architecture Works
==========================================

In the Matter specification, a **Fabric** is an isolated security domain sharing
a common Root Certificate Authority (CA), Fabric ID, and operational keys.
Every smart home ecosystem you use maintains its own independent fabric:

- **Fabric 1 (Apple Home)**: Managed by your Apple TV 4K or HomePod hub.
- **Fabric 2 (Google Home)**: Managed by your Google Nest Hub or Nest Wifi
  Pro controller.
- **Fabric 3 (Home Assistant)**: Managed by your local ``python-matter-server``
  instance.

When you pair ``purpleair-matterbridge`` with multiple ecosystems, the bridge
does not duplicate physical hardware or spin up separate processes. Instead,
the underlying `Matterbridge <https://matterbridge.io/>`_ runtime stores
separate **Node Operational Credentials (NOCs)** and Access Control Lists
(ACLs) inside its persistent ``~/.matterbridge`` directory.

Each controller opens its own independent CASE (Certificate Authenticated
Session Establishment) subscription to the bridge. When PurpleAir telemetry
updates, ``purpleair-matterbridge`` broadcasts attribute change reports across
every active fabric subscription concurrently.

Prerequisites for Multi-Admin Operation
=======================================

Before commissioning a second or third controller, verify your local network
meets Matter's transport requirements:

1. **Local IPv6 Enabled**: Matter mandates IPv6 link-local (``fe80::/10``)
   and Unique Local Addressing (ULA) on the LAN. You do not need IPv6 from
   your ISP, but IPv6 must be enabled on your router and Docker host.
2. **Host Networking & mDNS**: If deploying via Docker, always use
   ``network_mode: host`` so multicast DNS (mDNS on UDP port 5353) packets
   reach every controller on the subnet.
3. **Persistent Storage**: Mount the ``/root/.matterbridge`` volume so fabric
   certificates and pairings survive container upgrades.

Step 1: Commission the Primary Fabric (Apple Home)
==================================================

Start ``purpleair-matterbridge`` and inspect the startup logs or web UI
(typically ``http://<host-ip>:8283``) to obtain the initial onboarding payload:

.. code-block:: bash

    docker logs -f purpleair-matterbridge

Look for the initial QR code and the 11-digit manual pairing code:

.. code-block:: text

    [Matterbridge] QR Code: MT:Y.K9042C00KA0648G00
    [Matterbridge] Manual Pairing Code: 3497-011-2983

Pair the bridge with your primary ecosystem first:

1. Open the **Apple Home** app on an iOS device on the same local Wi-Fi.
2. Tap **+** -> **Add Accessory** -> **More options...** -> **My Accessory
   Isn't Shown Here** (or scan the QR code directly).
3. Enter the 11-digit manual pairing code.
4. Assign the bridged PurpleAir sensors to their rooms.

Once paired, the initial commissioning window closes automatically. Attempting
to reuse the original printed QR code for Google Home will fail because the
device is now commissioned and locked to Fabric 1.

Step 2: Share to Google Home via Enhanced Commissioning
=======================================================

To add a second controller, the primary controller—or the bridge itself—must
invoke the **OpenCommissioningWindow** command (Cluster ``0x003C``,
Administrator Commissioning) to generate a fresh, time-limited ephemeral
passcode.

Option A: Share Directly from Apple Home
----------------------------------------

1. Open **Apple Home** and long-press the **PurpleAir Matterbridge** tile (or
   navigate to **Home Settings** -> **Home Hubs & Bridges**).
2. Select the bridge and tap **Turn On Pairing Mode**.
3. Apple Home instructs the bridge to open an Enhanced Commissioning Window
   (typically valid for 15 minutes) and displays a newly generated 11-digit
   setup code.
4. Open the **Google Home** app on your phone, tap **Devices** -> **Add** ->
   **Matter-enabled device** -> **Continue without scanning**, and enter the
   temporary pairing code generated by Apple Home.

Option B: Trigger Sharing from the Matterbridge Web UI
------------------------------------------------------

If your primary controller's mobile UI hides bridge sharing options, you can
open a fresh commissioning window directly from the Matterbridge frontend:

1. Navigate to ``http://<host-ip>:8283`` in your browser.
2. Click **Share** (or **Open Commissioning Window**) on the PurpleAir bridge
   card.
3. Matterbridge emits a new ephemeral QR code and 11-digit pairing code in
   the dashboard and logs.
4. Scan or enter that temporary code inside **Google Home** or **Home
   Assistant** before the window expires.

Inspecting Active Fabrics & Subscriptions
=========================================

You can verify that both Apple Home and Google Home hold active operational
credentials on the bridge by checking the Matterbridge web dashboard or
inspecting the console logs after a sensor poll cycle:

.. code-block:: text

    [Commissioning] Fabric 1: Apple Inc. (NodeID: 0x000000001A2B3C4D)
    [Commissioning] Fabric 2: Google LLC (NodeID: 0x000000009F8E7D6C)
    [AirQuality] Sensor 282168 updated: PM2.5=6.4 ug/m3 -> Notified 2 fabrics

Each fabric maintains isolated access control, meaning removing the bridge
from Google Home later only revokes Fabric 2's operational certificates while
leaving Apple Home uninterrupted.

Troubleshooting Multi-Admin Pitfalls
====================================

When sharing a bridge across multiple vendors, keep these operational rules in
mind:

1. **Avoid Overlapping Commissioning Windows**: Never trigger pairing mode on
   two controllers at the exact same moment. Wait until Fabric 2 completes
   PASE/CASE key exchange before opening another window for Fabric 3.
2. **Verify mDNS Across VLANs**: If your Apple TV and Google Nest Hub reside on
   different subnets or IoT VLANs, mDNS reflector rules must forward both
   ``_matter._tcp`` (commissioned operational discovery) and ``_matterc._udp``
   (commissionable discovery) records.
3. **Check Fabric Slot Limits**: Matter 1.x devices guarantee support for at
   least 5 concurrent fabrics. Matterbridge handles this comfortably, allowing
   simultaneous pairing across Apple Home, Google Home, Alexa, and Home
   Assistant.

Summary & What's Next
=====================

Multi-fabric commissioning turns `purpleair-matterbridge
<https://github.com/carlkidcrypto/purpleair-matterbridge>`_ into a universal
local air quality hub. By leveraging Enhanced Commissioning Windows and local
IPv6 subscriptions, every smart home controller in your household stays
synchronized in real time without cloud dependencies.

In our next blog post, we will rotate back to `ezsnmp
<https://github.com/carlkidcrypto/ezsnmp>`_, diving into real-time Quality of
Service (QoS) telemetry and auditing Differentiated Services (DiffServ) queue
drops using ``DIFFSERV-MIB``.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

