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
   :maxdepth: 2
   :caption: Topics:

   category-ezsnmp
   category-purpleair-api
   category-purpleair-data-logger
   category-purpleair-matterbridge

Explore by Topic
----------------

.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item-card:: 📡 ezsnmp Telemetry & Architecture
      :link: category-ezsnmp
      :link-type: doc

      Deep dives into high-throughput SNMP polling, SNMPv3 security, network protocols (BGP, OSPF, IS-IS, VRRP, NetFlow, PoE, LLDP), and C++17 internals.

      +++
      📚 *28 Articles* • `ezsnmp` `Networking` `SNMP`

   .. grid-item-card:: 🌬️ PurpleAir API & IoT Sensing
      :link: category-purpleair-api
      :link-type: doc

      Developer tutorials for extracting real-time and historical air quality sensor telemetry, bounding box queries, and sensor group management.

      +++
      📚 *3 Articles* • `PurpleAir` `IoT` `Air Quality`

   .. grid-item-card:: 📊 PurpleAir Data Logger & TimescaleDB
      :link: category-purpleair-data-logger
      :link-type: doc

      Architecture and deployment guides for logging sensor data to TimescaleDB, PostgreSQL hypertables, and local CSV/SQLite archives.

      +++
      📚 *3 Articles* • `TimescaleDB` `PostgreSQL` `Data Logging`

   .. grid-item-card:: 🏠 Matter Smart Home & Matterbridge
      :link: category-purpleair-matterbridge
      :link-type: doc

      Exposing PurpleAir sensors as Matter 1.5.1 Air Quality devices into Apple Home, Home Assistant, and Matterbridge smart home ecosystems.

      +++
      📚 *3 Articles* • `Matter` `Smart Home` `Apple Home`

All Posts
---------

.. grid:: 1
   :gutter: 3

   .. grid-item-card:: 📖 Standardizing Multi-Repo CI/CD with Reusable GitHub Actions
      :link: shared-workflows-reusable-github-actions-cicd
      :link-type: doc

      Maintaining a single open source repository requires a handful of GitHub Actions workflows for linting, unit testing, and package publishing. However, once...

      +++
      📅 *November 21, 2026* • ⏱️ *7 min read* • `Github-Actions` `Cicd` `Shared-Workflows` `Python`

   .. grid-item-card:: 📖 Getting Started with ezsnmp_data_logger: SNMP Telemetry Pipelines
      :link: ezsnmp-data-logger-getting-started-pipelines
      :link-type: doc

      Polling network devices with `ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ gives Python engineers direct, high-speed access to Net-SNMP's C++17...

      +++
      📅 *November 20, 2026* • ⏱️ *7 min read* • `Ezsnmp` `Ezsnmp_Data_Logger` `Python` `Snmp`

   .. grid-item-card:: 📖 Monitoring Hardware Transceiver Optical Power (DOM/DDM) with ezsnmp
      :link: ezsnmp-transceiver-optical-power-dom-telemetry
      :link-type: doc

      High-speed datacenter spine uplinks and metro fiber rings depend on pluggable optical transceivers—such as SFP+, SFP28, QSFP28, and QSFP-DD modules. Before...

      +++
      📅 *November 19, 2026* • ⏱️ *5 min read* • `Ezsnmp` `Python` `Snmp` `Optics`

   .. grid-item-card:: 📖 Real-Time WebSocket Telemetry Streams & Event-Driven Cluster Updates
      :link: purpleair-matterbridge-websocket-event-driven-updates
      :link-type: doc

      Traditional smart home bridges rely heavily on fixed-interval HTTP polling. Every 30 or 60 seconds, the bridge requests a full JSON snapshot from an API or...

      +++
      📅 *November 18, 2026* • ⏱️ *5 min read* • `Purpleair` `Matter` `Websocket` `Matterbridge`

   .. grid-item-card:: 📖 Containerized Edge Deployments: Multi-Architecture Docker Builds for Raspberry Pi & NAS Systems
      :link: purpleair-data-logger-multiarch-docker-edge
      :link-type: doc

      Containerize purpleair_data_logger with multi-architecture Docker Buildx images, non-root security, persistent volumes, and healthchecks for Raspberry Pi and NAS systems.

      +++
      📅 *November 17, 2026* • ⏱️ *5 min read* • `Purpleair` `Docker` `Raspberry-Pi` `Arm64`

   .. grid-item-card:: 📖 Asynchronous Batch Polling & High-Concurrency Telemetry Pipelines with purpleair_api
      :link: purpleair-api-async-batch-polling-pipelines
      :link-type: doc

      Scale purpleair_api telemetry pipelines from single sensors to hundreds of stations using asyncio, bounded ThreadPoolExecutor concurrency, and rate-limit-safe backoff.

      +++
      📅 *November 16, 2026* • ⏱️ *5 min read* • `Purpleair` `Python` `Asyncio` `Concurrency`

   .. grid-item-card:: 📖 Real-Time QoS Telemetry: Auditing Differentiated Services (DiffServ) & Queue Drops with ezsnmp
      :link: ezsnmp-qos-diffserv-queue-drop-telemetry
      :link-type: doc

      Poll RFC 3289 DIFFSERV-MIB counters and algorithmic tail-drop or WRED queue discards in real time using ezsnmp and Python.

      +++
      📅 *November 15, 2026* • ⏱️ *5 min read* • `ezsnmp` `Python` `SNMP` `QoS`

   .. grid-item-card:: 📖 Multi-Fabric Commissioning: Sharing PurpleAir Matterbridge with Apple Home and Google Home Concurrently
      :link: purpleair-matterbridge-multi-fabric-commissioning
      :link-type: doc

      Share a single purpleair-matterbridge instance concurrently across Apple Home and Google Home using Matter Multi-Admin and Enhanced Commissioning Windows.

      +++
      📅 *November 14, 2026* • ⏱️ *5 min read* • `PurpleAir` `Matterbridge` `Matter` `Multi-Fabric`

   .. grid-item-card:: 📖 Building Automated Grafana Dashboards over TimescaleDB PurpleAir Telemetry
      :link: purpleair-data-logger-grafana-timescaledb-dashboards
      :link-type: doc

      Connect Grafana to TimescaleDB and PostgreSQL telemetry from purpleair_data_logger with read-only roles, time_bucket panels, heatmaps, and spike alerts.

      +++
      📅 *November 13, 2026* • ⏱️ *5 min read* • `PurpleAir` `Grafana` `TimescaleDB` `PostgreSQL`

   .. grid-item-card:: 📖 Working with the Matter Device Converter: Mapping Sensor Data to Matter 1.5.1 Clusters
      :link: purpleair-api-matter-device-converter-guide
      :link-type: doc

      Convert PurpleAir PM2.5, VOC, temperature, humidity, and pressure readings into CSA Matter 1.5.1 cluster payloads and US EPA AQI ratings in Python.

      +++
      📅 *November 12, 2026* • ⏱️ *5 min read* • `PurpleAir` `Python` `Matter` `IoT`

   .. grid-item-card:: 📖 Auditing BGP EVPN and VXLAN Overlay Fabric Health with ezsnmp
      :link: ezsnmp-bgp-evpn-vxlan-fabric-telemetry
      :link-type: doc

      Audit BGP EVPN control-plane sessions, VNI state, and VXLAN tunnel endpoints (VTEPs) across leaf-spine data center fabrics using ezsnmp and Net-SNMP.

      +++
      📅 *November 11, 2026* • ⏱️ *5 min read* • `ezsnmp` `Python` `SNMP` `BGP`

   .. grid-item-card:: 📖 Matter Device Clustering & Sensor Telemetry Mapping for Smart Homes
      :link: purpleair-matterbridge-device-clustering-telemetry-mapping
      :link-type: doc

      Deep dive into how purpleair-matterbridge translates raw particulate laser counters and environmental readings into Matter 1.5.1 compliant clusters.

      +++
      📅 *November 10, 2026* • ⏱️ *5 min read* • `PurpleAir` `Matter` `Smart-Home` `IoT`

   .. grid-item-card:: 📖 Local Sensor Polling & Offline CSV/SQLite Archival with purpleair_data_logger
      :link: purpleair-data-logger-local-csv-sqlite-archival
      :link-type: doc

      Configure and run the SQLite and CSV backends in purpleair_data_logger for zero-infrastructure edge logging, automated file rotation, and SQL analytics.

      +++
      📅 *November 9, 2026* • ⏱️ *5 min read* • `PurpleAir` `Python` `SQLite` `CSV`

   .. grid-item-card:: 📖 Historical Sensor Data Extraction and Bounding Box Geographic Queries with purpleair_api
      :link: purpleair-api-historical-data-bounding-box-queries
      :link-type: doc

      Extract historical sensor measurements, query spatial bounding boxes across geographic regions, and manage chunked time-series retrievals using the official purpleair_api Python library.

      +++
      📅 *November 08, 2026* • ⏱️ *5 min read* • `PurpleAir` `Python` `IoT` `Air-Quality`

   .. grid-item-card:: 📖 MPLS & Segment Routing LSP Telemetry: Label Switched Path Auditing with ezsnmp
      :link: ezsnmp-mpls-segment-routing-lsp-telemetry
      :link-type: doc

      Modern enterprise campus backbones, wide-area networks (WAN), and service provider backbones rely on Multiprotocol Label Switching (MPLS) and Segment...

      +++
      📅 *November 7, 2026* • ⏱️ *5 min read* • `Ezsnmp` `Python` `Snmp` `Mpls`

   .. grid-item-card:: 📖 Bridging PurpleAir Air Quality Sensors into Smart Home Matter Ecosystems
      :link: purpleair-matterbridge-smart-home-integration
      :link-type: doc

      Bridge PurpleAir air quality telemetry into Apple Home, Home Assistant, and Matter smart homes using the official purpleair-matterbridge plugin and Docker with host networking.

      +++
      📅 *November 06, 2026* • ⏱️ *5 min read* • `PurpleAir` `Matter` `Smart-Home` `IoT`

   .. grid-item-card:: 📖 Automated TimescaleDB & PostgreSQL Ingestion for PurpleAir Sensors
      :link: purpleair-data-logger-timescaledb-postgresql-ingestion
      :link-type: doc

      Stream real-time and historical PurpleAir air quality telemetry into PostgreSQL with TimescaleDB hypertables, automated compression, continuous aggregates, and time_bucket analytical SQL rollups.

      +++
      📅 *November 05, 2026* • ⏱️ *5 min read* • `PurpleAir` `TimescaleDB` `PostgreSQL` `IoT`

   .. grid-item-card:: 📖 Getting Started with the Python PurpleAir API Wrapper: Sensor Discovery, Keys & Rate Limits
      :link: purpleair-api-getting-started-guide
      :link-type: doc

      Explore the official PurpleAir API Python wrapper (purpleair_api). Learn sensor discovery, read and write credential separation, bounding box queries, and resilient rate-limited polling.

      +++
      📅 *November 04, 2026* • ⏱️ *5 min read* • `PurpleAir` `Python` `IoT` `Air-Quality`

   .. grid-item-card:: 📖 First-Hop Redundancy Monitoring: VRRP & HSRP with ezsnmp
      :link: ezsnmp-vrrp-hsrp-redundancy-monitoring
      :link-type: doc

      Query VRRP and HSRP operational parameters, cross-reconcile HA gateway pairs, and detect split-brain dual-master anomalies in real time using ezsnmp.

      +++
      📅 *November 03, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Vrrp` `Hsrp`

   .. grid-item-card:: 📖 Network Time & Clock Synchronization Telemetry with ezsnmp
      :link: ezsnmp-network-time-ntp-ptp-telemetry
      :link-type: doc

      Inspect system NTP synchronization states, evaluate stratum levels, and alert on clock skew and dispersion across network fleets using ezsnmp and Net-SNMP C bindings.

      +++
      📅 *November 02, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Ntp` `Ptp`

   .. grid-item-card:: 📖 OSPF & IS-IS Link-State Telemetry: Neighbor Auditing in ezsnmp
      :link: ezsnmp-ospf-isis-link-state-telemetry
      :link-type: doc

      Audit OSPF and IS-IS neighbor adjacencies, detect MTU-induced stuck sessions, and monitor LSA retransmission queues in real time using ezsnmp and Net-SNMP C bindings.

      +++
      📅 *November 01, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Ospf` `Is-Is`

   .. grid-item-card:: 📖 Traffic Flow Auditing: Monitoring NetFlow & IPFIX with ezsnmp
      :link: ezsnmp-traffic-flow-netflow-ipfix-auditing
      :link-type: doc

      Audit Cisco NetFlow and IPFIX flow exporter health with ezsnmp. Detect exporter-side packet drops, local queue buffer exhaustion, and cache sizing limits across transit routers.

      +++
      📅 *October 31, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Netflow` `Ipfix`

   .. grid-item-card:: 📖 Auditing Enterprise PoE Budgets & Power Delivery with ezsnmp
      :link: ezsnmp-enterprise-poe-power-auditing
      :link-type: doc

      Power over Ethernet (PoE) has evolved far beyond powering standard desk VoIP phones. In modern enterprise campus networks and smart facilities, edge...

      +++
      📅 *November 2, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Poe` `Power-Over-Ethernet`

   .. grid-item-card:: 📖 BGP Routing Telemetry: Peering States & Prefix Counts in ezsnmp
      :link: ezsnmp-bgp-routing-telemetry
      :link-type: doc

      The Border Gateway Protocol (BGP-4) serves as the routing foundation for the global internet, cloud direct connects, and modern data center spine-leaf Clos...

      +++
      📅 *November 1, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Bgp` `Bgp4-Mib`

   .. grid-item-card:: 📖 Dynamic Inventory Sync: Populating NetBox & Nautobot via ezsnmp
      :link: ezsnmp-dynamic-inventory-sync-netbox
      :link-type: doc

      Modern NetDevOps workflows center on a digital Source of Truth (SoT) such as **NetBox** or **Nautobot**. These platforms define the intended state of device...

      +++
      📅 *October 31, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Netbox` `Nautobot`

   .. grid-item-card:: 📖 Testing SNMP Automation Pipelines with pytest and ezsnmp
      :link: ezsnmp-testing-ci-cd-pytest
      :link-type: doc

      Developing network automation software—such as custom telemetry daemons, exporters, and configuration crawlers—presents a fundamental testing challenge:

      +++
      📅 *October 30, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Pytest` `Testing`

   .. grid-item-card:: 📖 Hardware Health & Optical Power Monitoring (DOM/DDM) in ezsnmp
      :link: ezsnmp-hardware-optical-dom-monitoring
      :link-type: doc

      In modern high-speed data center fabrics and long-haul links (10G, 25G, 100G, and 400G), optical transceivers (SFP+, QSFP28, QSFP-DD) represent one of the...

      +++
      📅 *October 29, 2026* • ⏱️ *5 min read* • `Python` `Snmp` `Optical` `Dom`

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
