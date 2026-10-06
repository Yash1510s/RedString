"use client";

import React, { useState } from "react";
import { FindingItem, EvidenceRecord } from "@/lib/api";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { Star } from "lucide-react";

interface EvidencePanelProps {
  finding: FindingItem | null;
  evidenceList: EvidenceRecord[];
  loading?: boolean;
  isStarred?: boolean;
  onToggleStar?: () => void;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  finding,
  evidenceList,
  loading = false,
  isStarred = false,
  onToggleStar,
}) => {
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const handleCopy = (id: number, payload: any) => {
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (!finding) {
    return (
      <aside
        className="w-80 shrink-0 border-l border-border bg-surface p-4 flex flex-col justify-center items-center text-center text-text-muted"
        aria-label="Evidence Panel"
      >
        <div className="w-10 h-10 rounded-control border border-border-default flex items-center justify-center mb-3 text-text-muted bg-canvas">
          ℹ
        </div>
        <p className="text-xs font-medium text-text-secondary mb-1">No finding selected</p>
        <p className="text-[11px] leading-relaxed">
          Select any record or node from the findings table to inspect its verified public evidence.
        </p>
      </aside>
    );
  }

  return (
    <aside
      className="w-80 shrink-0 border-l border-border bg-surface flex flex-col overflow-hidden"
      aria-label="Evidence Panel"
    >
      {/* Header */}
      <div className="p-3 border-b border-border bg-canvas">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-xs font-semibold text-accent">
              {finding.finding_id}
            </span>
            {onToggleStar && (
              <button
                type="button"
                onClick={onToggleStar}
                className="p-0.5 rounded hover:bg-subtle transition-colors"
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
        <h3 className="font-mono text-xs font-medium text-text-primary break-all">
          {finding.value}
        </h3>
        <div className="text-[11px] text-text-muted mt-1 uppercase tracking-wider">
          Category: <span className="font-medium text-text-secondary">{finding.type}</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Attributes overview if present */}
        {finding.attributes && Object.keys(finding.attributes).length > 0 && (
          <div className="p-2 rounded-control bg-canvas border border-border-subtle">
            <span className="text-[11px] font-medium text-text-muted uppercase tracking-wider block mb-1">
              Attributes
            </span>
            <div className="space-y-1 text-xs">
              {Object.entries(finding.attributes).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-2 font-mono text-[11px]">
                  <span className="text-text-muted truncate">{k}:</span>
                  <span className="text-text-primary truncate">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="text-[11px] font-medium text-text-muted uppercase tracking-wider">
          Immutable Provenance Evidence ({evidenceList.length})
        </div>

        {loading ? (
          <div className="p-4 text-center text-text-muted text-xs animate-pulse">
            Loading raw evidence records...
          </div>
        ) : evidenceList.length === 0 ? (
          <div className="p-3 text-center text-text-muted text-xs bg-canvas rounded-control border border-border-subtle">
            No raw payloads recorded for this finding.
          </div>
        ) : (
          evidenceList.map((ev) => (
            <div
              key={ev.id}
              className="p-2.5 rounded-control border border-border-subtle bg-canvas text-xs space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono font-medium text-text-primary uppercase text-[11px] px-1.5 py-0.5 rounded bg-subtle">
                  {ev.source_name}
                </span>
                <span className="text-[10px] text-text-muted font-mono">
                  v{ev.collector_version}
                </span>
              </div>

              {ev.source_ref && (
                <div className="text-[11px] font-mono text-text-secondary break-all">
                  Ref: {ev.source_ref}
                </div>
              )}

              <div className="text-[10px] text-text-muted">
                Collected: {new Date(ev.collected_at).toUTCString()}
              </div>

              {/* Raw JSON Payload Box */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-text-muted uppercase">Raw Response</span>
                  <button
                    onClick={() => handleCopy(ev.id, ev.raw)}
                    className="text-[10px] text-accent hover:underline font-mono"
                  >
                    {copiedId === ev.id ? "✓ Copied" : "Copy JSON"}
                  </button>
                </div>
                <pre className="p-2 rounded bg-surface border border-border-subtle font-mono text-[10px] text-text-primary overflow-x-auto max-h-48 whitespace-pre-wrap break-all">
                  {JSON.stringify(ev.raw, null, 2)}
                </pre>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
};
