/**
 * Utilities for exporting findings and graph intelligence into CSV and JSON formats.
 */

import { FindingItem, InvestigationGraphData, InvestigationItem, InvestigationSummaryData } from "./api";

/**
 * Clean and escape fields for CSV format per RFC 4180.
 */
function escapeCSV(val: any): string {
  if (val === null || val === undefined) return '""';
  let str = typeof val === "object" ? JSON.stringify(val) : String(val);
  str = str.replace(/"/g, '""');
  return `"${str}"`;
}

/**
 * Export findings array to a formatted CSV spreadsheet file.
 */
export function exportFindingsToCSV(findings: FindingItem[], targetDomain: string): void {
  const headers = [
    "Finding ID",
    "Entity ID",
    "Entity Type",
    "Observed Value",
    "Confidence",
    "Evidence Count",
    "Data Sources",
    "First Seen",
    "Attributes",
  ];

  const rows = findings.map((f) => [
    escapeCSV(f.finding_id),
    escapeCSV(f.entity_id),
    escapeCSV(f.type),
    escapeCSV(f.value),
    escapeCSV(f.confidence),
    escapeCSV(f.evidence_count),
    escapeCSV(f.sources.join(", ")),
    escapeCSV(f.first_seen),
    escapeCSV(f.attributes ? JSON.stringify(f.attributes) : ""),
  ]);

  const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\r\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  const cleanTarget = targetDomain.replace(/[^a-zA-Z0-9.-]/g, "_");
  link.setAttribute("download", `redstring-${cleanTarget}-findings.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export full investigation archive (investigation, findings, graph, summary) to JSON.
 */
export function exportInvestigationToJSON(params: {
  investigation: InvestigationItem | null;
  findings: FindingItem[];
  graphData: InvestigationGraphData | null;
  summary: InvestigationSummaryData | null;
}): void {
  const target = params.investigation?.target || "investigation";
  const archive = {
    metadata: {
      tool: "RedString OSINT Investigation Copilot",
      version: "1.0.0",
      exported_at: new Date().toISOString(),
      specification: "Grounded Passive Intelligence Schema",
    },
    investigation: params.investigation,
    executive_summary: params.summary,
    findings: params.findings,
    graph: params.graphData,
  };

  const jsonContent = JSON.stringify(archive, null, 2);
  const blob = new Blob([jsonContent], { type: "application/json;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  const cleanTarget = target.replace(/[^a-zA-Z0-9.-]/g, "_");
  link.setAttribute("download", `redstring-${cleanTarget}-archive.json`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
