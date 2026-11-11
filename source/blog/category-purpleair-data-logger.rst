.. meta::
   :description: Real-time time-series logging, local CSV/SQLite archival, and PostgreSQL/TimescaleDB ingestion with purpleair_data_logger (PADLs).
   :keywords: purpleair data logger, padls, timescaledb air quality, postgresql iot, sqlite csv archival
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: PurpleAir Data Logger & TimescaleDB — carlkidcrypto Blog
   :property=og:description: Real-time time-series logging, local CSV/SQLite archival, and PostgreSQL/TimescaleDB ingestion with purpleair_data_logger (PADLs).
   :property=og:type: website
   :property=og:url: https://carlkidcrypto.github.io/blog/category-purpleair-data-logger.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: PurpleAir Data Logger & TimescaleDB — carlkidcrypto Blog
   :name=twitter:description: Real-time time-series logging, local CSV/SQLite archival, and PostgreSQL/TimescaleDB ingestion with purpleair_data_logger (PADLs).
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

PurpleAir Data Logger & TimescaleDB
===================================

Production data pipeline guides, local CSV/SQLite offline logging, and automated TimescaleDB/PostgreSQL hypertable ingestion using `purpleair_data_logger <https://github.com/carlkidcrypto/purpleair_data_logger>`_ (PADLs).

.. toctree::
   :maxdepth: 1
   :caption: Articles:

   purpleair-data-logger-local-csv-sqlite-archival
   purpleair-data-logger-timescaledb-postgresql-ingestion

Articles
--------

.. grid:: 1
   :gutter: 3

   .. grid-item-card:: 📖 Local Sensor Polling & Offline CSV/SQLite Archival with purpleair_data_logger
         :link: purpleair-data-logger-local-csv-sqlite-archival
         :link-type: doc
   
         Enterprise cloud data warehouses and managed time-series databases like TimescaleDB offer exceptional query performance for central dashboards. However,...
   
         +++
         📅 *November 9, 2026* • ⏱️ *5 min read* • `Purpleair` `Python` `Sqlite` `Csv`

   .. grid-item-card:: 📖 Automated TimescaleDB & PostgreSQL Ingestion for PurpleAir Sensors
         :link: purpleair-data-logger-timescaledb-postgresql-ingestion
         :link-type: doc
   
         Stream real-time and historical PurpleAir air quality telemetry into PostgreSQL with TimescaleDB hypertables, automated compression, continuous aggregates, and time_bucket analytical SQL rollups.
   
         +++
         📅 *November 05, 2026* • ⏱️ *5 min read* • `PurpleAir` `TimescaleDB` `PostgreSQL` `IoT`
