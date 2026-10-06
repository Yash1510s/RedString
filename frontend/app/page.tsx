"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  createInvestigation,
  createDemoInvestigation,
  listInvestigations,
  InvestigationItem,
} from "@/lib/api";

export default function NewInvestigationPage() {
  const router = useRouter();

  const [target, setTarget] = useState("");
  const [targetType, setTargetType] = useState<"domain" | "company">("domain");
  const [officialDomain, setOfficialDomain] = useState("");
  const [consent, setConsent] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [recentList, setRecentList] = useState<InvestigationItem[]>([]);
  const [loadingList, setLoadingList] = useState(true);

  // Fetch recent investigations
  const fetchRecent = async () => {
    try {
      setLoadingList(true);
      const items = await listInvestigations();
      setRecentList(items);
    } catch {
      // Backend might be warming up
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    fetchRecent();
  }, []);

  function sanitizeDomainInput(input: string): string {
    let clean = input.trim();
    // Strip scheme if user pasted a URL (e.g. https://www.xavier.ac.in/)
    clean = clean.replace(/^[a-zA-Z]+:\/\//, "");
    // Strip trailing path, query, hash
    clean = clean.split("/")[0].split("?")[0].split("#")[0];
    // Strip port if present
    clean = clean.split(":")[0];
    return clean.trim().toLowerCase();
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!consent) {
      setErrorMessage("You must confirm lawful purpose consent to initiate passive investigation.");
      return;
    }

    let scanTarget = sanitizeDomainInput(target);
    const cleanOfficial = officialDomain.trim() ? sanitizeDomainInput(officialDomain) : null;

    if (targetType === "company") {
      if (cleanOfficial && cleanOfficial.includes(".")) {
        // If official domain is provided (e.g. jio.com), that is the target domain to scan
        scanTarget = cleanOfficial;
      } else if (scanTarget.includes(".")) {
        // User typed the domain into the primary company box
        scanTarget = scanTarget;
      } else {
        setErrorMessage(
          "For company investigations, please enter the official web domain (e.g. jio.com) so passive DNS and network collectors can query it."
        );
        return;
      }
    } else {
      if (!scanTarget || !scanTarget.includes(".")) {
        setErrorMessage("Please enter a valid public domain name (e.g. example.com).");
        return;
      }
    }

    try {
      setIsSubmitting(true);

      const created = await createInvestigation({
        target: scanTarget,
        target_type: targetType,
        official_domain: cleanOfficial || scanTarget,
        consent,
      });

      router.push(`/investigations/${created.id}`);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to start investigation.");
      setIsSubmitting(false);
    }
  };

  const handleLoadDemo = async () => {
    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      const demoInv = await createDemoInvestigation();
      router.push(`/investigations/${demoInv.id}`);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load demo investigation.");
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto w-full space-y-8">
      {/* Initiation Card */}
      <section className="bg-surface border border-border rounded-panel p-5 space-y-5" aria-labelledby="form-heading">
        <div>
          <h1 id="form-heading" className="text-base font-semibold text-text-primary tracking-tight">
            Start New Investigation
          </h1>
          <p className="text-xs text-text-muted mt-1">
            Passively queries authoritative DNS, Certificate Transparency, and public network metadata without active scanning or intrusion.
          </p>
        </div>

        {errorMessage && (
          <div
            className="p-3 bg-danger-bg border border-danger-fg/30 text-danger-fg text-xs rounded-control flex items-start gap-2"
            role="alert"
          >
            <span className="font-semibold">Error:</span>
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Target Type Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-text-secondary w-24">Target Type:</span>
            <div className="inline-flex rounded-control border border-border-default p-0.5 bg-canvas">
              <button
                type="button"
                onClick={() => setTargetType("domain")}
                className={`px-3 py-1 text-xs font-medium rounded-control transition-colors ${
                  targetType === "domain"
                    ? "bg-surface text-text-primary shadow-sm"
                    : "text-text-muted hover:text-text-primary"
                }`}
              >
                Domain
              </button>
              <button
                type="button"
                onClick={() => setTargetType("company")}
                className={`px-3 py-1 text-xs font-medium rounded-control transition-colors ${
                  targetType === "company"
                    ? "bg-surface text-text-primary shadow-sm"
                    : "text-text-muted hover:text-text-primary"
                }`}
              >
                Company
              </button>
            </div>
          </div>

          {/* Primary Target Input */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label htmlFor="target-input" className="block text-xs font-medium text-text-secondary">
                {targetType === "domain" ? "Public Domain Name" : "Company or Organization Name"}
              </label>
              <button
                type="button"
                onClick={handleLoadDemo}
                disabled={isSubmitting}
                className="text-[11px] font-mono text-accent hover:underline flex items-center gap-1 cursor-pointer"
                title="Instantly seed offline pre-correlated demo data without making external network calls"
              >
                <span>⚡ Load Offline Demo Data</span>
              </button>
            </div>
            <input
              id="target-input"
              type="text"
              required
              autoFocus
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder={targetType === "domain" ? "e.g. example.com" : "e.g. Example Inc"}
              className="w-full h-9 px-3 text-xs font-mono bg-canvas border border-border-default rounded-control text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <div className="flex flex-wrap items-center justify-between gap-2 pt-0.5">
              <span className="text-[11px] text-text-muted">
                Enter public domain name (no http://, ports, paths, or IP addresses).
              </span>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-text-muted font-mono">Quick:</span>
                <button
                  type="button"
                  onClick={() => {
                    setTarget("jio.com");
                    setTargetType("domain");
                  }}
                  className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-canvas border border-border-default hover:border-accent text-text-secondary hover:text-accent transition-colors"
                >
                  jio.com
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTarget("xavier.ac.in");
                    setTargetType("domain");
                  }}
                  className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-canvas border border-border-default hover:border-accent text-text-secondary hover:text-accent transition-colors"
                >
                  xavier.ac.in
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTarget("github.com");
                    setTargetType("domain");
                  }}
                  className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-canvas border border-border-default hover:border-accent text-text-secondary hover:text-accent transition-colors"
                >
                  github.com
                </button>
              </div>
            </div>
          </div>

          {/* Optional Official Domain for Company */}
          {targetType === "company" && (
            <div className="space-y-1.5">
              <label htmlFor="official-domain-input" className="block text-xs font-medium text-text-secondary">
                Company Web Domain (Required for DNS and network telemetry)
              </label>
              <input
                id="official-domain-input"
                type="text"
                required
                value={officialDomain}
                onChange={(e) => setOfficialDomain(e.target.value)}
                placeholder="e.g. jio.com"
                className="w-full h-9 px-3 text-xs font-mono bg-canvas border border-border-default rounded-control text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          )}

          {/* Mandatory Lawful Purpose Consent Gate */}
          <div className="pt-2 border-t border-border-subtle">
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                required
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-0.5 rounded-control border-border-default text-accent focus:ring-ring"
              />
              <span className="text-xs text-text-secondary leading-relaxed">
                I confirm I have a lawful reason to investigate this target and understand this tool only collects publicly available information.
              </span>
            </label>
          </div>

          {/* Submit Action */}
          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={isSubmitting || !consent}
              className={`h-9 px-4 text-xs font-semibold rounded-control transition-colors ${
                isSubmitting || !consent
                  ? "bg-subtle text-text-muted cursor-not-allowed border border-border-subtle"
                  : "bg-accent text-accent-fg hover:opacity-90 shadow-sm"
              }`}
            >
              {isSubmitting ? "Starting investigation..." : "Start investigation"}
            </button>
          </div>
        </form>
      </section>

      {/* Recent Investigations Table */}
      <section className="bg-surface border border-border rounded-panel p-5 space-y-3" aria-labelledby="history-heading">
        <div className="flex items-center justify-between">
          <h2 id="history-heading" className="text-sm font-semibold text-text-primary">
            Recent Investigations
          </h2>
          <button
            onClick={fetchRecent}
            className="text-xs text-text-muted hover:text-text-primary font-mono"
            title="Refresh list"
          >
            ↻ Refresh
          </button>
        </div>

        {loadingList ? (
          <div className="p-8 text-center text-xs text-text-muted animate-pulse">
            Loading past investigation records...
          </div>
        ) : recentList.length === 0 ? (
          <div className="p-8 text-center text-xs text-text-muted border border-dashed border-border-default rounded-control">
            No investigations yet. Enter a domain above to begin.
          </div>
        ) : (
          <div className="overflow-x-auto border border-border-subtle rounded-control">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-canvas border-b border-border-subtle text-text-muted text-[11px] uppercase tracking-wider">
                  <th className="py-2 px-3 font-medium">Target</th>
                  <th className="py-2 px-3 font-medium">Type</th>
                  <th className="py-2 px-3 font-medium">Status</th>
                  <th className="py-2 px-3 font-medium">Findings</th>
                  <th className="py-2 px-3 font-medium">Created</th>
                  <th className="py-2 px-3 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {recentList.map((item) => (
                  <tr key={item.id} className="hover:bg-subtle/50 transition-colors">
                    <td className="py-2 px-3 font-mono font-medium text-text-primary">
                      {item.target}
                    </td>
                    <td className="py-2 px-3 capitalize text-text-secondary">
                      {item.target_type}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium capitalize ${
                          item.status === "completed"
                            ? "text-success-fg bg-success-bg"
                            : item.status === "running"
                            ? "text-accent bg-info-bg"
                            : "text-text-muted bg-canvas"
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono text-text-secondary">
                      {item.findings_count}
                    </td>
                    <td className="py-2 px-3 text-text-muted text-[11px]">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="py-2 px-3 text-right">
                      <Link
                        href={`/investigations/${item.id}`}
                        className="text-xs font-semibold text-accent hover:underline font-mono"
                      >
                        Open →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
