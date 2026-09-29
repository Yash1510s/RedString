import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "RedString — OSINT Investigation Copilot",
  description:
    "Passive OSINT intelligence analyst tool with strict SSRF boundaries and verifiable evidence provenance.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-theme="dark">
      <body className="min-h-screen flex flex-col bg-canvas text-text-primary antialiased">
        {/* Global Dense Navigation Header */}
        <header className="h-12 border-b border-border bg-surface px-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2 text-text-primary hover:text-accent transition-colors">
              <span className="font-semibold text-sm tracking-tight text-accent font-mono">
                RedString
              </span>
              <span className="text-xs text-text-muted hidden sm:inline">
                OSINT Investigation Copilot
              </span>
            </Link>

            <nav className="flex items-center gap-3 text-xs pl-4 border-l border-border-subtle" aria-label="Main Navigation">
              <Link
                href="/"
                className="text-text-secondary hover:text-text-primary transition-colors py-1"
              >
                New Investigation
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-control bg-canvas border border-border-subtle text-[11px] font-mono text-text-muted">
              <span className="w-1.5 h-1.5 rounded-full bg-success-fg" />
              Passive Only (S1)
            </span>
          </div>
        </header>

        {/* Main Application Canvas */}
        <main className="flex-1 flex flex-col overflow-hidden">{children}</main>
      </body>
    </html>
  );
}
