/**
 * Typed client API utilities connecting frontend to FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface InvestigationItem {
  id: number;
  target: string;
  target_type: string;
  official_domain?: string | null;
  status: "pending" | "running" | "completed" | "failed" | "partial";
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  findings_count: number;
  consent_given?: boolean;
  collectors?: Array<{
    collector: string;
    status: string;
    started_at: string;
    finished_at?: string | null;
    error?: any;
  }>;
}

export interface FindingItem {
  finding_id: string;
  entity_id: number;
  type: string;
  value: string;
  confidence: "high" | "medium" | "low";
  attributes: Record<string, any>;
  sources: string[];
  evidence_count: number;
  first_seen: string;
}

export interface EvidenceRecord {
  id: number;
  source_name: string;
  source_ref?: string | null;
  raw: Record<string, any>;
  collected_at: string;
  collector_version: string;
}

export async function createInvestigation(params: {
  target: string;
  target_type?: string;
  official_domain?: string | null;
  consent: boolean;
}): Promise<InvestigationItem> {
  const res = await fetch(`${API_BASE}/api/investigations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: params.target,
      target_type: params.target_type || "domain",
      official_domain: params.official_domain || null,
      consent: params.consent,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${res.status}`);
  }

  return res.json();
}

export async function listInvestigations(): Promise<InvestigationItem[]> {
  const res = await fetch(`${API_BASE}/api/investigations?limit=30`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch investigations: ${res.status}`);
  }
  return res.json();
}

export async function getInvestigation(id: number | string): Promise<InvestigationItem> {
  const res = await fetch(`${API_BASE}/api/investigations/${id}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to load investigation details: ${res.status}`);
  }
  return res.json();
}

export async function listFindings(id: number | string): Promise<FindingItem[]> {
  const res = await fetch(`${API_BASE}/api/investigations/${id}/findings`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to load findings: ${res.status}`);
  }
  return res.json();
}

export async function getEntityEvidence(
  investigationId: number | string,
  entityId: number | string
): Promise<EvidenceRecord[]> {
  const res = await fetch(
    `${API_BASE}/api/investigations/${investigationId}/entities/${entityId}/evidence`,
    { cache: "no-store" }
  );
  if (!res.ok) {
    throw new Error(`Failed to load evidence: ${res.status}`);
  }
  return res.json();
}

export function getEventStreamUrl(id: number | string): string {
  return `${API_BASE}/api/investigations/${id}/events`;
}

export interface GraphNodeData {
  id: string;
  entityId: number;
  label: string;
  type: string;
  findingId: string;
  attributes: Record<string, any>;
}

export interface GraphEdgeData {
  id: string;
  relationId: number;
  source: string;
  target: string;
  type: string;
  confidence: "high" | "medium" | "low";
  findingId: string;
  distinct_sources: string[];
}

export interface InvestigationGraphData {
  nodes: Array<{ data: GraphNodeData }>;
  edges: Array<{ data: GraphEdgeData }>;
  meta: {
    nodeCount: number;
    edgeCount: number;
    generatedAt: string;
  };
}

export async function getInvestigationGraph(
  id: number | string,
  types?: string
): Promise<InvestigationGraphData> {
  const url = new URL(`${API_BASE}/api/investigations/${id}/graph`);
  if (types) {
    url.searchParams.set("types", types);
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to load graph data: ${res.status}`);
  }
  return res.json();
}

export interface KeyFindingItem {
  claim: string;
  finding_ids: string[];
  category?: string;
}

export interface KeyObservationItem {
  observation: string;
  finding_ids: string[];
}

export interface InvestigationSummaryData {
  summary: string;
  key_findings: KeyFindingItem[];
  observations: KeyObservationItem[];
  next_steps: string[];
  limitations: string[];
  model?: string;
  prompt_version?: string;
}

export async function getInvestigationSummary(
  id: number | string
): Promise<InvestigationSummaryData> {
  const res = await fetch(`${API_BASE}/api/investigations/${id}/summary`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to load summary: ${res.status}`);
  }
  return res.json();
}

export async function regenerateInvestigationSummary(
  id: number | string
): Promise<InvestigationSummaryData> {
  const res = await fetch(`${API_BASE}/api/investigations/${id}/summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Failed to regenerate summary: ${res.status}`);
  }
  return res.json();
}

export async function cancelInvestigation(id: number | string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/investigations/${id}/cancel`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Failed to cancel investigation: ${res.status}`);
  }
}

export async function deleteInvestigation(id: number | string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/investigations/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error(`Failed to delete investigation: ${res.status}`);
  }
}

export function getReportUrl(id: number | string): string {
  return `${API_BASE}/api/investigations/${id}/report`;
}
