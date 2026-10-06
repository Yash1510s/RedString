import React from "react";
import Link from "next/link";

export default function AcceptableUsePage() {
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
          Acceptable Use Policy
        </h1>
        <p className="text-xs text-text-muted font-mono mt-1">
          Draft for team review • Version 1.0 • September 2026
        </p>
      </div>

      <div className="prose prose-sm text-text-secondary text-xs leading-relaxed space-y-4">
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-text-primary">
            1. Purpose and Permitted Activities
          </h2>
          <p>
            RedString (OSINT Investigation Copilot) is an educational and analytical tool designed exclusively for passive discovery of publicly available internet infrastructure records.
          </p>
          <p>Permitted activities include:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Querying authoritative public DNS records.</li>
            <li>Consulting public RDAP and WHOIS registries.</li>
            <li>Retrieving public Certificate Transparency logs via crt.sh and Certspotter.</li>
            <li>Fetching public repository metadata from GitHub.</li>
            <li>Inspecting standard HTTP response headers returned on public homepages.</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-text-primary">
            2. Strictly Prohibited Uses
          </h2>
          <p>
            Users are strictly forbidden from attempting any active, invasive, or non-consensual operations. The system actively enforces controls blocking:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Port scanning, service enumeration, or vulnerability scanning.</li>
            <li>Directory brute-forcing or credential stuffing.</li>
            <li>Targeting internal, private, loopback, link-local, or cloud metadata IP ranges (enforced by SSRF Guard).</li>
            <li>Attempting to unmask or profile private individuals or bypass redacted registry data.</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-text-primary">
            3. Investigation Consent Gate
          </h2>
          <p>
            In accordance with Safety Rule S4, every investigation requires affirmative confirmation of lawful authority or educational intent before any collector is scheduled.
          </p>
        </section>
      </div>
    </div>
  );
}
