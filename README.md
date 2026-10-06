# RedString (OSINT Investigation Copilot)

An operational, evidence-grounded OSINT investigation web tool where analysts enter a domain, passively collect public intelligence (DNS, RDAP, Certificate Transparency, HTTP headers, GitHub metadata), correlate findings into a relationship graph, and generate audit-ready reports.

---

## ⚡ Quick Start (Under 10 Commands)

### 1. Backend Setup
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Navigate to **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 🧭 Key Features & Navigation

- **New Investigation (`/`)**: Domain target entry guarded by the lawful-purpose Consent Gate (Rule S4).
- **History (`/investigations`)**: Audit trail of previous investigations with search, filter, and permanent deletion (GDPR/privacy control). Includes a **"Load Demo Data"** action for instant offline presentations.
- **Investigation Workspace (`/investigations/[id]`)**:
  - **Overview**: High-level entity metric counters, execution milestones, and limitations.
  - **Graph**: Interactive Cytoscape.js canvas with Okabe-Ito colour-blind safe palette, distinct geometric shapes per entity type, Force/Concentric layouts, PNG export, and an integrated **Accessible Table Alternative** (WCAG 2.2 AA).
  - **Findings & Category Tabs**: DNS, RDAP, Certificates, Technologies, Repositories tables with search and sorting.
  - **Evidence Panel**: Persistent 320px right-hand inspector displaying immutable raw proofs, timestamps, and collector versions for any selected node or row.
  - **AI Summary**: Grounded summary engine with model/prompt version badges, markdown copy, regeneration, and clickable `[F-XXXXXX]` finding chips linking directly to raw evidence.
  - **Export Report**: Print-ready 13-section report (`/report`).
- **Settings & Diagnostics (`/settings`)**: Read-only inspection of active API integrations, rate-limit warnings, and security perimeter rules without leaking secrets.
- **Legal Documentation (`/legal/*`)**: Draft policies for Acceptable Use, Privacy, and Terms of Service.

---

## 🛡️ Safety & Non-Negotiable Rules

| ID | Constraint | Implementation Control |
|---|---|---|
| **S1** | Passive only | DNS queries, public RDAP/Whois, Certificate Transparency (crt.sh/certspotter), GitHub metadata, single GET of homepage. No port scans or exploits. |
| **S2** | SSRF Guard | Outbound HTTP requests resolve IPs first; reject loopback, private RFC-1918, link-local, cloud metadata (`169.254.169.254`), non-standard ports, and redirects. |
| **S3** | Target validation | Strict regex + `tldextract` validation; IP literals, localhost, and credentials rejected. |
| **S4** | Consent gate | API rejects requests without `consent=true`. |
| **S5** | No secrets hunting | GitHub collector fetches repository metadata and README domain-mentions only. |
| **S6** | No personal profiling | RDAP parser strips personal names, telephone numbers, and addresses. |
| **S7** | Respect limits | 24-hour response caching (`http_cache`) and throttling. |
| **S8** | Secrets safety | All credentials loaded via `.env`; never committed or logged. |
| **S9** | Grounded AI | Output strictly validated against stored finding IDs. 100% functional offline with deterministic template fallback. |
| **S10** | No fabricated data | Sample and synthetic data explicitly labelled `[Demo Data]`. |
| **S11** | Honest claims | Findings classified as "observed" or "inferred", never "proven". |

---

## 🧪 Verification & Testing

```bash
# Backend unit tests (87 tests covering collectors, correlation, AI, and SSRF guard):
cd backend
.venv\Scripts\pytest

# Frontend type checks and linting:
cd frontend
npm run type-check
npm run lint

# Production build validation:
npm run build
```
