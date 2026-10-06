"use client";

import React, { useState } from "react";
import { FindingItem, EvidenceRecord } from "@/lib/api";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { Star, Info, Code2, ChevronDown, ChevronUp, Copy, Check, ExternalLink } from "lucide-react";

interface EvidencePanelProps {
  finding: FindingItem | null;
  evidenceList: EvidenceRecord[];
  loading?: boolean;
  isStarred?: boolean;
  onToggleStar?: () => void;
}

const ENTITY_EXPLANATIONS: Record<string, { label: string; explanation: string }> = {
  ip: {
    label: "Public IP Address",
    explanation: "The server hosting the target domain. Anyone opening the website connects directly to this numerical address.",
  },
  domain: {
    label: "Root Apex Domain",
    explanation: "The primary registered internet address and organization identity being audited.",
  },
  subdomain: {
    label: "Discovered Subdomain",
    explanation: "A service or portal under the main domain (e.g. mail, student portal, or api) found in public records.",
  },
  nameserver: {
    label: "Authoritative Nameserver",
    explanation: "An authoritative DNS directory server responsible for telling web browsers where the organization's servers are located.",
  },
  mail_provider: {
    label: "Mail Gateway (MX)",
    explanation: "The email server infrastructure handling incoming emails sent to this domain (e.g. Google Workspace).",
  },
  technology: {
    label: "Web Software Stack",
    explanation: "Software component (such as Apache web server or PHP) running on the organization's public web perimeter.",
  },
  cloud_provider: {
    label: "Cloud / Network Host",
    explanation: "The hosting network or Content Delivery Network (CDN) providing server infrastructure for this address.",
  },
  repository: {
    label: "Public Code Repository",
    explanation: "A public GitHub codebase discovered during reconnaissance that matched target keywords or domain references.",
  },
  person: {
    label: "Public Contributor",
    explanation: "A public author or GitHub user account linked to discovered open-source code repositories.",
  },
  certificate: {
    label: "TLS/SSL Certificate",
    explanation: "A digital certificate issued by a Certificate Authority used to encrypt web traffic and verify domain authenticity.",
  },
};

function formatAttributeKey(key: string): string {
  const map: Record<string, string> = {
    stars: "GitHub Stars",
    forks: "Forks Count",
    language: "Language",
    match_basis: "Detection Basis",
    live: "Resolution Status",
    resolved_ips: "Resolved IPs",
    record_type: "DNS Record Type",
    cloud_provider: "Hosting Provider",
    issuer_name: "Certificate Issuer",
    serial_number: "Serial Number",
    category: "Component Type",
    contributions: "Verified Commits",
    associated_repo: "Associated Repo",
    role: "Contributor Role",
    homepage: "Official Link",
    txt_strings: "TXT Record Payload",
  };
  return map[key] || key.replace(/_/g, " ");
}

function formatAttributeValue(key: string, val: any): string {
  if (val === null || val === undefined || val === "") return "None specified";
  if (key === "live") return val ? "Active / Resolving" : "Unresolved";
  if (key === "match_basis") {
    if (val === "homepage_exact_match") return "Exact Homepage URL Match";
    if (val === "domain_text_match") return "Domain Text Match";
    if (val === "keyword_relevance" || val === "search_relevance") return "Keyword Search Match";
  }
  if (Array.isArray(val)) return val.join(", ");
  return String(val);
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  finding,
  evidenceList,
  loading = false,
  isStarred = false,
  onToggleStar,
}) => {
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [expandedJsonIds, setExpandedJsonIds] = useState<Set<number>>(new Set());

  const handleCopy = (id: number, payload: any) => {
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const toggleJson = (id: number) => {
    setExpandedJsonIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (!finding) {
    return (
      <aside
        className="w-80 shrink-0 border-l border-border bg-surface p-4 flex flex-col justify-center items-center text-center text-text-muted"
        aria-label="Evidence Panel"
      >
        <div className="w-10 h-10 rounded-control border border-border-default flex items-center justify-center mb-3 text-text-muted bg-canvas">
          <Info className="w-5 h-5 opacity-60" />
        </div>
        <p className="text-xs font-semibold text-text-secondary mb-1">No finding selected</p>
        <p className="text-[11px] leading-relaxed max-w-[220px]">
          Click any node on the graph canvas or any row in the findings table to inspect its verified public evidence.
        </p>
      </aside>
    );
  }

  const meta = ENTITY_EXPLANATIONS[finding.type] || {
    label: finding.type.toUpperCase(),
    explanation: "Passively observed technical entity discovered during public reconnaissance.",
  };

  return (
    <aside
      className="w-80 shrink-0 border-l border-border bg-surface flex flex-col overflow-hidden"
      aria-label="Evidence Panel"
    >
      {/* Header */}
      <div className="p-3 border-b border-border bg-canvas">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-xs font-bold text-accent">
              {finding.finding_id}
            </span>
            {onToggleStar && (
              <button
                type="button"
                onClick={onToggleStar}
                className="p-1 rounded hover:bg-subtle transition-colors"
                title={isStarred ? "Unstar finding" : "Star finding"}
                aria-label={isStarred ? "Unstar finding" : "Star finding"}
              >
                <Star
                  className={`w-3.5 h-3.5 ${
                    isStarred
                      ? "text-yellow-400 fill-yellow-400"
                      : "text-text-muted hover:text-text-primary"
                  }`}
                />
              </button>
            )}
          </div>
          <ConfidenceBadge confidence={finding.confidence} showDetail={true} />
        </div>

        {/* Entity Title */}
        <h3 className="font-mono text-xs font-semibold text-text-primary break-all mb-1">
          {finding.value}
        </h3>

        {/* Human-Readable Category Badge */}
        <div className="flex items-center gap-1.5 text-[11px]">
          <span className="font-medium px-1.5 py-0.5 rounded text-[10px] uppercase font-mono bg-accent/10 text-accent border border-accent/20">
            {meta.label}
          </span>
        </div>

        {/* Plain-English Explanation Box */}
        <div className="mt-2.5 p-2 rounded-control bg-subtle/40 border border-border-subtle text-[11px] text-text-secondary leading-snug">
          <span className="font-semibold text-text-primary block mb-0.5">What is this?</span>
          {meta.explanation}
        </div>
      </div>

      {/* Content Body */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Friendly Attributes Overview */}
        {finding.attributes && Object.keys(finding.attributes).length > 0 && (
          <div className="p-2.5 rounded-control bg-canvas border border-border-subtle">
            <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block mb-1.5">
              Observed Properties
            </span>
            <div className="space-y-1.5 text-xs">
              {Object.entries(finding.attributes).map(([k, v]) => {
                if (v === null || v === undefined || v === "") return null;
                const isUrl = String(v).startsWith("http://") || String(v).startsWith("https://");
                return (
                  <div key={k} className="flex flex-col text-[11px]">
                    <span className="text-text-muted text-[10px] uppercase tracking-wider">
                      {formatAttributeKey(k)}
                    </span>
                    {isUrl ? (
                      <a
                        href={String(v)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-accent hover:underline break-all flex items-center gap-1 font-mono text-[11px]"
                      >
                        {String(v)}
                        <ExternalLink className="w-3 h-3 opacity-70 shrink-0" />
                      </a>
                    ) : (
                      <span className="text-text-primary font-mono text-[11px] break-all">
                        {formatAttributeValue(k, v)}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Provenance Evidence Section */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">
              Verifiable Evidence Proofs ({evidenceList.length})
            </span>
          </div>

          <p className="text-[10px] text-text-muted mb-2">
            Every record below represents an immutable public network response captured during this investigation.
          </p>

          {loading ? (
            <div className="p-4 text-center text-text-muted text-xs animate-pulse">
              Loading verified records...
            </div>
          ) : evidenceList.length === 0 ? (
            <div className="p-3 text-center text-text-muted text-xs bg-canvas rounded-control border border-border-subtle">
              No raw payloads recorded for this finding.
            </div>
          ) : (
            <div className="space-y-2.5">
              {evidenceList.map((ev) => {
                const isJsonOpen = expandedJsonIds.has(ev.id);
                const hasRawData = ev.raw && Object.keys(ev.raw).length > 0;

                return (
                  <div
                    key={ev.id}
                    className="p-2.5 rounded-control border border-border-subtle bg-canvas text-xs space-y-2"
                  >
                    {/* Source Header */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono font-bold text-text-primary uppercase text-[10px] px-1.5 py-0.5 rounded bg-subtle border border-border-subtle">
                          {ev.source_name}
                        </span>
                        <span className="text-[10px] text-emerald-500 font-medium">✓ Verified</span>
                      </div>
                      <span className="text-[10px] text-text-muted font-mono">
                        v{ev.collector_version}
                      </span>
                    </div>

                    {/* Reference / Endpoint */}
                    {ev.source_ref && (
                      <div className="text-[11px] font-mono text-text-secondary break-all">
                        <span className="text-text-muted text-[10px] block uppercase">Source Query</span>
                        {ev.source_ref.startsWith("http") ? (
                          <a
                            href={ev.source_ref}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-accent hover:underline flex items-center gap-1"
                          >
                            {ev.source_ref}
                            <ExternalLink className="w-2.5 h-2.5 opacity-70 shrink-0" />
                          </a>
                        ) : (
                          <span>{ev.source_ref}</span>
                        )}
                      </div>
                    )}

                    {/* Timestamp */}
                    <div className="text-[10px] text-text-muted">
                      Captured: {new Date(ev.collected_at).toUTCString()}
                    </div>

                    {/* Collapsible Developer JSON Box */}
                    {hasRawData && (
                      <div className="pt-1 border-t border-border-subtle">
                        <div className="flex items-center justify-between">
                          <button
                            type="button"
                            onClick={() => toggleJson(ev.id)}
                            className="text-[10px] font-medium text-text-secondary hover:text-text-primary flex items-center gap-1 transition-colors py-0.5"
                          >
                            <Code2 className="w-3 h-3 text-accent" />
                            <span>{isJsonOpen ? "Hide Raw Payload" : "Inspect Raw Payload"}</span>
                            {isJsonOpen ? (
                              <ChevronUp className="w-3 h-3" />
                            ) : (
                              <ChevronDown className="w-3 h-3" />
                            )}
                          </button>

                          <button
                            type="button"
                            onClick={() => handleCopy(ev.id, ev.raw)}
                            className="text-[10px] text-accent hover:underline font-mono flex items-center gap-1"
                          >
                            {copiedId === ev.id ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-500" />
                                <span>Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-2.5 h-2.5" />
                                <span>Copy JSON</span>
                              </>
                            )}
                          </button>
                        </div>

                        {isJsonOpen && (
                          <pre className="mt-1.5 p-2 rounded bg-surface border border-border-subtle font-mono text-[10px] text-text-primary overflow-x-auto max-h-48 whitespace-pre-wrap break-all leading-tight">
                            {JSON.stringify(ev.raw, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
