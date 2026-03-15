Modernization TODO List
=======================

Conventions
-----------

- ``[x]`` done
- ``[ ]`` not done yet
- ``[-]`` intentionally deferred

Primary goals
-------------

- keep ZSpider as a self-hosted application instead of a general-purpose PyPI package
- preserve the ``web / dispatcher / crawler`` process split
- preserve the task / parser / field-configuration domain model
- reduce runtime aging, security risk, and maintenance friction incrementally

Current snapshot
----------------

- [x] documentation reorganized into bilingual Chinese / English sections
- [x] repository positioning clarified as a self-hosted application
- [x] local entry points centered around ``make`` / ``python -m`` / ``docker compose``
- [x] unified ``settings`` layer for runtime configuration
- [x] ``development / testing / production`` environment distinction
- [x] WSGI-based web startup replacing Flask ``app.run``
- [x] ``/healthz`` and ``/readyz`` endpoints
- [x] operations documentation and ``.env.example``
- [x] explicit admin bootstrap command via ``make bootstrap-admin``

P0: Baseline and Tooling
------------------------

- [x] development and runtime docs updated
- [x] unified local entry points such as ``make install`` / ``make dev`` / ``make docs``
- [ ] define and document the supported Python version policy
- [ ] add lint checks to CI, not only unit tests
- [ ] introduce ``ruff``
- [ ] introduce ``pytest`` and phase out ``unittest discover``
- [ ] add minimal ``mypy`` coverage to key modules
- [ ] complete ``pyproject.toml`` so it actually carries toolchain configuration

P1: Configuration and Deployment Hygiene
----------------------------------------

- [x] MQ, Memcached, and MongoDB addresses are environment-driven
- [x] unified ``settings`` layer added
- [x] environment split for development, testing, and production
- [x] local dependencies defined through ``docker-compose.services.yml``
- [x] Flask development startup replaced with WSGI serving
- [x] health and readiness documentation added
- [x] Compose health checks added for MongoDB and RabbitMQ
- [ ] add a reliable Compose health check for Memcached
- [ ] add a dedicated health endpoint for Dispatcher
- [ ] add a dedicated health or liveness signal for Crawler
- [ ] write a single deployment guide for local and hosted operation modes
- [ ] decide whether the legacy ``supervisor`` configs stay or are removed

P2: Security Hardening
----------------------

- [x] removed implicit "first login becomes admin"
- [x] added explicit admin bootstrap command
- [ ] upgrade password hashing from SHA-256 to ``bcrypt`` or ``argon2``
- [ ] design a compatible password migration path
- [ ] add regression tests for login, logout, and admin bootstrap
- [ ] review ``SECRET_KEY``, session cookie, and CSRF configuration
- [ ] define clearer admin permission boundaries
- [ ] replace ``eval`` in ``publish.py``

P3: Web / API Boundary Refactor
-------------------------------

- [ ] extract login, task management, and log workflows into service modules
- [ ] define more stable internal APIs for tasks, fields, results, and logs
- [ ] reduce direct coupling between templates and database models
- [ ] gradually turn the current HTML admin into one client of backend capabilities
- [ ] improve error handling and response boundaries in the web layer

P4: Runtime and Data Plane
--------------------------

- [ ] formalize the Dispatcher -> Crawler message schema
- [ ] add execution state and run-history tracking
- [ ] improve retry, dead-letter, or compensation strategy
- [ ] clarify status codes for crawl, parse, and publish failures
- [ ] evaluate whether Redis should replace Memcached
- [ ] add metrics for queue lag, crawl success rate, and publish failure rate

P5: UX Modernization
--------------------

- [ ] redesign the admin information architecture
- [ ] improve task creation flow
- [ ] improve parser debugging and preview
- [ ] add run history, diff views, and result inspection
- [ ] improve logs and operator-facing failure feedback

Explicit non-goals
------------------

- [-] no full rewrite
- [-] no premature microservice split
- [-] no aggressive frontend/backend split at this stage
- [-] no frontend rebuild just for visual modernization
- [-] no database migration before real operational need appears
- [-] no goal of publishing to PyPI

Recommended next batch
----------------------

If work continues from the current state, the next concrete batch should be:

- [ ] upgrade password hashing to ``bcrypt`` or ``argon2``
- [ ] add tests for login and admin bootstrap
- [ ] replace ``eval`` in ``publish.py``
- [ ] add linting to CI
- [ ] add Dispatcher health or readiness endpoint
