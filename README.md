# RedString (OSINT Investigation Copilot)

An operational, evidence-grounded OSINT investigation web tool where analysts enter a domain, passively collect public intelligence (DNS, RDAP, Certificate Transparency, HTTP headers, GitHub metadata), correlate findings into a relationship graph, and generate audit-ready reports.

## Quick Start (Under 10 Commands)

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
Open [http://localhost:3000](http://localhost:3000) for the application, or [http://localhost:3000/_ui](http://localhost:3000/_ui) for the Design System Kitchen Sink.

---

## Architectural Principles & Safety
- **Passive Only (S1):** Strictly query-based and public metadata. No port scanning, brute-forcing, or exploits.
- **Strict SSRF Guard (S2):** Outbound HTTP calls resolve first and reject private/loopback/metadata IP ranges, ports other than 80/443, and redirect hops.
- **Target Validation (S3):** Accepts public domain names only.
- **Consent Gate (S4):** Requires explicit user confirmation of lawful purpose.
- **Evidence Provenance:** Every finding and relationship edge traces to an immutable raw evidence record with timestamp.
- **Grounded AI:** Summaries only cite validated finding IDs; works 100% offline with deterministic template fallback.

## Testing & Quality Assurance
- **Backend Tests:** `pytest backend/tests`
- **Backend Linting:** `ruff check backend` and `mypy backend`
- **Frontend Type Check:** `npm --prefix frontend run type-check`
- **Frontend Tests:** `npm --prefix frontend test`
- **Frontend Linting:** `npm --prefix frontend run lint`
