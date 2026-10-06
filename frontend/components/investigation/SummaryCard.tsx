"use client";

import React, { useState } from "react";
import {
  Sparkles,
  Copy,
  Check,
  RefreshCw,
  AlertCircle,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";
import { InvestigationSummaryData } from "@/lib/api";

interface SummaryCardProps {
  summaryData: InvestigationSummaryData | null;
  onSelectFindingId?: (findingId: string) => void;
  onRegenerate?: () => Promise<void>;
  loading?: boolean;
}

export function SummaryCard({
  summaryData,
  onSelectFindingId,
  onRegenerate,
  loading = false,
}: SummaryCardProps) {
  const [copied, setCopied] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  if (loading) {
    return (
      <div className="p-8 text-center bg-surface border border-border rounded-panel text-xs text-text-muted animate-pulse">
        Generating grounded investigation summary...
      </div>
    );
  }

  if (!summaryData) {
    return (
      <div className="p-8 text-center bg-surface border border-border rounded-panel text-xs text-text-muted">
        No summary generated yet.
      </div>
    );
  }

  const handleCopy = () => {
    const text = [
      `### Executive Summary`,
      summaryData.summary,
      ``,
      `### Key Findings`,
      ...summaryData.key_findings.map(
        (f) => `- ${f.claim} (${f.finding_ids.join(", ")})`
      ),
      ``,
      `### Key Observations`,
      ...summaryData.observations.map(
        (o) => `- ${o.observation} (${o.finding_ids.join(", ")})`
      ),
      ``,
      `### Suggested Next Steps`,
      ...summaryData.next_steps.map((s) => `- ${s}`),
      ``,
      `### Limitations`,
      ...summaryData.limitations.map((l) => `- ${l}`),
    ].join("\n");

    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRegenerate = async () => {
    if (!onRegenerate || regenerating) return;
    try {
      setRegenerating(true);
      await onRegenerate();
    } finally {
      setRegenerating(false);
    }
  };

  const isTemplate =
    !summaryData.model ||
    summaryData.model.includes("template") ||
    summaryData.model.includes("deterministic");

  return (
    <div
      className="bg-surface border border-border rounded-panel p-5 space-y-5"
      role="region"
      aria-label="Investigation Summary Card"
    >
      {/* Header with Model & Version Badges */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border-subtle">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-control bg-accent/10 text-accent">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-text-primary">
              Investigation Summary
            </h2>
            <div className="flex items-center gap-2 text-[11px] text-text-muted font-mono mt-0.5">
              <span>
                {isTemplate
                  ? "Deterministic Grounded Template"
                  : `Model: ${summaryData.model}`}
              </span>
              <span>•</span>
              <span>v{summaryData.prompt_version || "1.0.0"}</span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {onRegenerate && (
            <button
              type="button"
              onClick={handleRegenerate}
              disabled={regenerating}
              className="px-2.5 py-1 text-xs font-mono rounded-control border border-border-default hover:bg-subtle text-text-secondary flex items-center gap-1.5 transition-colors disabled:opacity-50"
              title="Regenerate grounded summary"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${regenerating ? "animate-spin" : ""}`}
              />
              <span>Regenerate</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleCopy}
            className="px-2.5 py-1 text-xs font-mono rounded-control border border-border-default hover:bg-subtle text-text-secondary flex items-center gap-1.5 transition-colors"
            title="Copy formatted summary to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-success-fg" />
                <span className="text-success-fg">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Narrative Summary */}
      <div className="space-y-1.5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted font-mono">
          Executive Summary
        </h3>
        <p className="text-xs text-text-primary leading-relaxed bg-canvas p-3 rounded-control border border-border-subtle font-sans">
          {summaryData.summary}
        </p>
      </div>

      {/* Key Findings with Clickable Finding Chips */}
      {summaryData.key_findings.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted font-mono flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-success-fg" />
            Key Findings ({summaryData.key_findings.length})
          </h3>
          <ul className="space-y-2">
            {summaryData.key_findings.map((finding: any, idx) => {
              const claimText = finding.claim || finding.text || "Directly observed signal";
              return (
                <li
                  key={idx}
                  className="text-xs text-text-secondary flex items-start gap-2 bg-canvas/40 p-2.5 rounded-control border border-border-subtle"
                >
                  <span className="text-accent font-bold mt-0.5">•</span>
                  <div className="flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {finding.category && (
                        <span className="inline-block px-1.5 py-0.2 rounded-xs font-mono text-[10px] uppercase bg-canvas border border-border-subtle text-text-muted">
                          {finding.category}
                        </span>
                      )}
                      <span className="text-text-primary font-medium">{claimText}</span>
                    </div>
                    {finding.finding_ids && finding.finding_ids.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                        <span className="text-[10px] font-mono text-text-muted">Evidence:</span>
                        {finding.finding_ids.map((fid: string) => (
                          <button
                            key={fid}
                            type="button"
                            onClick={() => onSelectFindingId?.(fid)}
                            className="px-1.5 py-0.2 rounded-xs font-mono text-[10px] bg-accent/10 text-accent hover:bg-accent/20 border border-accent/20 transition-colors"
                            title={`Inspect raw provenance for ${fid}`}
                          >
                            {fid}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Key Observations */}
      {summaryData.observations.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted font-mono">
            Correlated Observations ({summaryData.observations.length})
          </h3>
          <ul className="space-y-2">
            {summaryData.observations.map((obs: any, idx) => {
              const obsText = obs.observation || obs.text || "Correlated topology signal";
              return (
                <li
                  key={idx}
                  className="text-xs text-text-secondary flex items-start gap-2 bg-canvas/40 p-2.5 rounded-control border border-border-subtle"
                >
                  <span className="text-accent font-bold mt-0.5">•</span>
                  <div className="flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {obs.confidence && (
                        <span className="inline-block px-1.5 py-0.2 rounded-xs font-mono text-[10px] capitalize bg-canvas border border-border-subtle text-text-muted">
                          {obs.confidence} confidence
                        </span>
                      )}
                      <span className="text-text-primary">{obsText}</span>
                    </div>
                    {obs.finding_ids && obs.finding_ids.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                        <span className="text-[10px] font-mono text-text-muted">Evidence:</span>
                        {obs.finding_ids.map((fid: string) => (
                          <button
                            key={fid}
                            type="button"
                            onClick={() => onSelectFindingId?.(fid)}
                            className="px-1.5 py-0.2 rounded-xs font-mono text-[10px] bg-accent/10 text-accent hover:bg-accent/20 border border-accent/20 transition-colors"
                            title={`Inspect raw provenance for ${fid}`}
                          >
                            {fid}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Suggested Next Steps */}
      {summaryData.next_steps.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted font-mono flex items-center gap-1.5">
            <ArrowRight className="w-3.5 h-3.5 text-accent" />
            Suggested Next Steps
          </h3>
          <ul className="space-y-1">
            {summaryData.next_steps.map((step, idx) => (
              <li
                key={idx}
                className="text-xs text-text-secondary flex items-center gap-2 pl-2"
              >
                <span className="text-text-muted">→</span>
                <span>{step}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Limitations Notice */}
      {summaryData.limitations.length > 0 && (
        <div className="space-y-1.5 pt-2 border-t border-border-subtle">
          <div className="flex items-center gap-1.5 text-text-muted text-[11px] font-mono uppercase tracking-wider">
            <AlertCircle className="w-3 h-3 text-warning-fg" />
            <span>Investigation Limitations & Scope</span>
          </div>
          <ul className="space-y-1">
            {summaryData.limitations.map((lim, idx) => (
              <li
                key={idx}
                className="text-[11px] text-text-muted pl-4 relative before:content-['-'] before:absolute before:left-1"
              >
                {lim}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
