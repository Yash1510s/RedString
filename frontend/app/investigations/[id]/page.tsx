"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import {
  FileText,
  Trash2,
  RefreshCw,
  Search,
  ExternalLink,
  ChevronRight,
  Shield,
  Layers,
  Sparkles,
} from "lucide-react";

import {
  getInvestigation,
  listFindings,
  getEntityEvidence,
  getEventStreamUrl,
  getInvestigationGraph,
  getInvestigationSummary,
  regenerateInvestigationSummary,
  deleteInvestigation,
  getReportUrl,
  InvestigationItem,
  FindingItem,
  EvidenceRecord,
  InvestigationGraphData,
  InvestigationSummaryData,
} from "@/lib/api";
import { CollectorProgress, CollectorState } from "@/components/investigation/CollectorProgress";
import { EvidencePanel } from "@/components/investigation/EvidencePanel";
import { SummaryCard } from "@/components/investigation/SummaryCard";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

// Dynamically import Cytoscape GraphView to ensure zero SSR hydration friction
const GraphView = dynamic(
  () =>
    import("@/components/investigation/GraphView").then((mod) => mod.GraphView),
  {
    ssr: false,
    loading: () => (
      <div className="flex-1 flex items-center justify-center p-8 text-xs text-text-muted bg-canvas">
        Loading Cytoscape relationship canvas...
      </div>
    ),
  }
);

type WorkspaceTab =
  | "overview"
  | "graph"
  | "findings"
  | "certificates"
  | "technologies"
  | "repositories"
  | "summary";

export default function InvestigationWorkspacePage() {
  const params = useParams();
  const id = params.id as string;
  const router = useRouter();
  const searchParams = useSearchParams();

  // Navigation tab from URL or default
  const activeTab = (searchParams.get("tab") as WorkspaceTab) || "overview";

  const setTab = (tab: WorkspaceTab) => {
    const nextParams = new URLSearchParams(searchParams.toString());
    nextParams.set("tab", tab);
    router.replace(`/investigations/${id}?${nextParams.toString()}`);
  };

  // State
  const [investigation, setInvestigation] = useState<InvestigationItem | null>(null);
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<FindingItem | null>(null);
  const [evidenceList, setEvidenceList] = useState<EvidenceRecord[]>([]);
  const [loadingEvidence, setLoadingEvidence] = useState(false);

  const [graphData, setGraphData] = useState<InvestigationGraphData | null>(null);
  const [summaryData, setSummaryData] = useState<InvestigationSummaryData | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);

  const [collectors, setCollectors] = useState<CollectorState[]>([
    { collector: "dns", status: "pending" },
    { collector: "rdap", status: "pending" },
    { collector: "ct", status: "pending" },
    { collector: "tech", status: "pending" },
    { collector: "github", status: "pending" },
  ]);

  const [loadingWorkspace, setLoadingWorkspace] = useState(true);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [tableSearch, setTableSearch] = useState("");
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Dedicated graph fetcher
  const fetchGraph = useCallback(async () => {
    try {
      setLoadingGraph(true);
      setGraphError(null);
      const data = await getInvestigationGraph(id);
      setGraphData(data);
    } catch (err: any) {
      console.error("Failed to load graph:", err);
      setGraphError(err.message || "Failed to load graph data");
    } finally {
      setLoadingGraph(false);
    }
  }, [id]);

  // Load all investigation data
  const loadData = useCallback(async () => {
    try {
      const inv = await getInvestigation(id);
      setInvestigation(inv);

      // Collectors
      if (inv.collectors && inv.collectors.length > 0) {
        setCollectors(
          inv.collectors.map((c) => ({
            collector: c.collector,
            status: c.status,
            error: c.error?.message,
          }))
        );
      }

      // Findings
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

      // Graph data
      fetchGraph();

      // Summary data
      getInvestigationSummary(id).then(setSummaryData).catch(() => {});
    } catch (err) {
      console.error("Failed to load workspace data:", err);
    } finally {
      setLoadingWorkspace(false);
    }
  }, [id, fetchGraph]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Connect to SSE event stream
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
          listFindings(id).then(setFindings);
          getInvestigationGraph(id).then(setGraphData).catch(() => {});
        } else if (data.type === "investigation_complete") {
          setInvestigation((prev) =>
            prev ? { ...prev, status: data.status } : null
          );
          listFindings(id).then(setFindings);
          getInvestigationGraph(id).then(setGraphData).catch(() => {});
          getInvestigationSummary(id).then(setSummaryData).catch(() => {});
          eventSource.close();
        }
      } catch {
        // Heartbeat or ping
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [id]);

  // Select finding row or graph node
  const handleSelectFinding = useCallback(async (finding: FindingItem) => {
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
  }, [id]);

  const handleSelectEntityFromGraph = useCallback(
    (entityId: number, findingId?: string) => {
      // 1. Try matching by entity_id
      let match = findings.find(
        (f) => Number(f.entity_id) === Number(entityId)
      );

      // 2. Try matching by finding_id (e.g. F-000012)
      if (!match && findingId) {
        match = findings.find((f) => f.finding_id === findingId);
      }

      // 3. Fallback: retrieve from graphData nodes if findings list hasn't loaded or is filtered
      if (!match && graphData) {
        const gNode = graphData.nodes.find(
          (n) =>
            Number(n.data.entityId) === Number(entityId) ||
            (findingId && n.data.findingId === findingId)
        );
        if (gNode) {
          match = {
            finding_id: gNode.data.findingId || (entityId ? `F-${entityId.toString().padStart(6, "0")}` : "F-000000"),
            entity_id: Number(gNode.data.entityId || entityId),
            type: gNode.data.type,
            value: gNode.data.label,
            confidence: "high",
            attributes: gNode.data.attributes || {},
            sources: ["Passive observation"],
            evidence_count: 1,
            first_seen: new Date().toISOString(),
          };
        }
      }

      if (match) {
        handleSelectFinding(match);
      }
    },
    [findings, graphData, handleSelectFinding]
  );

  const handleSelectFindingById = (findingId: string) => {
    const match = findings.find((f) => f.finding_id === findingId);
    if (match) {
      handleSelectFinding(match);
    }
  };

  // Regenerate summary
  const handleRegenerateSummary = async () => {
    setLoadingSummary(true);
    try {
      const regenerated = await regenerateInvestigationSummary(id);
      setSummaryData(regenerated);
    } catch (err) {
      console.error("Failed to regenerate summary:", err);
    } finally {
      setLoadingSummary(false);
    }
  };

  // Delete investigation
  const handleDeleteInvestigation = async () => {
    try {
      setIsDeleting(true);
      await deleteInvestigation(id);
      router.push("/");
    } catch (err) {
      console.error("Failed to delete investigation:", err);
      setIsDeleting(false);
      setIsDeleteDialogOpen(false);
    }
  };

  // Filter findings for category tabs
  const filteredCategoryFindings = useMemo(() => {
    let list = findings;

    if (activeTab === "certificates") {
      list = findings.filter((f) => f.type === "certificate");
    } else if (activeTab === "technologies") {
      list = findings.filter((f) => f.type === "technology");
    } else if (activeTab === "repositories") {
      list = findings.filter((f) => f.type === "repository");
    }

    if (tableSearch.trim()) {
      const q = tableSearch.toLowerCase();
      list = list.filter(
        (f) =>
          f.value.toLowerCase().includes(q) ||
          f.finding_id.toLowerCase().includes(q) ||
          f.type.toLowerCase().includes(q)
      );
    }

    return list;
  }, [findings, activeTab, tableSearch]);

  // Aggregate category counts for tab badges
  const counts = useMemo(() => {
    const map: Record<string, number> = {
      subdomains: 0,
      ips: 0,
      certificates: 0,
      technologies: 0,
      repositories: 0,
    };
    findings.forEach((f) => {
      if (f.type === "subdomain") map.subdomains++;
      else if (f.type === "ip") map.ips++;
      else if (f.type === "certificate") map.certificates++;
      else if (f.type === "technology") map.technologies++;
      else if (f.type === "repository") map.repositories++;
    });
    return map;
  }, [findings]);

  if (loadingWorkspace && !investigation) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-xs text-text-muted animate-pulse font-mono">
        Loading investigation workspace...
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Central Investigation Workspace */}
      <div className="flex-1 flex flex-col overflow-hidden bg-canvas">
        {/* Workspace Top Header */}
        <div className="p-3 border-b border-border bg-surface flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-xs text-text-muted hover:text-text-primary font-mono transition-colors"
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
              <p className="text-[11px] text-text-muted mt-0.5 font-mono">
                Target: <span className="capitalize">{investigation?.target_type}</span> • Started:{" "}
                {investigation?.created_at
                  ? new Date(investigation.created_at).toUTCString()
                  : "Just now"}
              </p>
            </div>
          </div>

          {/* Header Action Buttons */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadData}
              className="px-2.5 py-1 text-xs font-mono rounded-control border border-border-default hover:bg-subtle text-text-secondary flex items-center gap-1.5 transition-colors"
              title="Refresh findings and graph"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>

            <a
              href={getReportUrl(id)}
              target="_blank"
              rel="noopener noreferrer"
              className="px-2.5 py-1 text-xs font-mono rounded-control bg-accent text-accent-fg hover:opacity-90 flex items-center gap-1.5 transition-colors"
              title="Open audit-ready printable report in new tab"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Export Report</span>
              <ExternalLink className="w-3 h-3 opacity-70" />
            </a>

            <button
              type="button"
              onClick={() => setIsDeleteDialogOpen(true)}
              className="p-1.5 text-text-muted hover:text-danger-fg hover:bg-danger-bg rounded-control transition-colors"
              title="Delete investigation (Privacy control)"
              aria-label="Delete investigation"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Real-time Collector Progress Strip */}
        <div className="p-3 border-b border-border bg-surface shrink-0">
          <CollectorProgress collectors={collectors} />
        </div>

        {/* Tab Bar with Counts */}
        <div className="flex items-center px-3 border-b border-border bg-surface shrink-0 overflow-x-auto">
          {[
            { id: "overview", label: "Overview" },
            {
              id: "graph",
              label: `Graph (${graphData?.meta.nodeCount || findings.length})`,
            },
            { id: "findings", label: `Findings (${findings.length})` },
            {
              id: "certificates",
              label: `Certificates (${counts.certificates})`,
            },
            {
              id: "technologies",
              label: `Technologies (${counts.technologies})`,
            },
            {
              id: "repositories",
              label: `Repositories (${counts.repositories})`,
            },
            { id: "summary", label: "AI Summary" },
          ].map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setTab(tab.id as WorkspaceTab)}
                className={`py-2 px-3 text-xs font-medium border-b-2 whitespace-nowrap transition-colors ${
                  isActive
                    ? "border-accent text-accent font-semibold"
                    : "border-transparent text-text-muted hover:text-text-primary"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Main Tab View Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {/* TAB 1: OVERVIEW */}
          {activeTab === "overview" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-5">
              {/* Count Metric Tiles */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {[
                  { label: "Subdomains", val: counts.subdomains },
                  { label: "IP Addresses", val: counts.ips },
                  { label: "Certificates", val: counts.certificates },
                  { label: "Technologies", val: counts.technologies },
                  { label: "Repositories", val: counts.repositories },
                ].map((tile) => (
                  <div
                    key={tile.label}
                    className="p-3 bg-surface border border-border rounded-panel"
                  >
                    <div className="text-[11px] font-mono text-text-muted uppercase">
                      {tile.label}
                    </div>
                    <div className="text-xl font-mono font-semibold text-text-primary mt-1">
                      {tile.val}
                    </div>
                  </div>
                ))}
              </div>

              {/* Summary Card Preview */}
              <SummaryCard
                summaryData={summaryData}
                onSelectFindingId={handleSelectFindingById}
                onRegenerate={handleRegenerateSummary}
                loading={loadingSummary}
              />

              {/* Collectors Details Table */}
              <div className="bg-surface border border-border rounded-panel p-4 space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted font-mono">
                  Collection Execution Trail
                </h3>
                <div className="border border-border-subtle rounded-panel overflow-hidden">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-canvas border-b border-border text-text-muted text-[11px] uppercase font-mono">
                        <th className="py-2 px-3">Collector</th>
                        <th className="py-2 px-3">Status</th>
                        <th className="py-2 px-3">Duration</th>
                        <th className="py-2 px-3">Entities</th>
                        <th className="py-2 px-3">Error / Note</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle font-mono text-xs">
                      {collectors.map((col) => (
                        <tr key={col.collector} className="hover:bg-subtle/50">
                          <td className="py-2 px-3 font-semibold uppercase text-text-primary">
                            {col.collector}
                          </td>
                          <td className="py-2 px-3 capitalize">
                            <span
                              className={`px-1.5 py-0.5 rounded-xs text-[10px] ${
                                col.status === "done"
                                  ? "bg-success-bg text-success-fg"
                                  : col.status === "failed"
                                  ? "bg-danger-bg text-danger-fg"
                                  : col.status === "running"
                                  ? "bg-info-bg text-accent"
                                  : "bg-canvas text-text-muted"
                              }`}
                            >
                              {col.status}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-text-secondary">
                            {col.duration_ms ? `${col.duration_ms} ms` : "—"}
                          </td>
                          <td className="py-2 px-3 text-text-secondary">
                            {col.count ?? "—"}
                          </td>
                          <td className="py-2 px-3 text-danger-fg text-[11px]">
                            {col.error || "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: CYTOSCAPE GRAPH */}
          {activeTab === "graph" && (
            <div className="flex-1 flex flex-col overflow-hidden relative">
              {loadingGraph && !graphData ? (
                <div className="flex-1 flex flex-col items-center justify-center p-8 text-xs text-text-muted font-mono space-y-2 animate-pulse">
                  <RefreshCw className="w-4 h-4 animate-spin text-accent" />
                  <span>Correlating entity relationship graph...</span>
                </div>
              ) : graphError && !graphData ? (
                <div className="flex-1 flex flex-col items-center justify-center p-8 text-xs text-danger-fg font-mono space-y-3">
                  <span>Error loading graph: {graphError}</span>
                  <button
                    onClick={fetchGraph}
                    className="px-3 py-1 text-xs border border-border-default rounded-control hover:bg-subtle text-text-primary"
                  >
                    ↻ Retry Loading Graph
                  </button>
                </div>
              ) : graphData ? (
                graphData.nodes.length === 0 ? (
                  <div className="flex-1 flex flex-col items-center justify-center p-8 text-xs text-text-muted font-mono space-y-3">
                    <span>No relationships or entities observed yet for this target.</span>
                    <button
                      onClick={fetchGraph}
                      className="px-3 py-1 text-xs border border-border-default rounded-control hover:bg-subtle text-accent"
                    >
                      ↻ Refresh Graph
                    </button>
                  </div>
                ) : (
                  <GraphView
                    graphData={graphData}
                    onSelectEntity={handleSelectEntityFromGraph}
                    selectedEntityId={selectedFinding?.entity_id}
                  />
                )
              ) : null}
            </div>
          )}

          {/* TAB 3, 4, 5, 6: FINDINGS & CATEGORY TABLES */}
          {(activeTab === "findings" ||
            activeTab === "certificates" ||
            activeTab === "technologies" ||
            activeTab === "repositories") && (
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {/* Table Search Toolbar */}
              <div className="flex items-center justify-between gap-3">
                <div className="relative flex-1 max-w-sm">
                  <Search className="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder={`Filter ${activeTab}...`}
                    value={tableSearch}
                    onChange={(e) => setTableSearch(e.target.value)}
                    className="w-full pl-8 pr-3 py-1 text-xs rounded-control bg-surface border border-border-default focus:border-accent font-mono text-text-primary"
                  />
                </div>
                <div className="text-[11px] font-mono text-text-muted">
                  Showing {filteredCategoryFindings.length} of {findings.length}{" "}
                  findings
                </div>
              </div>

              {/* Dense Category Findings Table */}
              {filteredCategoryFindings.length === 0 ? (
                <div className="p-12 text-center text-xs text-text-muted border border-dashed border-border rounded-panel bg-surface">
                  No {activeTab} records observed for this target.
                </div>
              ) : (
                <div className="border border-border rounded-panel bg-surface overflow-hidden">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-canvas border-b border-border text-text-muted text-[11px] uppercase tracking-wider font-mono">
                        <th className="py-2 px-3">Finding ID</th>
                        <th className="py-2 px-3">Type</th>
                        <th className="py-2 px-3">Value</th>
                        <th className="py-2 px-3">Confidence</th>
                        <th className="py-2 px-3">Sources</th>
                        <th className="py-2 px-3 text-right">Proofs</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle">
                      {filteredCategoryFindings.map((finding) => {
                        const isSelected =
                          selectedFinding?.finding_id === finding.finding_id;

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
          )}

          {/* TAB 7: AI SUMMARY */}
          {activeTab === "summary" && (
            <div className="flex-1 overflow-y-auto p-4">
              <SummaryCard
                summaryData={summaryData}
                onSelectFindingId={handleSelectFindingById}
                onRegenerate={handleRegenerateSummary}
                loading={loadingSummary}
              />
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

      {/* Delete Investigation Dialog */}
      <ConfirmDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
        title="Delete Investigation"
        description="Are you sure you want to permanently delete this investigation? This action removes all observed entities, relationships, and raw evidence records from the database."
        confirmLabel="Delete Permanently"
        confirmVariant="danger"
        isProcessing={isDeleting}
        onConfirm={handleDeleteInvestigation}
      />
    </div>
  );
}
