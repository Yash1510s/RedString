import React from "react";

export interface CollectorState {
  collector: string;
  status: "pending" | "running" | "ok" | "partial" | "failed" | string;
  count?: number;
  duration_ms?: number;
  error?: string;
}

interface CollectorProgressProps {
  collectors: CollectorState[];
}

export const CollectorProgress: React.FC<CollectorProgressProps> = ({ collectors }) => {
  return (
    <div
      className="p-3 bg-surface border border-border rounded-panel text-xs"
      aria-live="polite"
      aria-label="Collector Execution Progress"
    >
      <div className="text-text-muted font-medium mb-2 uppercase tracking-wider text-[11px]">
        Passive Collectors
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
        {collectors.map((c) => {
          const isPending = c.status === "pending";
          const isRunning = c.status === "running";
          const isOk = c.status === "ok";
          const isFailed = c.status === "failed";
          const isPartial = c.status === "partial";

          return (
            <div
              key={c.collector}
              className="flex items-center justify-between px-2.5 py-1.5 rounded-control border border-border-subtle bg-canvas"
            >
              <div className="flex items-center gap-2">
                <span className="font-mono font-medium text-text-primary uppercase text-xs">
                  {c.collector}
                </span>
                {isRunning && (
                  <span className="w-2 h-2 rounded-full bg-accent animate-ping" title="Running" />
                )}
              </div>

              <div>
                {isPending && (
                  <span className="text-text-muted text-[11px]">Pending</span>
                )}
                {isRunning && (
                  <span className="text-accent font-medium text-[11px]">Querying...</span>
                )}
                {isOk && (
                  <span className="inline-flex items-center gap-1 text-success-fg font-medium text-[11px]">
                    ✓ {c.count !== undefined ? `${c.count} findings` : "Done"}
                  </span>
                )}
                {isPartial && (
                  <span className="text-warning-fg font-medium text-[11px]">
                    Partial {c.count !== undefined && `(${c.count})`}
                  </span>
                )}
                {isFailed && (
                  <span className="text-danger-fg font-medium text-[11px]" title={c.error || "Failed"}>
                    Failed
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
