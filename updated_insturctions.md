# OSINT Investigation Copilot

## Phased Implementation Specification for a Terminal-Based Mini Project

You are a coding agent helping me build a **college-level OSINT mini project**.

The project is intentionally scoped as a **working proof-of-concept**, not a production-grade intelligence platform.

The goal is to build something that is:

* actually runnable,
* understandable by a student,
* demonstrable to a professor,
* modular enough to extend later,
* visually polished in the terminal,
* and technically coherent.

Do NOT over-engineer the project.

Do NOT turn this into an enterprise OSINT platform.

Do NOT add unnecessary infrastructure, microservices, authentication, Docker, Kubernetes, PostgreSQL, React/Next.js, cloud deployment, or dozens of external APIs unless explicitly requested later.

The project should be developed incrementally. Each MVP/phase must produce a working application before moving to the next phase.

---

# 1. PROJECT TITLE

**OSINT Investigation Copilot: An AI-Assisted Platform for Public-Source Intelligence Collection, Correlation and Visualization**

Short description:

> A terminal-based AI-assisted OSINT tool that accepts a domain as a target, collects selected publicly observable information using passive/public sources, normalizes the findings, establishes basic relationships between entities, presents the results in a readable terminal interface, and optionally generates an evidence-aware AI summary and investigation report.

---

# 2. IMPORTANT SCOPE

The project is a **mini-project prototype**.

The current implementation should focus primarily on:

**Target Type**

* Domain only

**OSINT Sources**

* DNS
* Certificate Transparency
* Basic HTTP/HTML technology detection

**Core intelligence features**

* Finding normalization
* Evidence/source tracking
* Basic entity relationships
* Terminal relationship visualization
* Investigation summary
* Optional AI-assisted summary
* Basic report generation

The following are NOT required for the initial implementation:

* Company investigations
* Username investigations
* Social media investigations
* Dark web investigations
* Email breach databases
* Vulnerability scanning
* Port scanning
* Exploitation
* Credential attacks
* Authentication bypass
* Active penetration testing
* Large-scale crawling
* Distributed collection
* Complex ML models
* Custom LLM training
* Production deployment

These may be future extensions.

---

# 3. IMPORTANT DEVELOPMENT RULE

Implement the project in the following phases.

**DO NOT IMPLEMENT ALL PHASES AT ONCE.**

First build MVP 1.

Make sure MVP 1 works.

Then MVP 2.

Make sure MVP 2 works.

Continue sequentially.

At the end of every phase:

1. Run/test the application.
2. Fix errors.
3. Explain what was implemented.
4. Explain how to run it.
5. Show an example of expected output.
6. Clearly state what remains for the next phase.

Do not move to the next phase automatically if the current phase is broken.

---

# 4. TECHNOLOGY STACK

Use Python as the primary language.

Recommended stack:

* Python 3.11+
* Rich — terminal UI
* dnspython — DNS queries
* httpx — HTTP requests
* BeautifulSoup4 — basic HTML analysis
* SQLite — local storage
* SQLAlchemy — database abstraction
* Pydantic — data validation
* python-dotenv — configuration
* Optional LLM SDK/API for AI phase
* Jinja2 — report templates
* WeasyPrint or another simple HTML-to-PDF mechanism for the report phase if practical

Avoid unnecessary dependencies.

If a feature can be implemented with Python's standard library, prefer that over adding another dependency.

---

# 5. HIGH-LEVEL ARCHITECTURE

The intended architecture is:

```text
                    USER
                     │
                     ▼
              TERMINAL INTERFACE
                     │
                     ▼
                ORCHESTRATOR
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
         DNS         CT       HTTP/HTML
      Collector   Collector   Collector
          │          │          │
          └──────────┼──────────┘
                     ▼
               DATA NORMALIZER
                     │
                     ▼
                EVIDENCE STORE
                     │
                     ▼
               CORRELATION
                     │
              ┌──────┴──────┐
              ▼             ▼
        RELATIONSHIP      AI ANALYSIS
           GRAPH
              │             │
              └──────┬──────┘
                     ▼
               REPORT OUTPUT
```

The architecture should be modular.

Collectors must not contain database logic.

The CLI must not contain collector logic.

The AI module must not directly perform OSINT collection.
\

---

# 6. PROJECT STRUCTURE

Create a clean structure similar to:

```text
osint-investigation-copilot/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   └── interface.py
│   │
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── dns.py
│   │   ├── certificates.py
│   │   └── technologies.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── normalizer.py
│   │   ├── evidence.py
│   │   ├── correlator.py
│   │   └── orchestrator.py
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── models.py
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   └── builder.py
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   └── copilot.py
│   │
│   └── reports/
│       ├── __init__.py
│       ├── generator.py
│       └── templates/
│
├── data/
│   └── investigations/
│
├── reports/
│
├── tests/
│
├── .env.example
├── requirements.txt
├── README.md
└── run.py
```

The exact structure can be simplified if necessary, but preserve separation of responsibilities.

---

# 7. CORE DATA CONCEPTS

The application should eventually work with three primary concepts.

## Entity

An entity represents something discovered.

Examples:

```text
DOMAIN
SUBDOMAIN
IP_ADDRESS
MAIL_SERVER
NAME_SERVER
CERTIFICATE
TECHNOLOGY
```

Each entity should have at minimum:

```text
id
type
value
```

---

## Evidence

Evidence explains where a finding came from.

Each evidence item should contain:

```text
id
source
finding
source_reference
collected_at
description
```

Example:

```text
Evidence ID: E-001

Finding:
93.184.216.34

Source:
DNS

Reference:
A record query for example.com

Collected:
2026-09-29 23:15:00
```

---

## Relationship

A relationship connects entities.

Example:

```text
example.com
    │
    └── HAS_SUBDOMAIN
            │
            ▼
      api.example.com
```

A relationship should contain:

```text
source_entity
relationship_type
target_entity
evidence_id
```

---

# 8. MVP 1 — BASIC TERMINAL APPLICATION

## Goal

Create a working terminal application that accepts a domain and displays a clean investigation header.

Example:

```text
╭────────────────────────────────────────────╮
│       OSINT INVESTIGATION COPILOT          │
╰────────────────────────────────────────────╯

Target: example.com
Type:   Domain

Investigation started...
```

## Requirements

Implement:

* Python entry point
* Rich terminal interface
* Domain input
* Basic domain validation
* Investigation ID
* Timestamp
* Clean output
* Graceful Ctrl+C handling
* Error handling for invalid input

Example:

```bash
python run.py
```

or:

```bash
python run.py example.com
```

Both approaches may be supported.

## Do NOT implement yet

* DNS
* CT
* AI
* database
* graph
* reports

The purpose of MVP 1 is simply to establish the application shell.

---

# 9. MVP 2 — DNS COLLECTOR

## Goal

Add the first actual OSINT collector.

Use `dnspython`.

Collect:

```text
A
AAAA
MX
NS
TXT
CNAME
```

Not every domain will have every record.

The collector must handle missing records gracefully.

Example output:

```text
DNS INTELLIGENCE

A Records
  • 93.184.216.34

MX Records
  • mail.example.com

Name Servers
  • ns1.example.com
  • ns2.example.com
```

## Requirements

Create a reusable:

```python
DNSCollector
```

with a method similar to:

```python
collect(domain)
```

It should return structured data rather than printing directly.

Example conceptual result:

```python
{
    "collector": "dns",
    "target": "example.com",
    "findings": [...]
}
```

The CLI is responsible for displaying it.

## Important

Do not make the collector dependent on the terminal UI.

---

# 10. MVP 3 — EVIDENCE MODEL

## Goal

Introduce evidence tracking.

Every finding produced by the DNS collector should have:

```text
finding
source
source_reference
timestamp
```

Example:

```text
E-001
Finding: 93.184.216.34
Type: A_RECORD
Source: DNS
Reference: example.com A query
Collected: 29 Sep 2026
```

Implement a simple evidence model.

At this stage, SQLite may be introduced.

However, if database implementation becomes unnecessary complexity, JSON persistence is acceptable temporarily.

The architecture must allow SQLite to be introduced later.

---

# 11. MVP 4 — CERTIFICATE TRANSPARENCY

## Goal

Add passive Certificate Transparency intelligence.

Given:

```text
example.com
```

query an appropriate public Certificate Transparency source.

Extract publicly observable hostnames/SANs.

For example:

```text
example.com
www.example.com
api.example.com
mail.example.com
```

Normalize wildcard entries.

Example:

```text
*.example.com
```

should be interpreted as the parent domain relationship rather than blindly displayed as a normal hostname.

## Output

```text
CERTIFICATE INTELLIGENCE

Certificate-related hostnames:

  • example.com
  • www.example.com
  • api.example.com
  • mail.example.com
```

Each discovered hostname should become evidence.

Important:

Do not claim that this represents every subdomain belonging to the domain.

Use wording such as:

> Publicly observable hostnames identified through Certificate Transparency.

---

# 12. MVP 5 — BASIC TECHNOLOGY DETECTION

## Goal

Perform simple passive HTTP/HTML analysis.

Request:

```text
https://example.com
```

with a reasonable timeout.

Inspect:

### HTTP headers

Examples:

```text
Server
X-Powered-By
Via
```

### HTML

Look for recognizable indicators such as:

```text
<meta name="generator">
/wp-content/
/_next/
/static/
/jquery
React indicators
Vue indicators
```

Do not attempt to build a full Wappalyzer replacement.

The goal is only a basic proof-of-concept.

Example:

```text
TECHNOLOGIES

  • nginx
  • React
```

Each detection must record its basis.

Example:

```text
Technology: nginx
Evidence: Server HTTP header

Technology: React
Evidence: recognizable HTML/JavaScript indicator
```

Avoid presenting weak detection as absolute fact.

---

# 13. MVP 6 — NORMALIZATION

## Goal

Make findings from different collectors follow one common structure.

For example:

```python
Finding(
    entity_type="SUBDOMAIN",
    value="api.example.com",
    source="CERTIFICATE_TRANSPARENCY",
    evidence="CT certificate SAN",
    collected_at=...
)
```

All collectors should eventually return normalized findings.

This is important because the correlation engine should not care whether a finding came from DNS, CT, or HTTP.

---

# 14. MVP 7 — BASIC CORRELATION

## Goal

Create relationships between discovered entities.

Implement only simple deterministic relationships.

Examples:

```text
example.com
    └── HAS_SUBDOMAIN
            └── api.example.com
```

```text
example.com
    └── RESOLVES_TO
            └── 93.184.216.34
```

```text
example.com
    └── USES_TECHNOLOGY
            └── nginx
```

Do NOT implement machine learning correlation.

Do NOT implement graph databases.

Do NOT attempt complex inference.

Use straightforward rules.

---

# 15. MVP 8 — TERMINAL INVESTIGATION VIEW

## Goal

Combine everything into one polished terminal output.

Example:

```text
╭──────────────────────────────────────────────╮
│           OSINT INVESTIGATION               │
│                                              │
│ Target: example.com                         │
╰──────────────────────────────────────────────╯

COLLECTORS

  DNS                         ✓
  Certificate Transparency   ✓
  Technology Detection       ✓

────────────────────────────────────────────────

STATISTICS

  Entities       17
  Subdomains      6
  Technologies    3
  Evidence       21
  Relationships  14

────────────────────────────────────────────────

KEY FINDINGS

  • 6 publicly observable hostnames
  • 3 technologies detected
  • 2 DNS infrastructure records
```

Use Rich tables/panels/status indicators.

Keep it readable.

Do not flood the screen with raw JSON.

---

# 16. MVP 9 — TERMINAL RELATIONSHIP GRAPH

## Goal

Render a simple text-based relationship graph.

Example:

```text
example.com
│
├── api.example.com
│
├── mail.example.com
│
├── www.example.com
│
├── 93.184.216.34
│
├── nginx
│
└── React
```

If useful, provide a relationship-specific view:

```text
example.com
│
├── HAS_SUBDOMAIN ── api.example.com
│
├── RESOLVES_TO ──── 93.184.216.34
│
└── USES_TECHNOLOGY ─ React
```

This is enough for the initial prototype.

A graphical UI such as React Flow is NOT required.

---

# 17. MVP 10 — INVESTIGATION COMMAND MODE

Add an interactive CLI mode.

After an investigation:

```text
osint>
```

Support commands such as:

```text
summary
findings
dns
subdomains
technologies
graph
evidence
analyze
report
export
help
exit
```

Example:

```text
osint> graph
```

displays the relationship graph.

Example:

```text
osint> evidence api.example.com
```

displays:

```text
Entity:
api.example.com

Type:
SUBDOMAIN

Source:
Certificate Transparency

Evidence:
Certificate SAN entry

Collected:
29 Sep 2026 23:18 IST
```

This makes the project feel like a proper terminal tool without requiring a frontend.

---

# 18. MVP 11 — AI INVESTIGATION SUMMARY

## Goal

Add an AI-assisted analysis layer.

The AI should NOT perform the collection.

The collectors collect information.

The correlation engine structures it.

The AI receives the structured findings.

Input should resemble:

```json
{
    "target": "example.com",
    "entities": [...],
    "relationships": [...],
    "evidence": [...]
}
```

Use an LLM API only if credentials are available.

Create a configuration such as:

```text
LLM_API_KEY=
LLM_MODEL=
```

in `.env`.

## AI instructions

The AI must:

1. Use only supplied evidence.
2. Never invent findings.
3. Clearly distinguish observations from interpretations.
4. Mention supporting evidence IDs for important findings.
5. Mention limitations.
6. Avoid claiming that the investigation is exhaustive.
7. Avoid making unsupported security claims.

Example output:

```text
AI INVESTIGATION SUMMARY

Executive Summary
-----------------
The investigation identified several publicly observable
hostnames associated with the target through Certificate
Transparency records.

Key Observations
----------------
1. Six hostnames were identified through CT data.
   Evidence: E-004 through E-009

2. The target returned an nginx server header.
   Evidence: E-015

Limitations
-----------
The investigation used a limited set of passive sources
and does not represent a complete inventory of the target's
infrastructure.
```

If the LLM is unavailable, the application must still work.

Provide a fallback non-AI summary.

---

# 19. MVP 12 — BASIC REPORT GENERATION

## Goal

Generate an investigation report.

At minimum:

```text
reports/
└── example.com/
    ├── report.html
    └── investigation.json
```

PDF generation can be added if practical.

Report sections:

```text
1. Target Information
2. Investigation Timestamp
3. Sources Used
4. DNS Findings
5. Certificate Findings
6. Technology Findings
7. Relationships
8. Key Observations
9. Evidence References
10. Limitations
```

The report should be generated from the structured investigation data, not manually assembled strings scattered throughout the application.

---

# 20. MVP 13 — SQLITE PERSISTENCE

If not already implemented earlier, move persistence to SQLite.

Store:

```text
investigations
entities
findings/evidence
relationships
```

Minimum conceptual schema:

```text
investigations
----------------
id
target
target_type
created_at
status


entities
----------------
id
investigation_id
type
value


evidence
----------------
id
investigation_id
entity_id
source
reference
description
collected_at


relationships
----------------
id
investigation_id
source_entity_id
relationship_type
target_entity_id
evidence_id
```

Do not over-normalize the database.

---

# 21. OPTIONAL MVP 14 — GITHUB INTELLIGENCE

Only implement this if the previous stages are stable.

Add public GitHub intelligence.

Possible scope:

* Public repositories associated with a company/organization
* Public repositories where the target domain is referenced
* Repository name
* URL
* Description
* Language
* Topics

Do not implement:

* Private repository access
* Credential collection
* Secret extraction
* Token hunting
* Aggressive repository crawling

The output should remain public-source intelligence.

---

# 22. OPTIONAL MVP 15 — COMPANY TARGET

Only after domain investigations work.

Allow:

```text
Target Type:
1. Domain
2. Company
```

For company targets, perform only a limited public-source lookup and then map the result into the same entity/evidence/relationship model.

Do not redesign the entire application around companies.

---

# 23. OPTIONAL MVP 16 — BETTER GRAPH VISUALIZATION

This is a future extension.

Potential options:

* Rich tree visualization
* Graphviz-generated image
* Export graph to DOT
* Interactive web UI

Do NOT introduce React/Next.js merely because a graph would look better.

The terminal version is sufficient for the mini-project.

---

# 24. OPTIONAL MVP 17 — WEB FRONTEND

Only implement this if significant time remains.

Potential future architecture:

```text
Terminal CLI
      │
      ▼
Core Investigation Engine
      ▲
      │
FastAPI
      │
      ▼
Next.js Frontend
```

The important requirement is that the frontend should consume the same investigation engine/data model.

Do not rewrite the project to accommodate the frontend.

---

# 25. COMMAND-LINE EXPERIENCE

The final CLI should support something similar to:

```bash
python run.py example.com
```

for a quick investigation.

And:

```bash
python run.py
```

for interactive mode.

Interactive mode:

```text
╭─────────────────────────────────────────────╮
│         OSINT INVESTIGATION COPILOT         │
╰─────────────────────────────────────────────╯

Target type:
> Domain

Target:
> example.com

Select collectors:

  [x] DNS
  [x] Certificate Transparency
  [x] Technology Detection

Start investigation? [Y/n]
> y
```

Then:

```text
Collecting...

DNS                         ✓
Certificate Transparency   ✓
Technology Detection       ✓
Normalization               ✓
Correlation                 ✓

Investigation complete.
```

---

# 26. ERROR HANDLING

The tool must never crash just because one collector fails.

For example:

```text
DNS                         ✓ COMPLETE
Certificate Transparency   ✓ COMPLETE
Technology Detection       ⚠ FAILED
```

Then:

```text
Investigation completed with partial results.

Technology Detection:
HTTP request timed out.
```

The remaining investigation should still be available.

---

# 27. CACHING / RATE LIMITING

Keep this simple.

Do not hammer public services.

Implement reasonable:

* request timeouts
* exception handling
* basic delays where appropriate
* optional local caching

Do not perform aggressive enumeration.

---

# 28. TESTING

At minimum create tests for:

```text
Domain validation
DNS parsing
Wildcard normalization
Finding normalization
Relationship generation
```

Example:

```text
tests/
├── test_validation.py
├── test_dns.py
├── test_normalizer.py
└── test_correlator.py
```

Tests do not need to be extensive.

---

# 29. README

Create a simple README containing:

```text
# OSINT Investigation Copilot

## Overview

## Features

## Architecture

## Installation

## Usage

## Example Output

## Project Structure

## Limitations

## Future Work
```

Be honest about limitations.

Do not claim that the tool performs exhaustive OSINT.

---

# 30. SECURITY / ETHICAL SCOPE

This is a passive/public-source OSINT educational project.

The tool should focus on:

* Public DNS information
* Public Certificate Transparency information
* Public HTTP/HTML metadata
* Public repository information
* Publicly observable relationships

Do not implement:

* credential attacks
* authentication bypass
* exploitation
* unauthorized access
* brute force
* vulnerability exploitation
* private data acquisition

The project is an intelligence aggregation and visualization prototype, not a penetration-testing tool.

---

# 31. PRIORITY ORDER

If time becomes limited, prioritize exactly in this order:

### CRITICAL

```text
1. CLI
2. Domain input
3. DNS collector
4. Certificate Transparency collector
5. Technology collector
6. Normalized findings
7. Evidence
8. Basic relationships
9. Terminal summary
```

### HIGH

```text
10. Terminal relationship tree
11. SQLite
12. Interactive commands
13. AI summary
```

### MEDIUM

```text
14. HTML report
15. PDF report
16. Tests
17. Better error handling
```

### LOW / FUTURE

```text
18. GitHub
19. Company targets
20. Advanced graph
21. Web frontend
22. Additional OSINT sources
23. Advanced correlation
24. Advanced confidence scoring
```

If time runs out, STOP at the highest completed level.

A smaller working project is preferable to a larger unfinished one.

---

# 32. DEFINITION OF MVP

The first meaningful MVP is complete when this works:

```bash
python run.py example.com
```

and produces:

```text
OSINT INVESTIGATION

Target: example.com

DNS
✓ A records
✓ MX records
✓ NS records

CERTIFICATE TRANSPARENCY
✓ Publicly observable hostnames

TECHNOLOGY
✓ Basic HTTP/HTML indicators

EVIDENCE
✓ Findings linked to sources

RELATIONSHIPS
✓ Domain → subdomain
✓ Domain → IP
✓ Domain → technology

SUMMARY
✓ Investigation statistics

GRAPH
✓ Terminal relationship tree
```

At this point, STOP.

Do not continue automatically.

This is the first usable project milestone.

---

# 33. AGENT BEHAVIOR

As the coding agent:

* Prefer simple working code over sophisticated architecture.
* Do not introduce technologies that are not necessary.
* Do not create abstractions before they are needed.
* Do not implement future phases prematurely.
* Do not rewrite working components unnecessarily.
* Keep collector modules independent.
* Keep data structures consistent.
* Keep the CLI readable.
* Explain important implementation decisions.
* Test every phase before moving forward.
* If an external API is unreliable, provide a graceful fallback.
* Never fabricate OSINT findings for the sake of a demo.
* Clearly distinguish real collected data from mock/test data.

When I say:

> "Implement MVP 1"

implement only MVP 1.

When I say:

> "Implement MVP 2"

implement only MVP 2 and integrate it with the existing working MVP.

Continue this pattern for every subsequent MVP.

---

# 34. FIRST TASK

For now, **do not implement the entire project**.

Start only with:

**MVP 1 — Basic Terminal Application**

Your first response should:

1. Inspect the environment/project directory.
2. Determine whether a project already exists.
3. Create the required initial structure.
4. Set up the Python environment/dependencies.
5. Implement the CLI shell.
6. Implement domain validation.
7. Implement investigation ID/timestamp generation.
8. Run the application.
9. Demonstrate successful execution.
10. Explain what was created.
11. Stop and wait for my instruction for MVP 2.

Do not implement DNS or any later feature until I explicitly ask for the next MVP.
