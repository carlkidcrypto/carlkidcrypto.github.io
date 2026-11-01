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


   ezsnmp-working-with-mibs-guide
   ezsnmp-cross-platform-installation-troubleshooting
   ezsnmp-high-throughput-multithreading
   ezsnmp-snmpv3-deep-dive
   ezsnmp-getting-started-guide

All Posts
---------

.. grid:: 1
   :gutter: 3

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
