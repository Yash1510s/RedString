# OSINT Investigation Copilot

A terminal-based, evidence-grounded OSINT investigation tool that accepts a target domain, passively collects observable public intelligence (DNS, Certificate Transparency, HTTP/HTML metadata), normalizes findings, establishes deterministic entity relationships, and presents an interactive executive terminal dashboard and relationship graph.

---

## 🚀 Quick Start & Usage Commands

If you ever forget how to run the application, use these commands from the project root:

### 1. Run Direct Investigation
```powershell
.venv\Scripts\python.exe run.py example.com
```

### 2. Run Interactive Mode
```powershell
.venv\Scripts\python.exe run.py
```

### 3. Run Test Suite
```powershell
.venv\Scripts\pytest
```

---

## 🛠️ Environment Setup

If setting up on a new machine or environment:

```powershell
# Create Python virtual environment
python -m venv .venv

# Install dependencies
.venv\Scripts\pip install -r requirements.txt
```

---

## 🔑 Key Features Implemented

* **Passive OSINT Collection:**
  * **DNS Intelligence:** Queries `A`, `AAAA`, `MX`, `NS`, `TXT`, and `CNAME` records using `dnspython`.
  * **Certificate Transparency:** Passively queries public crt.sh logs to identify observable subdomains/SANs with wildcard normalization.
  * **Technology Detection:** Passively inspects HTTP headers (`Server`, `X-Powered-By`) and HTML tags (`<meta name="generator">`, framework assets) for React, Next.js, WordPress, Nginx, Cloudflare, etc.
* **Evidence Provenance Tracking:** Every finding links to an immutable evidence record (`E-001`, `E-002`, ...) with source, timestamp, and query details.
* **Finding Normalization:** Converts raw findings into standard `Finding` objects (`FND-001`, `FND-002`, ...) categorized by entity type.
* **Entity Correlation:** Generates deterministic relationships (`HAS_SUBDOMAIN`, `RESOLVES_TO`, `USES_NAMESERVER`, `USES_MAILSERVER`, `USES_TECHNOLOGY`).
* **Terminal Visualizations:**
  * High-contrast, theme-agnostic Rich terminal formatting.
  * **ASCII/Rich Relationship Graph:** Text-based tree view linking target domain to entities and evidence IDs.
  * **Executive Dashboard:** Collectors status, investigation metrics, and key findings overview.

---

## 📁 Project Structure

```text
RedString/
├── app/
│   ├── main.py              # CLI orchestrator & execution workflow
│   ├── cli/
│   │   └── interface.py     # High-contrast Rich terminal UI renderers
│   ├── collectors/
│   │   ├── dns.py           # Passive DNS collector
│   │   ├── certificates.py  # Certificate Transparency collector (crt.sh)
│   │   └── technologies.py  # Passive HTTP/HTML technology collector
│   ├── core/
│   │   ├── models.py        # Pydantic models (Investigation, Evidence, Finding, Relationship)
│   │   ├── validation.py    # Target domain validation rules
│   │   ├── evidence.py      # EvidenceStore provenance manager
│   │   ├── normalizer.py    # DataNormalizer finding entity converter
│   │   └── correlator.py    # DataCorrelator relationship generator
│   └── graph/
│       └── builder.py       # Terminal Rich relationship tree builder
├── tests/                   # Pytest unit test suite
├── legacy/                  # Legacy web & backend archives
├── pytest.ini
├── requirements.txt
└── run.py                   # Root execution entrypoint
```

---

## 🛡️ Safety & Ethical Scope

* **Passive Only:** Strictly public metadata queries. No port scanning, brute-forcing, or exploitation.
* **Target Validation:** Rejects IP literals, URLs, local hostnames, and credentials.
* **Fault Tolerance:** Individual collector failures or network timeouts generate warnings without crashing the investigation.
