import React from "react";
import Link from "next/link";

export default function TermsOfServicePage() {
  return (
    <div className="flex-1 overflow-y-auto p-6 sm:p-10 max-w-3xl mx-auto w-full space-y-6">
      <div className="border-b border-border pb-4">
        <Link
          href="/"
          className="text-xs text-text-muted hover:text-text-primary font-mono mb-2 inline-block"
        >
          ← Return to New Investigation
        </Link>
        <h1 className="text-xl font-semibold text-text-primary">
          Terms of Service
        </h1>
        <p className="text-xs text-text-muted font-mono mt-1">
          Draft for team review • Version 1.0 • September 2026
        </p>
      </div>

      <div className="prose prose-sm text-text-secondary text-xs leading-relaxed space-y-4">
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-text-primary">
            1. Nature of Findings (Rule S11)
          </h2>
          <p>
            All records, relationships, and technology detections produced by RedString represent <strong>observed</strong> or <strong>inferred</strong> signals, never conclusive proof of ownership, infrastructure control, or legal culpability.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-text-primary">
            2. Heuristic Technology Detection
          </h2>
          <p>
            Technology fingerprinting matches public HTTP response headers, cookie names, and script tags against documented open-source heuristic rules. Detections may be subject to false positives or CDN masking.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-text-primary">
            3. Disclaimer of Warranties
          </h2>
          <p>
            This software is provided &quot;as is&quot; for legitimate reconnaissance, academic study, and security defensive analysis. The authors disclaim liability for any unauthorized targeting conducted in violation of applicable laws.
          </p>
        </section>
      </div>
    </div>
  );
}
