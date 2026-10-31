.. meta::
   :description: Technical articles, release notes, and engineering tutorials on ezsnmp, PurpleAir API, air quality IoT sensing, and DevOps automation by Carlos (@carlkidcrypto).
   :keywords: ezsnmp blog, purpleair api tutorials, purple air data logger guides, purpleair matterbridge, carlkidcrypto
   :author: Carlos (@carlkidcrypto)
   :property=og:title: Blog — carlkidcrypto
   :property=og:description: Technical articles, release notes, and tutorials on ezsnmp, PurpleAir API, and DevOps automation.
   :property=og:type: website
   :property=og:url: https://carlkidcrypto.github.io/blog/
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Blog — carlkidcrypto
   :name=twitter:description: Technical articles, release notes, and tutorials on ezsnmp, PurpleAir API, and DevOps automation.
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

Blog
====

Articles, release notes, and engineering tutorials on open source software, air quality sensing, and DevOps automation.

.. toctree::
   :maxdepth: 1
   :caption: Articles:













   ezsnmp-snmpv3-tls-dtls-security
   ezsnmp-custom-agent-extensions-agentx
   ezsnmp-vlan-management-qinq-automation
   ezsnmp-realtime-telemetry-polars-duckdb
   ezsnmp-set-operations-device-configuration
   ezsnmp-network-topology-discovery-lldp-cdp
   ezsnmp-custom-observability-exporters
   ezsnmp-cpp17-native-architecture
   ezsnmp-advanced-table-navigation
   ezsnmp-resilient-polling-error-handling
   ezsnmp-async-polling-event-loops
   ezsnmp-working-with-mibs-guide
   ezsnmp-cross-platform-installation-troubleshooting
   ezsnmp-high-throughput-multithreading
   ezsnmp-snmpv3-deep-dive
   ezsnmp-getting-started-guide

All Posts
---------

.. grid:: 1
   :gutter: 3

   .. grid-item-card:: 📖 Modernizing SNMP Security: SNMPv3 over TLS and DTLS with ezsnmp
      :link: ezsnmp-snmpv3-tls-dtls-security
      :link-type: doc

      For decades, network engineers securing SNMP relied on the User-based Security Model (USM) introduced in SNMPv3. While USM provided cryptographic hashing...

      +++
      📅 *October 28, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Snmpv3` `Tls`

   .. grid-item-card:: 📖 Building Custom SNMP Agent Extensions with Python and ezsnmp
      :link: ezsnmp-custom-agent-extensions-agentx
      :link-type: doc

      While most network engineers interact with SNMP purely as client consumers (running ``GET``, ``WALK``, or ``SET`` queries against network gear), systems...

      +++
      📅 *October 27, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Snmpd` `Agentx`

   .. grid-item-card:: 📖 Automating VLAN Management & Q-in-Q Tagging with ezsnmp
      :link: ezsnmp-vlan-management-qinq-automation
      :link-type: doc

      In enterprise campus environments, data center fabrics, and carrier Ethernet networks, Virtual Local Area Networks (VLANs, IEEE 802.1Q) partition physical...

      +++
      📅 *October 26, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Vlan` `Q-In-Q`

   .. grid-item-card:: 📖 Real-Time Network Telemetry with ezsnmp, Polars, and DuckDB
      :link: ezsnmp-realtime-telemetry-polars-duckdb
      :link-type: doc

      Modern network engineers increasingly require sub-interval telemetry: polling switch fabrics, optical links, and data center core routers at 1- to 5-second...

      +++
      📅 *October 25, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Polars` `Duckdb`

   .. grid-item-card:: 📖 SNMP Set Operations & Device Configuration with ezsnmp
      :link: ezsnmp-set-operations-device-configuration
      :link-type: doc

      While the vast majority of network monitoring relies on read-only operations (``GET`` and ``WALK``), the Simple Network Management Protocol was designed...

      +++
      📅 *October 24, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Snmpset` `Configuration`

   .. grid-item-card:: 📖 Automating Network Topology Discovery: LLDP and CDP with ezsnmp
      :link: ezsnmp-network-topology-discovery-lldp-cdp
      :link-type: doc

      Maintaining accurate, real-time physical network maps is an essential requirement for data center automation, root-cause failure analysis, and Source of...

      +++
      📅 *October 23, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Lldp` `Cdp`

   .. grid-item-card:: 📖 Building Custom Observability Exporters with ezsnmp
      :link: ezsnmp-custom-observability-exporters
      :link-type: doc

      In modern Site Reliability Engineering (SRE) and cloud infrastructure, network metrics belong alongside application telemetry in centralized platforms like...

      +++
      📅 *October 22, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Prometheus` `Opentelemetry`

   .. grid-item-card:: 📖 C++17 Under the Hood: Inside ezsnmp's Native Architecture
      :link: ezsnmp-cpp17-native-architecture
      :link-type: doc

      Python extensions interfacing with legacy C libraries are notoriously difficult to maintain. The official Net-SNMP library—while mature, highly optimized,...

      +++
      📅 *October 21, 2026* • ⏱️ *5 min read* • `Python` `Cpp` `C++17` `Snmp`

   .. grid-item-card:: 📖 Navigating Complex SNMP Tables with ezsnmp: Advanced Patterns
      :link: ezsnmp-advanced-table-navigation
      :link-type: doc

      Unlike modern REST APIs or SQL databases that return structured JSON arrays or tabular rows, Simple Network Management Protocol (SNMP) represents tables as...

      +++
      📅 *October 20, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Tables` `Mib`

   .. grid-item-card:: 📖 Resilient SNMP Polling with ezsnmp: Timeouts, Retries & Errors
      :link: ezsnmp-resilient-polling-error-handling
      :link-type: doc

      Simple Network Management Protocol (SNMP) runs over User Datagram Protocol (UDP), an inherently connectionless transport. In laboratory setups, polling runs...

      +++
      📅 *October 19, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Reliability` `Error-Handling`

   .. grid-item-card:: 📖 Asynchronous Polling with ezsnmp: Integrating into asyncio
      :link: ezsnmp-async-polling-event-loops
      :link-type: doc

      Modern network automation tools—from FastAPI telemetry microservices to real-time event streaming engines—rely heavily on Python's ``asyncio`` event loop to...

      +++
      📅 *October 18, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Asyncio` `Concurrency`

   .. grid-item-card:: 📖 Working with MIBs in ezsnmp: OID Translation & Enterprise MIBs
      :link: ezsnmp-working-with-mibs-guide
      :link-type: doc

      Behind every SNMP query lies an Object Identifier (OID)—a dotted-decimal tree sequence like ``.1.3.6.1.2.1.1.1.0``. While network daemons communicate...

      +++
      📅 *October 17, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Mibs` `Net-Snmp`

   .. grid-item-card:: 🛠️ Cross-Platform Installation & Troubleshooting ezsnmp Builds
      :link: ezsnmp-cross-platform-installation-troubleshooting
      :link-type: doc

      Master ezsnmp installations across Windows, macOS, Linux distributions, and Docker. Learn how pre-built Windows wheels, Homebrew taps, and multi-stage Docker builds resolve C-extension header and linker bottlenecks.

      +++
      📅 *October 16, 2026* • ⏱️ *6 min read* • `Python` `DevOps` `Packaging` `Troubleshooting`

   .. grid-item-card:: ⚡ High-Throughput Network Monitoring: Scaling ezsnmp Concurrency
      :link: ezsnmp-high-throughput-multithreading
      :link-type: doc

      Scale network monitoring throughput in Python using ezsnmp. Learn how C-level GIL release, ThreadPoolExecutor worker pools, and GETBULK maximize parallel polling performance.

      +++
      📅 *October 15, 2026* • ⏱️ *5 min read* • `Python` `Networking` `Concurrency` `Performance`

   .. grid-item-card:: 🔒 Mastering SNMPv3 with ezsnmp: USM, AuthPriv, and EngineID Tips
      :link: ezsnmp-snmpv3-deep-dive
      :link-type: doc

      A deep dive into secure SNMPv3 network monitoring with ezsnmp. Covers USM security levels, SHA/AES authPriv setup, VRF contexts, explicit EngineID caching, and robust exception handling.

      +++
      📅 *October 14, 2026* • ⏱️ *5 min read* • `Python` `Networking` `SNMPv3` `Security`

   .. grid-item-card:: 📡 Modern SNMP in Python with ezsnmp: Practical Guide & Migration
      :link: ezsnmp-getting-started-guide
      :link-type: doc

      A hands-on introduction to ezsnmp—a high-performance, C++17 Python wrapper for Net-SNMP. Covers v2c queries, GETBULK walks, SNMPv3 authPriv encryption, session reuse, and migrating from Easy SNMP.

      +++
      📅 *October 13, 2026* • ⏱️ *4 min read* • `Python` `Networking` `ezsnmp`
