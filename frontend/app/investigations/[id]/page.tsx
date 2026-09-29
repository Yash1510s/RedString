"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getInvestigation,
  listFindings,
  getEntityEvidence,
  getEventStreamUrl,
  InvestigationItem,
  FindingItem,
  EvidenceRecord,
} from "@/lib/api";
import { CollectorProgress, CollectorState } from "@/components/investigation/CollectorProgress";
import { EvidencePanel } from "@/components/investigation/EvidencePanel";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";

export default function InvestigationWorkspacePage() {
  const params = useParams();
  const id = params.id as string;

  const [investigation, setInvestigation] = useState<InvestigationItem | null>(null);
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<FindingItem | null>(null);
  const [evidenceList, setEvidenceList] = useState<EvidenceRecord[]>([]);
  const [loadingEvidence, setLoadingEvidence] = useState(false);

  const [collectors, setCollectors] = useState<CollectorState[]>([
    { collector: "dns", status: "pending" },
  ]);

  const [loadingWorkspace, setLoadingWorkspace] = useState(true);
  const [selectedTab, setSelectedTab] = useState<"dns" | "all">("dns");

  // Load initial investigation data
  const loadData = useCallback(async () => {
    try {
      const inv = await getInvestigation(id);
      setInvestigation(inv);

      // Map collectors
      if (inv.collectors && inv.collectors.length > 0) {
        setCollectors(
          inv.collectors.map((c) => ({
            collector: c.collector,
            status: c.status,
            error: c.error?.message,
          }))
        );
      }

      const fList = await listFindings(id);
      setFindings(fList);

      // Auto-select first finding if none selected
      if (fList.length > 0) {
        setSelectedFinding((prev) => {
          if (!prev) {
            getEntityEvidence(id, fList[0].entity_id).then(setEvidenceList);
            return fList[0];
          }
          return prev;
        });
      }
    } catch (err) {
      console.error("Failed to load workspace data:", err);
    } finally {
      setLoadingWorkspace(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Connect to SSE event stream for live progress
  useEffect(() => {
    if (!id) return;
    const eventSource = new EventSource(getEventStreamUrl(id));

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "collector_start") {
          setCollectors((prev) =>
            prev.map((c) =>
              c.collector === data.collector ? { ...c, status: "running" } : c
            )
          );
        } else if (data.type === "collector_done") {
          setCollectors((prev) =>
            prev.map((c) =>
              c.collector === data.collector
                ? {
                    ...c,
                    status: data.status,
                    count: data.entities_count,
                    duration_ms: data.duration_ms,
                    error: data.error,
                  }
                : c
            )
          );
          // Refresh findings
          listFindings(id).then((f) => setFindings(f));
        } else if (data.type === "investigation_complete") {
          setInvestigation((prev) =>
            prev ? { ...prev, status: data.status } : null
          );
          listFindings(id).then((f) => setFindings(f));
          eventSource.close();
        }
      } catch {
        // Ping or non-json heartbeat
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [id]);

  // Handle finding row selection
  const handleSelectFinding = async (finding: FindingItem) => {
    setSelectedFinding(finding);
    try {
      setLoadingEvidence(true);
      const ev = await getEntityEvidence(id, finding.entity_id);
      setEvidenceList(ev);
    } catch (err) {
      console.error("Failed to fetch evidence:", err);
      setEvidenceList([]);
    } finally {
      setLoadingEvidence(false);
    }
  };

  const filteredFindings = findings.filter((f) => {
    if (selectedTab === "dns") {
      return (
        f.type === "ip" ||
        f.type === "nameserver" ||
        f.type === "mail_provider" ||
        f.attributes?.spf_record ||
        f.attributes?.dmarc_record
      );
    }
    return true;
  });

  if (loadingWorkspace && !investigation) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-xs text-text-muted animate-pulse">
        Initializing investigation workspace...
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Central Investigation Workspace */}
      <div className="flex-1 flex flex-col overflow-hidden bg-canvas">
        {/* Workspace Top Header */}
        <div className="p-3 border-b border-border bg-surface flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-xs text-text-muted hover:text-text-primary font-mono"
            >
              ← Back
            </Link>
            <div className="h-4 w-px bg-border" />
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-mono font-semibold text-text-primary">
                  {investigation?.target}
                </h1>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-control text-[11px] font-medium capitalize ${
                    investigation?.status === "completed"
                      ? "text-success-fg bg-success-bg"
                      : investigation?.status === "running"
                      ? "text-accent bg-info-bg"
                      : "text-text-muted bg-canvas border border-border-subtle"
                  }`}
                >
                  {investigation?.status === "running" && (
                    <span className="w-1.5 h-1.5 rounded-full bg-accent animate-ping" />
                  )}
                  {investigation?.status}
                </span>
              </div>
              <p className="text-[11px] text-text-muted mt-0.5">
                Target Type: <span className="capitalize">{investigation?.target_type}</span> • Started:{" "}
                {investigation?.created_at ? new Date(investigation.created_at).toUTCString() : "Just now"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadData}
              className="px-2.5 py-1 text-xs font-mono rounded-control border border-border-default bg-canvas hover:bg-subtle text-text-secondary"
              title="Refresh findings"
            >
              ↻ Refresh
            </button>
          </div>
        </div>

        {/* Scrollable Center Pane */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Real-time Collector Progress Strip */}
          <CollectorProgress collectors={collectors} />

          {/* Findings Filter Tabs */}
          <div className="flex items-center justify-between border-b border-border">
            <div className="flex gap-2">
              <button
                onClick={() => setSelectedTab("dns")}
                className={`py-2 px-3 text-xs font-medium border-b-2 transition-colors ${
                  selectedTab === "dns"
                    ? "border-accent text-accent"
                    : "border-transparent text-text-muted hover:text-text-primary"
                }`}
              >
                DNS Records ({filteredFindings.length})
              </button>
              <button
                onClick={() => setSelectedTab("all")}
                className={`py-2 px-3 text-xs font-medium border-b-2 transition-colors ${
                  selectedTab === "all"
                    ? "border-accent text-accent"
                    : "border-transparent text-text-muted hover:text-text-primary"
                }`}
              >
                All Findings ({findings.length})
              </button>
            </div>
            <div className="text-[11px] text-text-muted font-mono">
              Total Entities Observed: {findings.length}
            </div>
          </div>

          {/* Dense Findings Table */}
          {filteredFindings.length === 0 ? (
            <div className="p-12 text-center text-xs text-text-muted border border-dashed border-border-default rounded-panel bg-surface">
              {investigation?.status === "running"
                ? "Querying DNS authoritative resolvers... Findings will populate automatically."
                : "No DNS records observed for this target."}
            </div>
          ) : (
            <div className="border border-border rounded-panel bg-surface overflow-hidden">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-canvas border-b border-border text-text-muted text-[11px] uppercase tracking-wider">
                    <th className="py-2.5 px-3 font-medium">Finding ID</th>
                    <th className="py-2.5 px-3 font-medium">Category</th>
                    <th className="py-2.5 px-3 font-medium">Observed Value</th>
                    <th className="py-2.5 px-3 font-medium">Confidence</th>
                    <th className="py-2.5 px-3 font-medium">Source</th>
                    <th className="py-2.5 px-3 font-medium text-right">Evidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {filteredFindings.map((finding) => {
                    const isSelected = selectedFinding?.finding_id === finding.finding_id;

                    return (
                      <tr
                        key={finding.finding_id}
                        onClick={() => handleSelectFinding(finding)}
                        className={`cursor-pointer transition-colors ${
                          isSelected
                            ? "bg-selected border-l-2 border-l-accent"
                            : "hover:bg-subtle/60"
                        }`}
                      >
                        <td className="py-2 px-3 font-mono text-accent font-medium">
                          {finding.finding_id}
                        </td>
                        <td className="py-2 px-3">
                          <span className="inline-block px-1.5 py-0.5 rounded text-[10px] uppercase font-mono bg-canvas border border-border-subtle text-text-secondary">
                            {finding.type}
                          </span>
                        </td>
                        <td className="py-2 px-3 font-mono font-medium text-text-primary break-all">
                          {finding.value}
                        </td>
                        <td className="py-2 px-3">
                          <ConfidenceBadge confidence={finding.confidence} />
                        </td>
                        <td className="py-2 px-3 text-text-secondary font-mono text-[11px]">
                          {finding.sources.join(", ")}
                        </td>
                        <td className="py-2 px-3 text-right font-mono text-text-muted">
                          {finding.evidence_count} proofs
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Persistent 320px Right-side Evidence Panel */}
      <EvidencePanel
        finding={selectedFinding}
        evidenceList={evidenceList}
        loading={loadingEvidence}
      />
    </div>
  );
}
