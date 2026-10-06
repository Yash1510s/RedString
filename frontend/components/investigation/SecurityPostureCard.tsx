"use client";

import React, { useMemo } from "react";
import { FindingItem } from "@/lib/api";
import { ShieldCheck, ShieldAlert, AlertTriangle, Info, CheckCircle2, XCircle } from "lucide-react";

interface SecurityPostureCardProps {
  findings: FindingItem[];
  targetDomain: string;
}

interface PostureItem {
  id: string;
  category: string;
  title: string;
  severity: "secure" | "warning" | "risk" | "info";
  description: string;
  evidenceFindingId?: string;
}

export function SecurityPostureCard({ findings, targetDomain }: SecurityPostureCardProps) {
  const postureItems: PostureItem[] = useMemo(() => {
    const items: PostureItem[] = [];

    // 1. Inspect TXT findings for DMARC
    const txtFindings = findings.filter(
      (f) => f.type === "domain" || f.type === "subdomain" || (f.attributes && f.attributes.record_type === "TXT")
    );

    let dmarcRecord = "";
    let dmarcFindingId: string | undefined;
    let spfRecord = "";
    let spfFindingId: string | undefined;

    findings.forEach((f) => {
      const val = (f.value || "").toLowerCase();
      const txtData = (f.attributes?.txt_strings || f.attributes?.data || "").toString().toLowerCase();
      const combined = `${val} ${txtData}`;

      if (combined.includes("v=dmarc1")) {
        dmarcRecord = combined;
        dmarcFindingId = f.finding_id;
      }
      if (combined.includes("v=spf1")) {
        spfRecord = combined;
        spfFindingId = f.finding_id;
      }
    });

    // DMARC Evaluation
    if (dmarcRecord) {
      if (dmarcRecord.includes("p=reject")) {
        items.push({
          id: "dmarc",
          category: "Email Authentication",
          title: "DMARC Reject Policy Enforced",
          severity: "secure",
          description: "Strict reject policy (p=reject) prevents unauthorized domain impersonation and spoofed phishing.",
          evidenceFindingId: dmarcFindingId,
        });
      } else if (dmarcRecord.includes("p=quarantine")) {
        items.push({
          id: "dmarc",
          category: "Email Authentication",
          title: "DMARC Quarantine Policy Active",
          severity: "warning",
          description: "Quarantine policy (p=quarantine) redirects spoofed messages to spam rather than outright rejecting them.",
          evidenceFindingId: dmarcFindingId,
        });
      } else {
        items.push({
          id: "dmarc",
          category: "Email Authentication",
          title: "DMARC Monitoring Only (p=none)",
          severity: "warning",
          description: "DMARC policy is set to monitoring mode only. Domain is vulnerable to active email spoofing.",
          evidenceFindingId: dmarcFindingId,
        });
      }
    } else {
      items.push({
        id: "dmarc",
        category: "Email Authentication",
        title: "No DMARC Record Observed",
        severity: "risk",
        description: "No public DMARC record observed. Attackers can forge emails appearing to originate from this domain.",
      });
    }

    // SPF Evaluation
    if (spfRecord) {
      if (spfRecord.includes("-all")) {
        items.push({
          id: "spf",
          category: "Mail Security",
          title: "Hard-Fail SPF Configured (-all)",
          severity: "secure",
          description: "Authoritative list of permitted sending mail gateways is strictly enforced.",
          evidenceFindingId: spfFindingId,
        });
      } else if (spfRecord.includes("~all")) {
        items.push({
          id: "spf",
          category: "Mail Security",
          title: "Soft-Fail SPF Configured (~all)",
          severity: "warning",
          description: "Permissive soft-fail allows mail transfer agents to accept unlisted sending servers with warning tags.",
          evidenceFindingId: spfFindingId,
        });
      } else {
        items.push({
          id: "spf",
          category: "Mail Security",
          title: "Permissive SPF Rules Detected",
          severity: "risk",
          description: "SPF record lacks explicit fail flags, allowing unauthorized senders to bypass gateway filters.",
          evidenceFindingId: spfFindingId,
        });
      }
    } else {
      items.push({
        id: "spf",
        category: "Mail Security",
        title: "Missing SPF Authorization Record",
        severity: "risk",
        description: "No sender policy framework record found; mail routing integrity is unverified.",
      });
    }

    // 2. Nameserver Redundancy
    const nsEntities = findings.filter((f) => f.type === "nameserver");
    if (nsEntities.length >= 2) {
      items.push({
        id: "dns",
        category: "DNS Resilience",
        title: `${nsEntities.length} Delegated Nameservers (Redundant)`,
        severity: "secure",
        description: "Authoritative DNS routing is distributed across independent nameserver endpoints.",
      });
    } else if (nsEntities.length === 1) {
      items.push({
        id: "dns",
        category: "DNS Resilience",
        title: "Single Nameserver (Single Point of Failure)",
        severity: "risk",
        description: "Only one authoritative nameserver observed. DNS outage could render domain unreachable.",
      });
    }

    // 3. Cloud / CDN Perimeter Shield
    const cloudOrCdn = findings.filter(
      (f) =>
        f.type === "cloud_provider" ||
        (f.type === "technology" &&
          ["cloudflare", "cloudfront", "fastly", "akamai", "aws"].some((c) =>
            f.value.toLowerCase().includes(c)
          ))
    );

    if (cloudOrCdn.length > 0) {
      const names = cloudOrCdn.map((c) => c.value).join(", ");
      items.push({
        id: "cloud",
        category: "Perimeter Shield",
        title: `Cloud Perimeter Active (${names})`,
        severity: "secure",
        description: "Web perimeter routes through managed cloud/CDN proxy layers mitigating direct DDoS and origin discovery.",
      });
    } else {
      items.push({
        id: "cloud",
        category: "Perimeter Shield",
        title: "Direct Origin Server Exposure",
        severity: "info",
        description: "Web perimeter appears directly bound to public host IPs without an intermediary CDN proxy.",
      });
    }

    return items;
  }, [findings]);

  const severityBadge = (sev: PostureItem["severity"]) => {
    switch (sev) {
      case "secure":
        return {
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-success-fg shrink-0" />,
          badgeClass: "bg-success-bg border-success-fg/30 text-success-fg",
          tag: "SECURE",
        };
      case "warning":
        return {
          icon: <AlertTriangle className="w-3.5 h-3.5 text-warning-fg shrink-0" />,
          badgeClass: "bg-warning-bg border-warning-fg/30 text-warning-fg",
          tag: "WARNING",
        };
      case "risk":
        return {
          icon: <XCircle className="w-3.5 h-3.5 text-danger-fg shrink-0" />,
          badgeClass: "bg-danger-bg border-danger-fg/30 text-danger-fg",
          tag: "RISK",
        };
      default:
        return {
          icon: <Info className="w-3.5 h-3.5 text-accent shrink-0" />,
          badgeClass: "bg-subtle border-border-default text-text-secondary",
          tag: "INFO",
        };
    }
  };

  return (
    <div className="bg-surface border border-border rounded-panel p-4 space-y-3">
      <div className="flex items-center justify-between border-b border-border pb-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-accent" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-text-primary font-mono">
            Passive Security Posture Indicators
          </h2>
        </div>
        <span className="text-[10px] font-mono text-text-muted">
          Rule S1 Compliant · Non-intrusive public telemetry
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {postureItems.map((item) => {
          const config = severityBadge(item.severity);
          return (
            <div
              key={item.id}
              className="p-3 bg-canvas border border-border-default rounded-control flex flex-col justify-between space-y-1.5"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5 min-w-0">
                  {config.icon}
                  <span className="text-xs font-semibold font-mono text-text-primary truncate">
                    {item.title}
                  </span>
                </div>
                <span
                  className={`px-1.5 py-0.5 text-[9px] font-mono uppercase font-semibold border rounded ${config.badgeClass} shrink-0`}
                >
                  {config.tag}
                </span>
              </div>
              <p className="text-[11px] text-text-secondary leading-relaxed">
                {item.description}
              </p>
              <div className="flex items-center justify-between pt-1 border-t border-border-subtle text-[10px] font-mono text-text-muted">
                <span>Category: {item.category}</span>
                {item.evidenceFindingId && (
                  <span className="text-accent font-medium">
                    Evidence: {item.evidenceFindingId}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
