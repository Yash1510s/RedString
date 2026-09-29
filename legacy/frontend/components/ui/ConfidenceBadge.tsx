import React from "react";

export type ConfidenceLevel = "high" | "medium" | "low";

interface ConfidenceBadgeProps {
  confidence: ConfidenceLevel | string;
  showDetail?: boolean;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  confidence,
  showDetail = false,
}) => {
  const level = (confidence || "medium").toLowerCase() as ConfidenceLevel;

  if (level === "high") {
    return (
      <span
        className="inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-control border bg-success-bg text-success-fg border-success-fg/30"
        title="Directly observed from definitive authoritative record"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-success-fg shrink-0" aria-hidden="true" />
        <span>{showDetail ? "Directly observed" : "High"}</span>
      </span>
    );
  }

  if (level === "medium") {
    return (
      <span
        className="inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-control border bg-info-bg text-info-fg border-info-fg/30"
        title="Inferred from strong structural signal"
      >
        <span className="w-1.5 h-1.5 rotate-45 border border-info-fg bg-info-fg/40 shrink-0" aria-hidden="true" />
        <span>{showDetail ? "Inferred from strong signal" : "Medium"}</span>
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-control border bg-warning-bg text-warning-fg border-warning-fg/30"
      title="Weak signal, verify manually"
    >
      <span className="w-1.5 h-1.5 border border-warning-fg shrink-0" aria-hidden="true" />
      <span>{showDetail ? "Weak signal, verify manually" : "Low"}</span>
    </span>
  );
};
