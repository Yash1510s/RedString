# Architectural Decision Log (ADR)

This file tracks foundational and operational decisions for the OSINT Investigation Copilot project, as mandated by `AGENTS.md`.

---

## ADR-001: Execution Environment and Package Management

- **Date:** 2026-09-29
- **Decision:** Use Python 3.13 standard virtual environment (`.venv`) with `pip` for backend, and Node.js v22 with `npm` for frontend.
- **Reason:** Machine has Python 3.13.2 and Node v22.14.0 natively available. Using standard venv + pip avoids missing global CLI tooling (e.g. `uv` was not preinstalled globally) and guarantees zero-friction reproducible setup.
- **Alternatives considered:** `uv` (requires extra global install), `poetry` (heavier overhead).

---

## ADR-002: Asynchronous Database Layer with SQLite & SQLAlchemy 2.x

- **Date:** 2026-09-29
- **Decision:** Use SQLite via Async SQLAlchemy (`aiosqlite`) and Alembic for migrations.
- **Reason:** Spec section 17 decision 3 & 4. Zero-setup requirement for local student deployment, portable to PostgreSQL if needed, async matches FastAPI and httpx coroutine loops.
- **Alternatives considered:** Sync SQLAlchemy (blocks async event loop), raw sqlite3 (no schema portability).

---

## ADR-003: Hybrid Workspace Layout and Design System Architecture

- **Date:** 2026-09-29
- **Decision:** Adopt the "Hybrid Workspace" layout defined in `UI_SPEC.md` with strict CSS variable tokens in `frontend/app/tokens.css` mapped to Tailwind CSS.
- **Reason:** Blends persistent evidence exploration (320px right panel), fast dense tabular scanning, and interactive Cytoscape relationship canvas. Strictly obeys 4px/6px radii, Okabe-Ito color-blind palette, and zero decorative noise.
- **Alternatives considered:** Standard multi-page SaaS dashboard, graph-only canvas.

---

## ADR-004: Swappable LLM Interface with Mandatory Deterministic Template Fallback

- **Date:** 2026-09-29
- **Decision:** Implement `LLMClient` provider interface with validation gates, and a 100% deterministic local template summary fallback when no API key is provided.
- **Reason:** Fulfills safety rule S9 and allows full local, offline, or CI execution without an external LLM dependency.
- **Alternatives considered:** Requiring an active API key to run investigations (violates offline spec requirements).

---

## ADR-005: Project Branding and Git Remote Repository

- **Date:** 2026-09-29
- **Decision:** Name the tool **RedString (OSINT Investigation Copilot)** and associate with the GitHub remote repository `https://github.com/Yash1510s/RedString.git` on branch `main`.
- **Reason:** Reflects the core metaphor of connecting evidence nodes with verifiable provenance lines ("red string" on an intelligence corkboard) while preserving the descriptive subtitle.
- **Alternatives considered:** Generic "OSINT Copilot" or "Resolvia".

---

## ADR-006: Async Storage Models, Entity Deduplication, and Strict SSRF Boundary

- **Date:** 2026-09-29
- **Decision:** Implement async SQLAlchemy 2.0 ORM models for investigations, entities, relations, evidence, and collector runs. When duplicate entities are observed, attributes are non-destructively merged and raw evidence rows are appended. Implement a pre-flight SSRF Guard and SafeHttpClient enforcing IP checks (blocking loopback, private LAN, link-local, cloud metadata `169.254.169.254`), ports 80/443 only, max 3 redirects, and 2 MB response limits.
- **Reason:** Fulfills core spec safety rules S2 & S3 and data model requirements (Sections 5.2, 5.3, 5.4). Guarantees that no collector can initiate unauthorized requests to private infrastructure or drop previous investigative evidence.
- **Alternatives considered:** Blocking SSRF at the proxy level (unsupported in zero-setup local deployments), destructive entity replacement (violates auditability).

---

## ADR-007: Interactive Cytoscape Relationship Canvas and Accessible Table Alternative

- **Date:** 2026-10-06
- **Decision:** Implement interactive Cytoscape.js graph canvas (`GraphView`) with Okabe-Ito colour-blind safe palette, distinct geometric shapes per entity type, dynamic Next.js client-side rendering (`ssr: false`), layout toggling (Force/Concentric), PNG export, and an integrated Accessible Table Alternative adhering to WCAG 2.2 AA.
- **Reason:** Fulfills Spec Section 14 Phase 6 and `UI_SPEC.md §3.3 & §5.3`. Ensures screen readers and keyboard users can inspect all nodes and edges identically to canvas users without relying on visual graph rendering alone.
- **Alternatives considered:** Canvas-only rendering (violates accessibility S11.7), SVG-only force graph (performance degraded with 300+ nodes).

---

## ADR-008: Read-Only System Diagnostics, Offline Demo Seeding, and Complete Route Hierarchy

- **Date:** 2026-10-06
- **Decision:** Implement a read-only diagnostics endpoint (`GET /api/system`) and frontend screen (`/settings`), an offline pre-correlated demo seeding endpoint (`POST /api/investigations/demo`) visibly labelled "Demo data", and a dedicated History management view (`/investigations`) with permanent delete capabilities.
- **Reason:** Fulfills Spec Section 14 Phase 9 and `UI_SPEC.md §5.2 & §5.4`. Provides deterministic offline presentation capability without live network requests, satisfies Rule S10 labelling requirements, and gives investigators transparent insight into rate limits and security boundaries.
- **Alternatives considered:** Live-only investigations (risks demo failure on conference networks), manual database seeding scripts.

---

## ADR-009: Cytoscape DOM Reconciliation Isolation and Multi-Entity Grounded Summary Synthesis

- **Date:** 2026-10-06
- **Decision:** Isolate Cytoscape canvas mounting into a dynamically managed vanilla sub-DOM container with CSS visibility toggling (`hidden`/`flex`) instead of conditional React JSX unmounting, backed by a `ResizeObserver` for robust re-renders on layout or tab changes. Expand deterministic grounded intelligence summary generation to cover 9 distinct entity types (DNS routing, nameservers, autonomous systems, mail security, perimeter technologies, codebases, certificates) with dual schema compatibility (`claim`/`text`) and automatic summary invalidation if collected during pending pipeline execution.
- **Reason:** Eliminates React runtime `removeChild` DOM reconciliation crashes triggered when Cytoscape modifies elements inside unmounting React containers. Ensures the accessible table view toggles instantly without remounting the canvas. Guarantees that analyst AI summaries provide comprehensive domain narrative breakdowns with direct verifiable finding citations (`[F-XXXXXX]`) rather than sparse 0-finding placeholders.
- **Alternatives considered:** Recreating Cytoscape instance on every table view toggle (slow, state loss, causes DOM detachment crashes), sparse summary text without breakdown.



