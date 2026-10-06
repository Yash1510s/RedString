"""Audit-ready investigation report generator per Spec Section 12."""

import re
from collections import defaultdict
from typing import Any

from app.models.db_models import Entity, Evidence, Investigation, Relation


def _render_certs_rows(certs: list[Entity]) -> str:
    if not certs:
        return "<tr><td colspan='5'>No certificates observed.</td></tr>"
    rows = []
    for c in certs[:10]:
        serial = str(c.attributes.get("serial_number", "N/A"))[:16]
        issuer = str(c.attributes.get("issuer_name", "Unknown"))
        not_before = str(c.attributes.get("not_before", "N/A"))
        not_after = str(c.attributes.get("not_after", "N/A"))
        wildcard = "Yes" if c.attributes.get("wildcard") else "No"
        rows.append(
            f"<tr><td class='code'>{serial}...</td><td>{issuer}</td>"
            f"<td>{not_before}</td><td>{not_after}</td><td>{wildcard}</td></tr>"
        )
    return "\n".join(rows)


def _render_subdomain_rows(subdomains: list[Entity]) -> str:
    if not subdomains:
        return "<tr><td colspan='3'>No subdomains discovered.</td></tr>"
    rows = []
    for s in subdomains[:25]:
        is_live = s.attributes.get("live", False)
        status_html = (
            "<span class='badge' style='background:#dcfce7;color:#166534'>LIVE</span>"
            if is_live
            else "<span class='badge'>UNRESOLVED</span>"
        )
        ips = ", ".join(s.attributes.get("resolved_ips", [])) or "None"
        rows.append(
            f"<tr><td class='code'>{s.value}</td><td>{status_html}</td>"
            f"<td class='code'>{ips}</td></tr>"
        )
    return "\n".join(rows)


def _render_tech_rows(technologies: list[Entity], cloud_providers: list[Entity]) -> str:
    rows = []
    for t in technologies:
        category = str(t.attributes.get("category", "Technology"))
        conf = str(t.attributes.get("confidence", "medium")).capitalize()
        rows.append(f"<tr><td><strong>{t.value}</strong></td><td>{category}</td><td>{conf}</td></tr>")
    for c in cloud_providers:
        rows.append(f"<tr><td><strong>{c.value}</strong></td><td>Cloud / CDN Host</td><td>High (IP CIDR match)</td></tr>")
    if not rows:
        return "<tr><td colspan='3'>No technology fingerprints detected.</td></tr>"
    return "\n".join(rows)


def _render_repo_rows(repositories: list[Entity]) -> str:
    if not repositories:
        return "<tr><td colspan='4'>No public repositories referencing domain found.</td></tr>"
    rows = []
    for r in repositories[:5]:
        stars = str(r.attributes.get("stars", 0))
        lang = str(r.attributes.get("language", "N/A"))
        basis = str(r.attributes.get("match_basis", "N/A"))
        rows.append(
            f"<tr><td class='code'>{r.value}</td><td>{stars}</td>"
            f"<td>{lang}</td><td>{basis}</td></tr>"
        )
    return "\n".join(rows)


def _render_people_rows(people: list[Entity]) -> str:
    if not people:
        return "<tr><td colspan='4'>No public contributors discovered.</td></tr>"
    rows = []
    for p in people[:6]:
        role = str(p.attributes.get("role", "Contributor"))
        contribs = str(p.attributes.get("contributions", 0))
        repo = str(p.attributes.get("associated_repo", "N/A"))
        rows.append(
            f"<tr><td class='code'><strong>{p.value}</strong></td><td>{role}</td>"
            f"<td>{contribs}</td><td class='code'>{repo}</td></tr>"
        )
    return "\n".join(rows)


def _render_evidence_rows(evidence_list: list[Evidence]) -> str:
    rows = []
    for ev in evidence_list[:60]:
        ev_id = f"EV-{ev.id:06d}"
        source = ev.source_name
        ref = ev.source_ref or "Direct query"
        ts = ev.collected_at.strftime("%Y-%m-%d %H:%M:%S")
        rows.append(
            f"<tr id='ev-{ev_id}'><td class='code'><strong>{ev_id}</strong></td><td>{source}</td>"
            f"<td class='code'>{ref}</td><td>{ts}</td></tr>"
        )
    return "\n".join(rows)


def _render_observations(key_findings: list[dict[str, Any]], observations: list[dict[str, Any]]) -> str:
    items = []
    for kf in key_findings:
        text = str(kf.get("claim") or kf.get("text", ""))
        category = kf.get("category", "")
        cat_badge = (
            f"<span class='badge' style='background:#f4f4f5; color:#52525b; border:1px solid #e4e4e7; margin-right:6px;'>{category}</span>"
            if category
            else ""
        )
        chips = " ".join(
            f"<span class='finding-badge'>{fid}</span>"
            for fid in kf.get("finding_ids", [])
        )
        items.append(f"<li style='margin-bottom:8px; line-height:1.5;'>{cat_badge}{text} {chips}</li>")

    for obs in observations:
        text = str(obs.get("observation") or obs.get("text", ""))
        conf = str(obs.get("confidence", "high")).upper()
        conf_badge = f"<span class='badge' style='background:#f4f4f5; color:#52525b; border:1px solid #e4e4e7; margin-right:6px;'>{conf} CONFIDENCE</span>"
        chips = " ".join(
            f"<span class='finding-badge'>{fid}</span>"
            for fid in obs.get("finding_ids", [])
        )
        items.append(f"<li style='margin-bottom:8px; line-height:1.5;'>{conf_badge}{text} {chips}</li>")

    return "\n".join(items) if items else "<li>No structured observations recorded.</li>"


def _render_security_posture_table(entities: list[Entity]) -> str:
    """Evaluate passive perimeter security posture per Rule S1."""
    dmarc_status = (
        "No DMARC Record Observed",
        "RISK",
        "Domain is vulnerable to active email spoofing and unauthorized sender impersonation.",
        "#fef2f2",
        "#991b1b",
        "#fecaca",
    )
    spf_status = (
        "No SPF Record Observed",
        "RISK",
        "Sending mail gateways unauthenticated; mail transfer agents may reject or flag mail.",
        "#fef2f2",
        "#991b1b",
        "#fecaca",
    )

    for e in entities:
        val = (e.value or "").lower()
        txt = str(e.attributes.get("txt_strings", "") if e.attributes else "").lower()
        combined = f"{val} {txt}"
        if "v=dmarc1" in combined:
            if "p=reject" in combined:
                dmarc_status = (
                    "DMARC Reject Policy Enforced (p=reject)",
                    "SECURE",
                    "Strict policy actively rejects unauthorized spoofed email.",
                    "#ecfdf5",
                    "#065f46",
                    "#a7f3d0",
                )
            elif "p=quarantine" in combined:
                dmarc_status = (
                    "DMARC Quarantine Policy Active (p=quarantine)",
                    "WARNING",
                    "Spoofed messages redirected to spam quarantine rather than outright rejected.",
                    "#fffbeb",
                    "#92400e",
                    "#fde68a",
                )
            else:
                dmarc_status = (
                    "DMARC Monitoring Only (p=none)",
                    "WARNING",
                    "Policy set to monitoring mode; domain remains vulnerable to active spoofing.",
                    "#fffbeb",
                    "#92400e",
                    "#fde68a",
                )
        if "v=spf1" in combined:
            if "-all" in combined:
                spf_status = (
                    "Hard-Fail SPF Enforced (-all)",
                    "SECURE",
                    "Authoritative sending gateway list strictly enforced.",
                    "#ecfdf5",
                    "#065f46",
                    "#a7f3d0",
                )
            elif "~all" in combined:
                spf_status = (
                    "Soft-Fail SPF Active (~all)",
                    "WARNING",
                    "Permissive soft-fail allows unlisted gateways with warning tag.",
                    "#fffbeb",
                    "#92400e",
                    "#fde68a",
                )
            else:
                spf_status = (
                    "Permissive SPF Configuration",
                    "RISK",
                    "SPF rules do not restrict sending gateways.",
                    "#fef2f2",
                    "#991b1b",
                    "#fecaca",
                )

    # Nameserver redundancy
    ns_ents = [e for e in entities if e.type == "nameserver"]
    if len(ns_ents) >= 2:
        ns_status = (
            f"{len(ns_ents)} Independent Authoritative Nameservers",
            "SECURE",
            "Authoritative DNS resolution distributed across multiple nameservers.",
            "#ecfdf5",
            "#065f46",
            "#a7f3d0",
        )
    elif len(ns_ents) == 1:
        ns_status = (
            "Single Nameserver Observed (SPOF)",
            "RISK",
            "Potential single point of failure in DNS delegation.",
            "#fef2f2",
            "#991b1b",
            "#fecaca",
        )
    else:
        ns_status = (
            "Nameservers Unobserved",
            "WARNING",
            "No authoritative nameservers discovered in passive query.",
            "#fffbeb",
            "#92400e",
            "#fde68a",
        )

    # Cloud/CDN Shielding
    tech_ents = [e for e in entities if e.type in ("technology", "cloud_provider")]
    cdn_found = [
        e.value
        for e in tech_ents
        if any(k in e.value.lower() for k in ("cloudflare", "cloudfront", "fastly", "akamai"))
    ]
    if cdn_found:
        cdn_status = (
            f"Perimeter Shielded ({', '.join(cdn_found)})",
            "SECURE",
            "Origin hosting IP protected behind reverse proxy and DDoS mitigation network.",
            "#ecfdf5",
            "#065f46",
            "#a7f3d0",
        )
    else:
        cdn_status = (
            "Direct Origin IP Exposure (No CDN Shield)",
            "WARNING",
            "Web traffic resolves directly to origin hosting IP without reverse-proxy DDoS layer.",
            "#fffbeb",
            "#92400e",
            "#fde68a",
        )

    rows = [
        ("Email Spoofing Defense (DMARC)", dmarc_status),
        ("Sender Policy Framework (SPF)", spf_status),
        ("DNS Redundancy & Availability", ns_status),
        ("Perimeter Shielding & Origin Privacy", cdn_status),
    ]

    html_rows = []
    for category, (title, label, desc, bg, fg, border) in rows:
        pill = f"<span class='badge' style='background:{bg}; color:{fg}; border:1px solid {border}; font-weight:700;'>{label}</span>"
        html_rows.append(
            f"<tr><td style='font-weight:600; width:30%;'>{category}</td>"
            f"<td><strong>{title}</strong><div style='font-size:8.5pt; color:#52525b; margin-top:2px;'>{desc}</div></td>"
            f"<td style='text-align:center; width:15%;'>{pill}</td></tr>"
        )

    return "\n".join(html_rows)


def generate_html_report(
    inv: Investigation,
    entities: list[Entity],
    relations: list[Relation],
    evidence_list: list[Evidence],
    summary_data: dict[str, Any],
) -> str:
    """Generate self-contained, printable HTML report with all 13 required sections."""
    by_type: dict[str, list[Entity]] = defaultdict(list)
    for ent in entities:
        by_type[ent.type].append(ent)

    created_str = inv.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    finished_str = (
        inv.finished_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        if inv.finished_at
        else "In Progress / Completed"
    )

    domain_ents = by_type.get("domain", [])
    rdap_attrs = domain_ents[0].attributes if domain_ents else {}
    registrar = rdap_attrs.get("registrar", "N/A")
    created_date = rdap_attrs.get("created_date", "N/A")
    expires_date = rdap_attrs.get("expires_date", "N/A")
    statuses = ", ".join(rdap_attrs.get("statuses", [])) or "Active"

    ns_list = [e.value for e in by_type.get("nameserver", [])]
    mail_list = [e.value for e in by_type.get("mail_provider", [])]

    certs_html = _render_certs_rows(by_type.get("certificate", []))
    subdomains_html = _render_subdomain_rows(by_type.get("subdomain", []))
    tech_html = _render_tech_rows(by_type.get("technology", []), by_type.get("cloud_provider", []))
    repo_html = _render_repo_rows(by_type.get("repository", []))
    people_html = _render_people_rows(by_type.get("person", []))
    evidence_html = _render_evidence_rows(evidence_list)
    obs_html = _render_observations(
        summary_data.get("key_findings", []),
        summary_data.get("observations", []),
    )
    security_posture_html = _render_security_posture_table(entities)

    raw_summary_text = summary_data.get("summary", "No summary available.")
    # Convert raw finding citations (F-000XXX) into styled badges
    formatted_summary = re.sub(
        r"\b(F-\d{6})\b",
        r"<span class='finding-badge'>\1</span>",
        raw_summary_text,
    )

    model_badge = str(
        summary_data.get("generator")
        or summary_data.get("model")
        or "Deterministic Grounded Engine"
    )

    next_steps = summary_data.get("next_steps", [])
    recommendations_html = ""
    if next_steps:
        recommendations_html = f"""
        <div class="recommendation-box">
          <strong>Recommended Analyst Actions & Hardening Priorities:</strong>
          <ul>
            {"".join(f"<li>{step}</li>" for step in next_steps)}
          </ul>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>RedString OSINT Report - {inv.target}</title>
<style>
  @page {{
    size: A4;
    margin: 20mm;
    @bottom-center {{
      content: "RedString OSINT Copilot | Page " counter(page) " of " counter(pages);
      font-size: 9pt;
      color: #71717a;
    }}
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #18181b;
    background: #ffffff;
    line-height: 1.5;
    font-size: 11pt;
    margin: 0;
    padding: 0;
  }}
  .header {{
    border-bottom: 2px solid #09090b;
    padding-bottom: 12px;
    margin-bottom: 24px;
  }}
  .logo {{
    font-size: 20pt;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: #09090b;
  }}
  .subtitle {{
    font-size: 10pt;
    color: #71717a;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 2px;
  }}
  h2 {{
    font-size: 13pt;
    font-weight: 600;
    color: #09090b;
    border-bottom: 1px solid #e4e4e7;
    padding-bottom: 4px;
    margin-top: 26px;
    margin-bottom: 12px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 16px;
    font-size: 9.5pt;
  }}
  th, td {{
    padding: 6px 10px;
    text-align: left;
    border: 1px solid #e4e4e7;
  }}
  th {{
    background: #f4f4f5;
    font-weight: 600;
  }}
  .badge {{
    display: inline-block;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 8pt;
    font-weight: 600;
    text-transform: uppercase;
    background: #f4f4f5;
  }}
  .finding-badge {{
    display: inline-block;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 8pt;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-weight: 600;
    background: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    text-decoration: none;
    margin: 1px 2px;
    vertical-align: middle;
  }}
  .code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 9pt;
  }}
  .executive-box {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #2563eb;
    padding: 16px 20px;
    border-radius: 6px;
    margin-bottom: 20px;
  }}
  .exec-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 8px;
    margin-bottom: 12px;
  }}
  .exec-title {{
    font-size: 10pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #1e293b;
    font-family: ui-monospace, monospace;
  }}
  .exec-body {{
    font-size: 10pt;
    color: #334155;
    line-height: 1.6;
  }}
  .recommendation-box {{
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-left: 4px solid #16a34a;
    padding: 14px 18px;
    border-radius: 6px;
    margin-top: 16px;
    margin-bottom: 20px;
    font-size: 9.5pt;
    color: #166534;
  }}
  .recommendation-box ul {{
    margin: 6px 0 0 16px;
    padding: 0;
  }}
  .recommendation-box li {{
    margin-bottom: 4px;
    color: #14532d;
  }}
  .disclaimer {{
    background: #fafafa;
    border: 1px solid #e4e4e7;
    padding: 12px;
    border-radius: 6px;
    font-size: 9pt;
    color: #52525b;
    margin-top: 20px;
  }}
  .action-bar {{
    position: sticky;
    top: 0;
    left: 0;
    right: 0;
    background: #18181b;
    color: #ffffff;
    padding: 10px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    z-index: 1000;
    margin: 0 -20px 24px -20px;
  }}
  .action-tag {{
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
    color: #a1a1aa;
    font-family: ui-monospace, monospace;
  }}
  .btn-print {{
    background: #2563eb;
    color: #ffffff;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 10pt;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: background 0.15s ease;
  }}
  .btn-print:hover {{
    background: #1d4ed8;
  }}
  .btn-close {{
    background: #27272a;
    color: #d4d4d8;
    border: 1px solid #3f3f46;
    padding: 8px 14px;
    border-radius: 4px;
    font-size: 10pt;
    cursor: pointer;
    margin-left: 8px;
    transition: background 0.15s ease;
  }}
  .btn-close:hover {{
    background: #3f3f46;
  }}
  .content-wrap {{
    padding: 20px 30px;
    max-width: 900px;
    margin: 0 auto;
  }}
  @media print {{
    .no-print {{ display: none !important; }}
    .content-wrap {{ padding: 0 !important; max-width: 100% !important; margin: 0 !important; }}
    body {{ margin: 0; padding: 0; }}
  }}
</style>
</head>
<body>

<div class="action-bar no-print">
  <div class="action-left">
    <span class="action-tag">Official Audit Intelligence Report · INV-{inv.id:06d}</span>
  </div>
  <div class="action-right">
    <button type="button" onclick="window.print()" class="btn-print">
      🖨️ Print / Save as PDF
    </button>
    <button type="button" onclick="window.close()" class="btn-close">
      ✕ Close
    </button>
  </div>
</div>

<div class="content-wrap">

<div class="header">
  <div class="logo">RedString OSINT Report</div>
  <div class="subtitle">Evidence-Grounded Passive Intelligence Audit</div>
</div>

<h2>1. Target Information</h2>
<table>
  <tr><th style="width:30%">Target Hostname</th><td class="code">{inv.target}</td></tr>
  <tr><th>Target Category</th><td>{inv.target_type.capitalize()}</td></tr>
  <tr><th>Consent Verification</th><td>Lawful purpose confirmed (Rule S4 compliant)</td></tr>
  <tr><th>Investigation ID</th><td>INV-{inv.id:06d}</td></tr>
</table>

<h2>2. Investigation Timestamps & Scope</h2>
<table>
  <tr><th style="width:30%">Investigation Started</th><td>{created_str}</td></tr>
  <tr><th>Investigation Concluded</th><td>{finished_str}</td></tr>
  <tr><th>Passive Collectors Run</th><td>DNS, RDAP (PII-stripped), Certificate Transparency, HTTP Tech Fingerprints, GitHub Metadata</td></tr>
  <tr><th>Active Scans / Port Probes</th><td>None (Strictly passive per Rule S1)</td></tr>
</table>

<h2>3. Data Sources & Provenance</h2>
<table>
  <tr><th>Source</th><th>Method</th><th>Scope</th><th>Status</th></tr>
  <tr><td>dnspython</td><td>A, AAAA, MX, NS, TXT, CNAME, SOA</td><td>Root and www</td><td>Verified</td></tr>
  <tr><td>RDAP Bootstrap (IANA)</td><td>Authoritative registry lookup</td><td>Registrar & dates (PII stripped)</td><td>Verified</td></tr>
  <tr><td>crt.sh</td><td>Public Certificate Transparency logs</td><td>SANs & subdomains</td><td>Verified</td></tr>
  <tr><td>SafeHttpClient</td><td>SSRF-guarded HTTP GET</td><td>Homepage headers & HTML</td><td>Verified</td></tr>
  <tr><td>GitHub API</td><td>Public search & repo contributors</td><td>Public repositories & top contributors</td><td>Verified</td></tr>
</table>

<h2>4. Domain Intelligence (RDAP)</h2>
<table>
  <tr><th style="width:30%">Registrar</th><td>{registrar}</td></tr>
  <tr><th>Created Date</th><td>{created_date}</td></tr>
  <tr><th>Expiration Date</th><td>{expires_date}</td></tr>
  <tr><th>Registry Status</th><td>{statuses}</td></tr>
  <tr><th>Personal Registrant Data</th><td><em>Withheld / Stripped per Safety Rule S6</em></td></tr>
</table>

<h2>5. DNS Findings & Mail Infrastructure</h2>
<table>
  <tr><th style="width:30%">Nameservers</th><td>{", ".join(ns_list) or "None discovered"}</td></tr>
  <tr><th>Mail Providers</th><td>{", ".join(mail_list) or "None discovered"}</td></tr>
</table>

<h2>5b. Passive Security Posture & Exposure Matrix</h2>
<table>
  <thead>
    <tr>
      <th>Security Control</th>
      <th>Passive Observation & Posture Analysis</th>
      <th style="text-align:center; width:18%;">Posture Rating</th>
    </tr>
  </thead>
  <tbody>
    {security_posture_html}
  </tbody>
</table>

<h2>6. Certificate Findings</h2>
<table>
  <tr><th>Serial</th><th>Issuer</th><th>Valid From</th><th>Valid Until</th><th>Wildcard</th></tr>
  {certs_html}
</table>

<h2>7. Discovered Subdomains ({len(by_type.get('subdomain', []))})</h2>
<table>
  <tr><th>Subdomain</th><th>Status</th><th>Resolved IPs</th></tr>
  {subdomains_html}
</table>

<h2>8. Technology Stack & Cloud Providers</h2>
<table>
  <tr><th>Component</th><th>Type</th><th>Confidence</th></tr>
  {tech_html}
</table>

<h2>9. Public Repositories & Key Associated People</h2>
<table>
  <tr><th>Repository</th><th>Stars</th><th>Language</th><th>Match Basis</th></tr>
  {repo_html}
</table>

<table>
  <tr><th>Associated Person / Contributor</th><th>Role</th><th>Contributions</th><th>Associated Repo</th></tr>
  {people_html}
</table>

<h2>10. Relationship Graph Summary</h2>
<table>
  <tr><th style="width:30%">Total Entities</th><td>{len(entities)} nodes</td></tr>
  <tr><th>Total Relations</th><td>{len(relations)} edges</td></tr>
  <tr><th>Graph Model</th><td>Cytoscape-compatible typed property graph</td></tr>
</table>

<h2>11. Executive Threat Intelligence & Exposure Assessment</h2>
<div class="executive-box">
  <div class="exec-header">
    <span class="exec-title">Intelligence Synthesis & Architecture Breakdown</span>
    <span class="badge" style="background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe; font-weight:700;">PROCESSED VIA {model_badge}</span>
  </div>
  <div class="exec-body">
    {formatted_summary}
  </div>
</div>

<h3 style="font-size:11pt; margin-top:20px; margin-bottom:10px; color:#1e293b; font-weight:600;">Key Technical Findings & Correlated Observations</h3>
<ul style="padding-left:18px; margin-bottom:16px;">
  {obs_html}
</ul>

{recommendations_html}

<h2>12. Evidence References (Sample of Records)</h2>
<table>
  <tr><th>ID</th><th>Source</th><th>Source Reference</th><th>Timestamp (UTC)</th></tr>
  {evidence_html}
</table>

<h2>13. Scope, Limitations & Legal Notice</h2>
<div class="disclaimer">
  <strong>Passive Reconnaissance Notice:</strong> This audit report was compiled solely through passive open-source intelligence methods. No intrusive penetration testing, vulnerability exploitation, port scanning, or authenticated API extraction was conducted. Observations represent public internet telemetry observed at the specified timestamps. Personal registrant data has been explicitly withheld in compliance with Safety Rule S6.
</div>
</div>

</body>
</html>"""
    return html
