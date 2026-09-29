# AGENTS.md: Working Rules for OSINT Investigation Copilot

Read `docs/PROJECT_SPEC.md` first. It defines **what** to build. This file defines **how** to work.

**Precedence when rules conflict:** safety rules (spec section 2) > spec > this file > personal taste.

## 0. Product in one paragraph

An operational web tool where an investigator enters a domain, the system passively collects public information (DNS, RDAP, Certificate Transparency, homepage headers, public GitHub metadata), links findings into a graph, keeps source + evidence + timestamp for every finding, produces an AI summary that may only use those findings, and exports a PDF report. It is an analyst tool, not a marketing site.

## 1. Operating mode

1. **Detect mode.** If the repo has no application code, this is a greenfield build: follow spec section 14 phase by phase. If code exists, run the audit in section 2 before changing anything.
2. **Plan before edits.** For each phase, produce an implementation plan (files to create/change, approach, risks, how you will verify). Wait for approval before writing code.
3. **One vertical slice at a time.** Backend, API, UI, states and tests together. Do not start the next phase without confirmation.
4. **Smallest meaningful change.** Do not rewrite working code to make it look cleaner. Understand why it exists and what depends on it first.
5. **Verify by running.** Run the tests, linters and type checks. For UI work, open the app in the browser and exercise the flow, including loading, empty, error and success states. Report what you actually ran and what you saw. Never claim something works without running it.
6. **Stop and ask** (do not guess) when: a requirement is ambiguous; a decision is listed in spec section 17; you would add a dependency, a new service, or a new screen not in the spec; or a safety rule seems to block the task.
7. **Log decisions** in `docs/DECISIONS.md` (one short entry: decision, reason, alternatives).

## 2. Audit procedure (only when code already exists)

Do **not modify any file** during the audit except creating `docs/AUDIT.md`. Inspect the whole project, then write findings under:

- **KEEP**: strong and intentional. Say why.
- **IMPROVE**: works but needs refinement.
- **REMOVE**: unnecessary, repetitive, fake, or generic.
- **ADD**: missing states, accessibility, security, docs, tests, legal pages.
- **INVESTIGATE**: purpose or implementation unclear.

For each item give: severity (blocker / high / medium / low), file path(s), reason, proposed smallest fix. Stop after the audit and wait for approval.

## 3. Design principles: intentional, product-specific, not generic

The goal is **not** "look non-AI". The goal is an interface a competent team designed on purpose, where every element has a reason. Gradients, cards, icons, rounded corners and animation are allowed when they serve a purpose. Unexplained, repetitive, decorative or fabricated design is not.

**Test for every component:** purpose, user benefit, interaction, states, edge cases. If it cannot answer these, remove it.

### 3.1 Product-specific direction (binding)

- Dense, calm, information-first analyst UI. Neutral surfaces, one accent colour, colour only for meaning (status, confidence, entity type).
- System UI font for text, monospace for hostnames, IPs, records, hashes.
- Radius: two values only (4 px controls, 6 px panels). Borders separate regions. Shadow only for popovers and dialogs.
- Entity colours from a colour-blind-safe palette **plus** distinct shapes. Never rely on colour alone.
- No hero section, pricing, testimonials, feature-card grids, bento grids, sparkle icons, dot-grid or gradient backgrounds, glow, glassmorphism, decorative particles, or emojis in the UI. There is no marketing landing page. `/` is the New Investigation screen.
- Icons only for actions and status, always with an accessible name.
- Motion (120 to 200 ms) only for state change: progress, panel open, toast. Respect `prefers-reduced-motion`.

### 3.2 Warning signals checklist (use as a review lens, not a ban list)

Check whether any of these appear **without a stated reason**: checkmark-heavy lists; decorative icons; generic 3-tier pricing; no real product demonstration; excessive rounding; purple-and-black SaaS look; gradient orbs; dot grids; sparkles; multiple harsh gradients; plain unstructured white sections; arbitrary rainbow colours; shadows everywhere; repeated 3-card sections; emoji decoration; glassmorphism; overuse of em dashes; trendy fonts with no rationale; animated arrows; coloured left-edge stripes; fake testimonials; bento overuse; fake terminal windows; "It's not X, it's Y" copy; missing skeleton or loading states; missing Terms or Privacy pages; hover animation everywhere; neon or glow; generic pastel cards.

Items about pricing, testimonials, heroes and bento layouts do not apply to this product because those sections should not exist. Missing loading states and missing legal pages **do** apply and must be added.

### 3.3 Design system (required before UI work)

Define once, then reuse: type scale, spacing scale (4, 8, 12, 16, 24, 32, 48), semantic colour tokens (canvas, surface, text, muted, border, accent, success, warning, danger, info), light and dark themes, and the component set (button, input, select, checkbox, table, tabs, dialog, toast, badge). Values live as CSS variables. No arbitrary colours or pixel values in components. Avoid repeating the same card, icon placement, heading pattern or three-column layout on every screen; vary layout by content, keep the tokens consistent.

### 3.4 Copy

Plain and specific: what it does, for whom, how. Example: "Start investigation", not "Unleash the power of OSINT". No em dashes, no "It's not X, it's Y", no "revolutionizing", "unlock", "built for the future". Error messages say what happened and what to do next. Findings are described as observed or inferred, never proven.

### 3.5 No fabricated credibility

Never invent testimonials, logos, usage numbers, awards, certifications, benchmarks or partnerships. Sample data must be visibly labelled "Demo data" in the UI and in reports.

## 4. UX quality: real states, not happy paths only

Every workflow implements: **loading** (skeletons), **empty** (explain the next action), **error** (what went wrong, how to recover), **success** (clear confirmation), **partial or processing** (meaningful progress), **restricted or unauthorized** where relevant. The full matrix is in spec section 11.5.

Accessibility target: WCAG 2.2 AA. Keyboard operable, visible focus, contrast at least 4.5:1, labelled controls, semantic landmarks, aria-live for progress changes, table alternative for the graph. Responsive down to 360 px. Run an automated accessibility check (axe or equivalent) on main screens.

## 5. Engineering rules

- TypeScript strict; Python typed and checked with mypy; linters and formatters must pass.
- No dead code, no duplicate logic, no unused dependencies, no abstraction for its own sake.
- Every new dependency needs a one-line justification (why, maintained, licence). Prefer the stack in spec section 3.
- Domain errors map to one API error shape. No bare `except`, no silently swallowed errors.
- Config through environment variables with validation. Secrets never in code, logs, or git. Keep `.env.example` current.
- Server state through a data-fetching layer (TanStack Query) so loading and error states are handled uniformly. Generate API types from OpenAPI instead of hand-copying.
- Tests: unit tests use recorded fixtures and mocked HTTP; no live network in CI. Add tests for every safety rule.
- Commit in small, reviewable steps with clear messages. Do not touch unrelated files.

## 6. Safety rules (non-negotiable, summarised from spec section 2)

1. **Passive only.** DNS, RDAP, Certificate Transparency, GitHub public API, one normal GET of the homepage. No port scans, vulnerability checks, brute force, or anything requiring authorization.
2. **SSRF guard on every outbound HTTP request:** resolve first; reject loopback, private, link-local, multicast, reserved (IPv4 and IPv6); ports 80 and 443 only; re-validate every redirect (max 3); 2 MB response cap; timeouts.
3. **Target validation:** public hostnames only. No IP literals, localhost, credentials, paths or ports.
4. **Consent gate:** API refuses to start without `consent=true`; store it.
5. **No secrets hunting, no personal profiling.** GitHub: repository metadata and README for domain matching only. Drop personal RDAP fields.
6. **Respect** `robots.txt`, rate limits and API terms; cache for 24 h.
7. Never weaken or bypass a safety rule to make a test or demo pass.

## 7. Rules for AI features

Add an AI feature only if it has: a defined purpose, clear input and output, schema validation, error handling, loading state, fallback, explainability, latency and cost limits, and security review.

For this product the only AI feature in v1 is the grounded summary (spec section 10):

- Input is a compact JSON of stored findings. Counts are computed in code.
- Output is schema-validated. Every cited finding ID must exist; numeric claims must match code-computed counts; no domain or URL outside the findings.
- Collected content (HTML, headers, READMEs, certificate fields) is **untrusted**. Pass it only inside a delimited data block. The model has no tools. Add tests with prompt-injection strings.
- The app must work fully with no LLM configured, using a labelled template summary.
- Store `prompt_version` and model with each summary. Temperature 0 to 0.2. Log token use.

## 8. Definition of done (per phase and for the project)

Before saying a phase is finished, confirm each of these and report evidence:

- Tests, linters, type checks pass (paste the summary).
- The flow was exercised in the browser, including error and empty states.
- Safety rules touched by the phase have tests.
- README and `docs/DECISIONS.md` updated.
- No fabricated data, no unexplained decoration, no dead code.

Final review lenses: normal user, designer, developer, security reviewer, accessibility reviewer, product reviewer, skeptical evaluator (spec section 15). Fix genuine problems only. Do not make arbitrary changes just to avoid a listed pattern, and do not add complexity to prove the project is human-made.

## 9. How to report back

Keep messages short and factual:

1. What you did (files changed).
2. What you ran and the results.
3. What you decided and why (also in `docs/DECISIONS.md`).
4. What is unfinished or risky.
5. Questions that need a human answer.
