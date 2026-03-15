Modernization Plan
==================

This document proposes a practical modernization path for ZSpider.

The goal is not to rewrite the project from scratch. The goal is to preserve the parts that already fit the product well, then reduce the maintenance cost, deployment friction, and security risk step by step.

Why Modernize
-------------

From the current codebase and project analysis, ZSpider already has a useful platform shape:

- a clear three-process runtime split
- a task-centered operational model
- configuration-driven parsing
- a usable admin backend for recurring crawling workflows

The main issues are not product positioning or domain design. The main issues are:

- legacy-sensitive dependencies
- hardcoded environment assumptions
- outdated security defaults
- weak boundary between web, admin, and runtime services
- limited modern observability and release discipline

Modernization should therefore focus on runtime, safety, and maintainability first.

Guiding Principles
------------------

1. Preserve the domain model.

   The concepts around ``Task``, ``Parser``, ``ArticleField``, ``Dispatcher``, ``Crawler``, and result review are the core of the project. These should remain recognizable after modernization.

2. Prefer incremental replacement over rewrite.

   A full rewrite would delay value and create migration risk. This project is better served by staged upgrades with compatibility windows.

3. Separate product concerns from technical debt.

   The existing product idea is still valid. The modernization effort should target engineering debt instead of rethinking everything at once.

4. Make deployment and operation boring.

   Local startup, test execution, CI, and production configuration should be explicit, repeatable, and environment-driven.

5. Remove high-risk flexibility.

   Dynamic behavior such as unrestricted ``eval`` from configuration should be replaced with constrained, auditable mechanisms.

Target State
------------

After modernization, ZSpider should have the following characteristics:

- a supported modern Python runtime
- environment-driven configuration
- reproducible dependency locking
- API-first backend boundaries
- stronger authentication and authorization
- safer transformation and publish rules
- structured logs, metrics, and health checks
- CI with reliable test and lint gates
- documented migration paths for operators

What Should Be Kept
-------------------

The following parts are worth preserving:

+----------------------------------+--------------------------------------------------+
| Area                             | Keep / Preserve                                  |
+==================================+==================================================+
| Runtime split                    | ``web`` / ``dispatcher`` / ``crawler``           |
+----------------------------------+--------------------------------------------------+
| Product model                    | task-based recurring crawling                    |
+----------------------------------+--------------------------------------------------+
| Parser abstraction               | parser + field configuration model               |
+----------------------------------+--------------------------------------------------+
| Queue-based execution            | async dispatch between scheduler and workers     |
+----------------------------------+--------------------------------------------------+
| Self-hosted admin positioning    | internal operations and monitoring workflow      |
+----------------------------------+--------------------------------------------------+

These are the parts that differentiate ZSpider from a loose collection of crawler scripts.

What Should Change First
------------------------

Priority should be driven by operational risk rather than novelty.

Immediate focus areas:

1. dependency and runtime upgrade
2. configuration externalization
3. authentication and password handling
4. replacement of ``eval``-based transformation logic
5. test, lint, and release discipline

Current Constraints
-------------------

The current repository shows several constraints that should shape the plan:

- the repository still carries legacy packaging assumptions
- ``pyproject.toml`` is minimal and does not define modern build metadata
- the documented local stack is pinned to Python 3.9
- ``zspider/confs/conf.py`` embeds local and production assumptions in code
- ``zspider/web.py`` starts the Flask app with development-style execution
- the login flow allows the first submitted username and password to become the initial admin account
- ``zspider/pipelines/publish.py`` evaluates configured expressions with Python ``eval``

These constraints make the project maintainable only in a narrow, controlled environment.

Recommended Modernization Phases
--------------------------------

Phase 0: Baseline and Freeze
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:

- make the current system reproducible before changing behavior

Deliverables:

- confirm a known-good baseline environment
- record current startup, test, and deployment procedures
- capture sample data and representative tasks for regression validation
- define compatibility goals for the next supported Python version

Output:

- a short baseline report
- a smoke-test checklist for ``web``, ``dispatcher``, and ``crawler``

Phase 1: Tooling and Runtime Foundation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:

- modernize the engineering toolchain without changing product behavior

Changes:

- standardize local development around one Python version target
- add linting, formatting, import sorting, and test commands to CI
- introduce a lock strategy for application and development dependencies
- document supported Python versions and deprecation windows

Application-oriented direction:

- treat the repository as a deployable application, not a publishable library
- prefer source-based runtime entry points such as ``python -m zspider.web``
- keep packaging concerns minimal and only where they help internal deployment

Recommended tooling direction:

+----------------------+----------------------------------------------+
| Concern              | Recommendation                               |
+======================+==============================================+
| Packaging            | ``pyproject.toml`` with setuptools or hatch  |
+----------------------+----------------------------------------------+
| Lint                 | ``ruff``                                     |
+----------------------+----------------------------------------------+
| Format               | ``black``                                    |
+----------------------+----------------------------------------------+
| Tests                | ``pytest``                                   |
+----------------------+----------------------------------------------+
| Type checks          | ``mypy`` on selected boundaries              |
+----------------------+----------------------------------------------+
| Local automation     | ``make`` retained as compatibility wrapper   |
+----------------------+----------------------------------------------+

Exit criteria:

- fresh setup is reproducible from docs
- CI validates lint and tests on the chosen Python version

Phase 2: Configuration and Deployment Hygiene
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:

- remove environment assumptions from code and make service startup explicit

Changes:

- replace hardcoded MQ, cache, and service addresses with environment-based settings
- consolidate settings loading through a single configuration layer
- introduce development, test, and production profiles through environment variables
- define a supported local stack through Docker Compose
- replace development-style Flask execution with a production-ready WSGI or ASGI serving strategy
- document health endpoints and readiness checks

Recommended direction:

- use ``.env`` for local defaults
- keep config names stable and explicit, for example ``ZSPIDER_MONGODB_URI`` and ``ZSPIDER_AMQP_URL``
- ensure no production addresses or credentials are embedded in repository code

Exit criteria:

- the project starts with no code edits across environments
- all environment-sensitive values are externalized

Phase 3: Security Hardening
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:

- raise the security baseline to match a modern internal platform

Changes:

- replace direct SHA-256 password storage with ``bcrypt`` or ``argon2``
- remove the "first login becomes admin" bootstrap behavior
- add explicit admin bootstrap or management command flow
- review session configuration, secret management, and CSRF handling
- introduce role checks with clearer boundaries for admin-only operations
- add security-focused regression tests around login and authorization

High-priority risk removal:

- replace ``eval`` in publish transformations with one of the following:

  - a constrained expression language
  - a small whitelist-based transform registry
  - a plugin mechanism for trusted code reviewed transforms

Exit criteria:

- admin creation is explicit and auditable
- password storage follows a modern hashing strategy
- transformation rules no longer execute arbitrary Python from configuration

Phase 4: API-First Service Boundaries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:

- separate backend behavior from server-rendered admin templates

Changes:

- define a stable API layer for task management, parser configuration, results, and logs
- move business logic out of request handlers into service modules
- reduce coupling between templates and persistence models
- treat the current HTML admin as one client of the backend rather than the backend itself

Recommended approach:

- keep the current web stack during the transition
- first extract service and schema layers
- only then decide whether the admin UI stays server-rendered or becomes a separate frontend

Exit criteria:

- task and result operations are available through documented internal APIs
- core business logic is testable without full request context

Phase 5: Runtime and Data Plane Improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:

- improve reliability and scalability without changing the product model

Changes:

- formalize task message schemas between dispatcher and crawler
- add structured execution states for scheduled jobs and crawl runs
- improve failure handling, retries, and dead-letter or retry policy
- consider replacing Memcached with Redis if it simplifies heartbeat, deduplication, and temporary state
- add metrics around queue lag, crawl success rate, parser failures, and publish failures

This phase should be driven by observed operational needs, not by aesthetics.

Phase 6: UX and Product-Level Modernization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:

- improve usability after the technical core is stable

Possible work:

- redesign the admin information architecture
- improve task creation and parser debugging flows
- add preview and validation before task activation
- add better run history, diff view, and result inspection
- improve operator feedback for schedule status and publish failures

This phase should happen after the backend contracts are stable.

Suggested Repository Changes
----------------------------

The following repository-level changes are likely to provide the best near-term return:

1. complete ``pyproject.toml`` and reduce dependence on legacy packaging metadata
2. add a dedicated settings module that replaces direct config constants in ``zspider/confs/conf.py``
3. add a documented admin bootstrap command instead of implicit first-login bootstrap
4. replace ``eval`` in the publish pipeline with a constrained transformation mechanism
5. add ``docs/operations.rst`` or equivalent for environment setup, deployment, and health verification
6. add a clear CI matrix for the supported Python version strategy

Suggested Delivery Order
------------------------

An effective delivery order for a small team is:

1. establish baseline tests and runtime reproducibility
2. modernize packaging, dependency, and CI workflow
3. externalize configuration and stabilize deployment
4. harden authentication and remove dynamic code execution
5. extract service boundaries and internal APIs
6. improve runtime reliability and admin UX

This order reduces migration risk while improving day-to-day maintainability early.

Non-Goals
---------

The following are intentionally not first-phase goals:

- full microservice decomposition
- immediate replacement of Flask only for fashion reasons
- wholesale rewrite of spiders and parsers
- aggressive database migration before operational pain is clear
- frontend-heavy reimplementation before API boundaries exist

These may become reasonable later, but they should not block the core modernization path.

Risk Register
-------------

+------------------------------------+----------+------------------------------------------+
| Risk                               | Severity | Mitigation                               |
+====================================+==========+==========================================+
| Dependency upgrade breaks crawl    | High     | baseline fixtures and staged rollout     |
+------------------------------------+----------+------------------------------------------+
| Python upgrade breaks legacy libs  | High     | lockfile, CI matrix, compatibility tests |
+------------------------------------+----------+------------------------------------------+
| Security fix changes login flow    | High     | admin bootstrap command and migration    |
+------------------------------------+----------+------------------------------------------+
| API extraction stalls delivery     | Medium   | keep templates during transition         |
+------------------------------------+----------+------------------------------------------+
| Queue or cache replacement drags   | Medium   | make infra replacement optional          |
+------------------------------------+----------+------------------------------------------+
| Rewrite scope grows uncontrollable | High     | phase gates and non-goal discipline      |
+------------------------------------+----------+------------------------------------------+

Success Criteria
----------------

The modernization effort should be considered successful when:

- new developers can set up and run the project from documentation alone
- CI reliably validates the supported runtime and code quality gates
- production configuration is fully externalized
- high-risk behaviors such as implicit admin bootstrap and arbitrary ``eval`` are removed
- task execution and admin operations are observable and debuggable
- the project can evolve without relying on a frozen legacy environment

Recommended First Milestone
---------------------------

If only one milestone is funded first, it should include:

- baseline test and smoke coverage
- ``pyproject.toml`` completion
- dependency and CI cleanup
- environment-based settings
- secure admin bootstrap
- replacement plan for ``eval``-based publish rules

This milestone gives the project a maintainable foundation without forcing a product rewrite.
