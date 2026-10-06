import React from "react";
import Link from "next/link";

export default function PrivacyPolicyPage() {
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
          Privacy Policy
        </h1>
        <p className="text-xs text-text-muted font-mono mt-1">
          Draft for team review • Version 1.0 • September 2026
        </p>
      </div>

      <div className="prose prose-sm text-text-secondary text-xs leading-relaxed space-y-4">
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-text-primary">
            1. Personal Data Handling (Rule S6)
          </h2>
          <p>
            RedString strictly adheres to privacy-by-design principles:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Registrant personal information returned by RDAP/WHOIS providers (such as names, personal telephone numbers, and residential addresses) is automatically dropped by parser filters and marked as redacted.</li>
            <li>No personal profiling or identity tracking is performed or supported.</li>
            <li>No user account credentials or tracking cookies are collected or stored.</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-text-primary">
            2. Local Storage and Deletion
          </h2>
          <p>
            Investigation data (including entity relationships and raw evidence records) is stored locally within the application SQLite database.
          </p>
          <p>
            Users may permanently delete any investigation and all its associated findings at any time using the &quot;Delete Investigation&quot; action in the workspace.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-text-primary">
            3. Outbound Requests
          </h2>
          <p>
            Outbound HTTP requests are made strictly to authoritative public DNS servers, public RDAP endpoints, public Certificate Transparency APIs, and the public GitHub API. Every request is pre-validated by the SSRF Guard.
          </p>
        </section>
      </div>
    </div>
  );
}
