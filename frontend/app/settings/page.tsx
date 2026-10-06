"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ShieldCheck, Info, RefreshCw, KeyRound, Server } from "lucide-react";
import { getSystemStatus, SystemStatusData } from "@/lib/api";

export default function SettingsPage() {
  const [data, setData] = useState<SystemStatusData | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const res = await getSystemStatus();
      setData(res);
    } catch (err) {
      console.error("Failed to load system diagnostics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto w-full space-y-6">
      {/* Page Title */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h1 className="text-base font-semibold text-text-primary tracking-tight">
            System & Integrations Diagnostics
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Read-only configuration and collector rate limits status per Spec Section 5.4.
          </p>
        </div>

        <button
          type="button"
          onClick={loadStatus}
          className="px-2.5 py-1 text-xs font-mono rounded-control border border-border-default hover:bg-subtle text-text-secondary flex items-center gap-1.5 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-text-muted font-mono animate-pulse">
          Querying backend runtime parameters...
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Core Service Environment */}
          <section className="bg-surface border border-border rounded-panel p-4 space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-text-muted font-mono flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-accent" />
              Runtime Environment
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-2.5 bg-canvas rounded-control border border-border-subtle">
                <span className="text-text-muted text-[11px] font-mono block">
                  Application Version:
                </span>
                <span className="font-mono font-medium text-text-primary">
                  RedString v{data.version}
                </span>
              </div>
              <div className="p-2.5 bg-canvas rounded-control border border-border-subtle">
                <span className="text-text-muted text-[11px] font-mono block">
                  Environment:
                </span>
                <span className="font-mono font-medium text-text-primary capitalize">
                  {data.environment}
                </span>
              </div>
              <div className="p-2.5 bg-canvas rounded-control border border-border-subtle">
                <span className="text-text-muted text-[11px] font-mono block">
                  Database Layer:
                </span>
                <span className="font-mono font-medium text-text-primary">
                  {data.database}
                </span>
              </div>
              <div className="p-2.5 bg-canvas rounded-control border border-border-subtle">
                <span className="text-text-muted text-[11px] font-mono block">
                  Response Cache TTL:
                </span>
                <span className="font-mono font-medium text-text-primary">
                  {data.cache_ttl_hours} hours (Rule S7)
                </span>
              </div>
            </div>
          </section>

          {/* Safety & SSRF Guard Status */}
          <section className="bg-surface border border-border rounded-panel p-4 space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-text-muted font-mono flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-success-fg" />
              Security Boundaries (Non-negotiable Rules)
            </h2>
            <div className="p-3 bg-success-bg/40 border border-success-fg/20 rounded-control text-xs text-text-secondary leading-relaxed space-y-1">
              <p className="font-semibold text-success-fg text-[11px]">
                Pre-flight SSRF Guard (Rule S2): Active
              </p>
              <p className="text-[11px]">
                {data.ssrf_guard}. Only ports 80/443 and public internet targets are accepted. All internal, loopback, private RFC-1918, link-local, and cloud metadata addresses are immediately rejected.
              </p>
            </div>
          </section>

          {/* Integrations Table */}
          <section className="bg-surface border border-border rounded-panel p-4 space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-text-muted font-mono flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-accent" />
              Collector & Engine Integrations
            </h2>
            <div className="border border-border-subtle rounded-panel overflow-hidden">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-canvas border-b border-border text-text-muted text-[11px] uppercase tracking-wider font-mono">
                    <th className="py-2.5 px-3">Service / Engine</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Operational Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle font-mono text-xs">
                  {data.integrations.map((item) => (
                    <tr key={item.name} className="hover:bg-subtle/50">
                      <td className="py-2.5 px-3 font-semibold text-text-primary font-sans">
                        {item.name}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-block px-1.5 py-0.5 rounded-xs text-[10px] ${
                            item.status.includes("Configured") ||
                            item.status.includes("Active") ||
                            item.status.includes("Bundled")
                              ? "bg-success-bg text-success-fg"
                              : "bg-canvas border border-border-subtle text-text-secondary"
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-text-muted font-sans text-[11px]">
                        {item.note}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      ) : (
        <div className="p-8 text-center text-xs text-danger-fg bg-danger-bg border border-danger-fg/30 rounded-panel">
          Unable to connect to backend diagnostics endpoint. Verify backend is running on port 8000.
        </div>
      )}
    </div>
  );
}
