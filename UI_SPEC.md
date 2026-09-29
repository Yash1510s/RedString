# UI_SPEC.md: OSINT Investigation Copilot

Frontend source of truth. Read `AGENTS.md` (how to work) and `docs/PROJECT_SPEC.md` (what to build) first. Where this file and `PROJECT_SPEC.md` section 11 differ, **this file wins** for anything visual or interactive. Safety rules in `PROJECT_SPEC.md` section 2 still win over everything.

Chosen direction: **Hybrid workspace**, a deliberate mix of three explored layouts:

| Borrowed from | What we keep | Why |
|---|---|---|
| Evidence console | Collector progress strip; persistent evidence panel on the right | Provenance is the product's main claim, so it must always be one click away |
| Findings-first | Tab bar with counts; one dense findings table used in two places | Analysts scan many hostnames; tables beat graphs for scanning |
| Graph canvas | Large canvas with floating filters and toolbar; bottom drawer | The graph is the fastest way to grasp structure and the best demo moment |

---

## 1. Principles

1. **Evidence is one interaction away from anything.** Any node, edge, row or summary chip opens the same evidence panel.
2. **One selection model.** Selecting a finding anywhere selects it everywhere (graph, table, drawer, panel, URL).
3. **Density is a feature.** 14 px body, 32 px table rows, monospace for technical values.
4. **Colour carries meaning only:** status, confidence, entity type. Never decoration.
5. **Nothing depends on colour alone or on the graph alone.** Shapes, labels and a table alternative exist for everything.
6. **Every screen has real loading, empty, error and success states.**
7. **No marketing surfaces.** `/` is the New Investigation screen.

Forbidden without written approval: hero sections, feature-card grids, pricing, testimonials, bento layouts, gradients, glow, glassmorphism, dot-grid backgrounds, sparkle icons, emojis in UI, decorative animation, coloured left-edge stripes on cards, purple-on-black styling.

---

## 2. Tech choices for the frontend

Use exactly these unless you ask first.

| Need | Choice | Reason |
|---|---|---|
| Framework | Next.js App Router, TypeScript strict | As per project spec |
| Styling | Tailwind CSS driven by CSS variables (section 3) | Tokens stay in one place |
| Accessible primitives | Radix UI (Dialog, Tabs, Popover, Tooltip, Checkbox, Toggle Group, Dropdown Menu) | Correct keyboard and ARIA behaviour out of the box |
| Icons | `lucide-react`, only the icons in section 3.8 | Consistent outline set; keeps bundle small |
| Server state | TanStack Query | Loading/error handling and SSE-driven invalidation |
| Tables | TanStack Table + TanStack Virtual | Sorting, filtering, virtualisation past 200 rows |
| Graph | `cytoscape` + `react-cytoscapejs`, layouts `fcose` (force) and `dagre` (hierarchical) | Handles hundreds of nodes; two layouts are enough |
| Forms | React Hook Form + Zod | Schema shared with API validation |
| Types | Generated from backend OpenAPI | No hand-written duplicates |
| Tests | Vitest + Testing Library; Playwright for two smoke flows; axe | See spec section 13 |

No component library with its own theme (no MUI, Chakra, Ant). No animation library; CSS transitions only.

---

## 3. Design tokens

Define in `frontend/app/tokens.css` as CSS variables, expose to Tailwind via `tailwind.config`. **Components never use raw hex or arbitrary pixel values.**

### 3.1 Colour: neutrals and text

| Token | Light | Dark |
|---|---|---|
| `--bg-canvas` | `#F7F8FA` | `#0E1116` |
| `--bg-surface` | `#FFFFFF` | `#151A21` |
| `--bg-raised` | `#FFFFFF` | `#1B222B` |
| `--bg-subtle` | `#F0F2F5` | `#1E252F` |
| `--bg-selected` | `#E8F0FE` | `#14233D` |
| `--border-subtle` | `#E4E7EC` | `#232B35` |
| `--border-default` | `#DDE1E7` | `#2A323D` |
| `--border-strong` | `#C3C9D2` | `#3A4552` |
| `--text-primary` | `#14181F` | `#E6EAF0` |
| `--text-secondary` | `#4B5563` | `#A7B0BD` |
| `--text-muted` | `#6B7280` | `#8A95A3` |
| `--text-inverse` | `#FFFFFF` | `#0E1116` |

### 3.2 Colour: accent and status

| Token | Light | Dark | Use |
|---|---|---|---|
| `--accent` | `#1B5FC4` | `#6EA3F5` | Links, selection, primary button fill (light) |
| `--accent-fg` | `#FFFFFF` | `#0E1116` | Text on accent fill |
| `--success-fg` / `--success-bg` | `#1B7F4B` / `#E6F4EC` | `#5FD08F` / `#12281C` | Completed, high confidence |
| `--warning-fg` / `--warning-bg` | `#8A5A00` / `#FFF3D6` | `#F2B94B` / `#2E2410` | Partial, medium confidence |
| `--danger-fg` / `--danger-bg` | `#B42318` / `#FDECEA` | `#FF8A80` / `#331615` | Failed, destructive |
| `--info-fg` / `--info-bg` | `#175CD3` / `#E8F0FE` | `#8AB4FF` / `#14233D` | Neutral notices |
| `--focus-ring` | `#1B5FC4` | `#6EA3F5` | 2 px outline, 2 px offset |

Verify contrast: body text 4.5:1 minimum, large text and UI boundaries 3:1. If a pair fails, adjust the token, not the component.

### 3.3 Entity types (graph, tables, legend)

Colours are from the Okabe-Ito colour-blind-safe set. **Each type also has a distinct shape**, so colour is never the only cue. Store the mapping once in `lib/entityStyle.ts`.

| Entity type | Colour | Cytoscape shape | Size (px) |
|---|---|---|---|
| domain (root) | `#0072B2` | ellipse | 44 |
| subdomain | `#56B4E9` | ellipse | 22 |
| ip | `#E69F00` | rectangle | 22 |
| technology | `#009E73` | round-rectangle | 26 x 20 |
| certificate | `#F0E442` (stroke `#8A7F00`) | diamond | 24 |
| repository | `#CC79A7` | hexagon | 24 |
| cloud_provider | `#D55E00` | triangle | 24 |
| organization | `#999999` | octagon | 22 |
| nameserver | `#999999` | tag | 22 |
| mail_provider | `#999999` | barrel | 22 |

Grey types are distinguished by shape plus a type prefix in labels and tooltips.

### 3.4 Confidence styles (text always present)

| Level | Label in UI | Style |
|---|---|---|
| high | Directly observed | Filled badge, `--success-bg` / `--success-fg`, solid edge in graph |
| medium | Inferred from strong signal | Filled badge, `--warning-bg` / `--warning-fg`, dashed edge |
| low | Weak signal, verify manually | Outlined badge (transparent fill, `--border-strong`, `--text-secondary`), dotted edge |

Badges show the short word (High, Medium, Low); the long label appears in tooltips, the evidence panel and the report.

### 3.5 Typography

| Token | Value |
|---|---|
| `--font-sans` | `system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif` |
| `--font-mono` | `ui-monospace, "SF Mono", "Cascadia Mono", Consolas, monospace` |

| Role | Size / line-height | Weight |
|---|---|---|
| Page title | 24 / 32 | 600 |
| Section title | 20 / 28 | 600 |
| Emphasis | 16 / 24 | 500 |
| Body and table | 14 / 20 | 400 |
| Label | 13 / 18 | 500 |
| Meta and captions | 12 / 16 | 400 |

Use mono for hostnames, IPs, record values, finding IDs, timestamps and raw payloads. Use tabular figures (`font-variant-numeric: tabular-nums`) for counts and timestamps.

### 3.6 Spacing, shape, elevation, motion

| Token group | Values |
|---|---|
| Spacing scale | 4, 8, 12, 16, 24, 32, 48 |
| Radius | `--radius-control: 4px` (inputs, buttons, badges), `--radius-panel: 6px` (panels, dialogs). No other radii |
| Borders | 1 px `--border-default`; hairline separation, no card shadows |
| Elevation | Only popovers, dropdowns, dialogs and toasts have a shadow: `0 4px 16px rgb(0 0 0 / 0.12)`. Floating graph panels use border only |
| Row height | Table row 32; compact control 28; default control 32 |
| Motion | 120 ms (hover, focus), 180 ms (panel open/close, drawer). `ease-out`. Animate only `opacity` and `transform`. Disable under `prefers-reduced-motion` |
| z-index | content 0, sticky header 10, floating graph UI 20, drawer 30, popover 40, dialog 50, toast 60 |

### 3.7 Themes

Light and dark via `[data-theme]` on `<html>`. Default follows `prefers-color-scheme`; the user can override with a toggle in the top bar (persisted in `localStorage`, wrapped in try/catch). Graph colours stay constant across themes; graph canvas background uses `--bg-canvas`.

### 3.8 Icon allow-list (`lucide-react`)

`Search, Download, RefreshCw, Trash2, Check, X, AlertTriangle, Info, ChevronDown, ChevronUp, ChevronRight, Filter, Table2, Maximize2 (fit), Image (export PNG), Copy, ExternalLink, Sun, Moon, PanelRightClose, PanelRightOpen, Loader2 (spinner)`. Add others only with justification. Icons never stand alone: they need an accessible name or adjacent text.

---

## 4. App shell and navigation

```
+--------------------------------------------------------------+
| Top bar: [OSINT Copilot]  New investigation  History   [theme] [Settings] |
+--------------------------------------------------------------+
| Page content                                                    |
+--------------------------------------------------------------+
| Footer: Acceptable use · Privacy · Terms · v1.0.0               |
+--------------------------------------------------------------+
```

- Top bar height 48, border-bottom, no shadow. Product name is text plus a small monogram square; no logo art.
- No sidebar in v1. Two primary destinations do not justify one.
- Current route indicated by `aria-current="page"` and a 2 px bottom border in `--accent`.
- Footer is quiet (12 px, muted) and holds the legal links and version.

### Routes

| Route | Screen |
|---|---|
| `/` | New Investigation |
| `/investigations` | History |
| `/investigations/[id]` | Workspace (tab and selection in query string) |
| `/settings` | Integrations status (read-only) |
| `/legal/acceptable-use`, `/legal/privacy`, `/legal/terms` | Legal |
| `not-found`, `error` | Recoverable error pages |

---

## 5. Screens

### 5.1 New Investigation (`/`)

Purpose: start an investigation with a lawful-purpose confirmation, and resume recent work.

Layout: single column, max width 720, left-aligned under the top bar. No hero.

1. Page title "New investigation" and one line: "Collects publicly available information about a domain. Nothing is scanned or accessed without authorization."
2. Form panel (bordered, `--bg-surface`):
   - Target type: segmented control "Domain" / "Company".
   - Domain mode: field "Domain", placeholder `example.com`.
   - Company mode: "Company name" and "Official domain" (required, with helper text "Used to keep results accurate.").
   - Consent checkbox (label in section 10).
   - Primary button "Start investigation". Right of it, a text link "How this works" is **not** included (no filler).
3. "Recent investigations" table (last 5) with link "View all". Empty state in section 8.

Validation: on blur and on submit; errors below the field, linked with `aria-describedby`; focus moves to the first invalid field on submit. Button shows a spinner and stays enabled-looking but ignores repeat clicks while pending. Server errors show in an inline alert above the form.

### 5.2 History (`/investigations`)

Table columns: Target (mono), Type, Status, Started, Findings, Actions (Open, Delete). Search by target; filter by status. Sorted by started desc. Delete opens ConfirmDialog ("Delete investigation? This removes its findings and evidence. This can't be undone."). Pagination: cursor-based "Load more" button (no infinite scroll).

### 5.3 Workspace (`/investigations/[id]`)

This is the core screen. Zones, top to bottom:

1. **Header**: target (mono, 20 px), StatusBadge, "Demo data" tag when applicable, started-at (UTC, with local time in tooltip), actions on the right: Rerun (secondary), Export report (primary), overflow menu with Delete.
2. **Collector progress strip**: one chip per collector with icon and short text (section 6.5). Wraps on narrow screens. Announces changes via `aria-live="polite"`.
3. **Tab bar** with counts. Tabs: Overview, Graph, Findings, Certificates, Technologies, Repositories, AI summary. Active tab stored as `?tab=`. Default tab: **Graph** when the investigation has completed, **Overview** while running.
4. **Tab content** (below).
5. **Evidence panel**: right side, shared by Graph, Findings, Certificates, Technologies and Repositories tabs.
6. **Findings drawer**: bottom of the Graph tab only.

#### Overview tab
- Count tiles (Subdomains, IP addresses, Technologies, Repositories, Certificates). Tile: 12 px label, 24 px value, no icon, no card shadow, `--bg-subtle` fill.
- "Key observations": the AI (or template) summary in a SummaryCard (section 6.12).
- "Collection details": table of collectors with status, duration, counts, and error reason if any.
- "Limitations": bullet list from the report data (redacted registrant data, heuristic detection, etc.).

#### Graph tab (default)
Three regions inside the tab:

- **Canvas** (fills available width, min height 480, height `calc(100vh - header - strip - tabs - drawer)`):
  - Floating **FilterPanel** top-left (section 6.8). Collapsible.
  - Floating **toolbar** top-right: search field, layout toggle (Force / Hierarchy), Fit, Export PNG, "Show as table".
  - Legend bottom-left, small, shows shapes plus colours for types currently visible.
  - Mini status bottom-right: "63 nodes, 88 edges".
- **Evidence panel** right, 320 px wide, collapsible (state in `?panel=closed`).
- **Findings drawer** below the canvas: collapsed by default to a 36 px header showing "Findings in view: N" and the selected finding summary; expands to 40% of the tab height. Contains the same `FindingsTable` as the Findings tab, pre-filtered to what is visible on the canvas.

Behaviour:
- Clicking a node or edge selects it, opens/updates the evidence panel, and highlights the row in the drawer (scrolling it into view).
- Clicking a row selects and centres the node (animated 180 ms; instant under reduced motion).
- Clicking empty canvas clears selection. `Esc` also clears.
- Hover shows a tooltip: type, value, confidence, source. Tooltips are also shown on keyboard focus.
- Filters change what is visible on canvas and in the drawer at once. Filtered-out nodes are removed, not faded.
- Large graphs: see section 7.

#### Findings tab
Full-width `FindingsTable` (section 6.9) plus the evidence panel on the right. Filters above the table: text search, Type, Confidence, Source. Row click selects; `Enter` opens the evidence panel focus; export CSV button ("Export CSV") for the filtered rows.

#### Certificates, Technologies, Repositories tabs
Same table component with type-specific columns:

| Tab | Columns |
|---|---|
| Certificates | Issuer, Common name, Valid from, Valid to, SAN count, Wildcard, Confidence |
| Technologies | Technology, Category, Host, Version (if seen), Detection basis, Confidence |
| Repositories | Repository, Owner, Language, Stars, Last push, Match basis, Confidence |

Each has its own empty state text (section 8).

#### AI summary tab
Full SummaryCard with sections: Summary, Key findings, Observations, Suggested next steps, Limitations. Finding chips inline. Header shows model and prompt version, or "Generated without AI". Actions: Regenerate, Copy text.

### 5.4 Settings (`/settings`)

Read-only "Integrations" table: GitHub token (Configured / Not configured), LLM provider (name / Not configured), Cache TTL, Version. Never display secret values. Explains why a collector might be limited ("Add GITHUB_TOKEN to the backend environment to raise rate limits."). Reason to exist: makes failure states explainable.

### 5.5 Legal pages

Plain prose, max width 720, 16 px / 26 px, table of contents not needed. Mark each as "Draft for team review" at the top until reviewed. Content must match actual behaviour (stored data, retention, deletion). These are not legal advice.

### 5.6 Error pages

`not-found`: "That page doesn't exist." with links to New investigation and History. `error`: "Something went wrong." with a Retry button and, in development only, the error message. Investigation not found inside Workspace: "This investigation doesn't exist or was deleted." with link to History.

---

## 6. Components

For each: purpose, states, keyboard, accessibility. Implement as small composable components under `components/ui` (primitives) and `components/investigation` (domain).

### 6.1 Button
Variants: primary (filled `--accent`), secondary (border), ghost (no border), danger. Max **one primary per view**. Sizes: 28, 32. States: default, hover, focus-visible, pressed, loading (spinner replaces icon, label stays, ignores clicks), disabled (avoid; prefer enabled with explanatory response). Min target 32 x 32 (24 x 24 absolute minimum).

### 6.2 Form controls
Input, Select, Checkbox, SegmentedControl (Radix ToggleGroup, `role="radiogroup"` semantics), SearchField. Visible label always; helper text 12 px; error text with icon and `--danger-fg`.

### 6.3 StatusBadge
Investigation statuses: Pending, Running (with spinner), Completed, Completed with errors, Failed, Cancelled. Icon plus text.

### 6.4 ConfidenceBadge
Section 3.4. Tooltip with the long label. Never colour only.

### 6.5 CollectorProgress
One chip per collector: icon + name + short detail.

| State | Icon | Detail text |
|---|---|---|
| pending | dashed circle | "Waiting" |
| running | spinner | elapsed seconds after 3 s |
| done | check | count, e.g. "Certificates 31" |
| partial | alert triangle | "Partial" + tooltip with reason |
| failed | x | reason, e.g. "Rate limited" |
| cancelled | dash | "Cancelled" |

Clicking a failed or partial chip scrolls to the Collection details table and opens the reason. Retry per collector is out of scope for v1 (use Rerun).

### 6.6 TabBar
Radix Tabs. Counts in tab labels are tabular numbers. Arrow keys move between tabs. Horizontally scrollable below 768 px with visible scroll affordance (fade-free: use a border and chevrons buttons if overflow).

### 6.7 CountTile
Label, value, optional caption. Not interactive unless it links to a filtered tab (then it is a link with visible focus).

### 6.8 FilterPanel (graph)
Checkbox list of entity types with glyph (shape+colour), name and count. "Show all" and "Hide all" text buttons. Additional toggles: "Only live hosts", "Min confidence" (segmented: All / Medium+ / High). Collapsible to an icon button. Its state is part of the URL (`?types=`, `?live=`, `?conf=`).

### 6.9 FindingsTable
The single table used in the Findings tab and Graph drawer.

| Column | Notes |
|---|---|
| Finding | Mono value, truncates with tooltip; entity glyph before text |
| Type | Entity type label |
| Relation | e.g. `RESOLVES_TO 203.0.113.10`, mono |
| Confidence | ConfidenceBadge |
| Source | Source name |
| Collected | UTC time, tabular, tooltip with full timestamp |

Behaviour: sortable columns (`aria-sort`), sticky header, row height 32, virtualised above 200 rows, roving tabindex keyboard navigation (Up/Down moves, Enter selects, Space toggles selection preview), selected row uses `--bg-selected` plus a visible outline (not colour alone). Column visibility menu is out of scope. Copy-value button appears on row hover and focus.

### 6.10 GraphView
See section 7.

### 6.11 EvidencePanel
Structure, top to bottom:
1. Header: entity glyph, value (mono, wraps), close button.
2. ConfidenceBadge with long label.
3. Finding ID (copyable) and one-sentence statement, e.g. "api.example.com resolves to 203.0.113.10."
4. "Evidence" list. Each record: source name, reference (query or URL, external links open in new tab with `rel="noopener noreferrer"`), collected at (UTC), collector version. Expandable "Raw data" viewer (mono, max height 240, copy button, "Truncated" notice when applicable).
5. "Related findings": up to 5 connected entities (click to select).

Empty state when nothing selected: "Select a node or row to see where it came from." Loading: skeleton lines. Error: inline message with Retry. The panel is `role="complementary"` with an accessible name; when a selection changes, focus is not stolen, but an `aria-live="polite"` region announces "Showing evidence for api.example.com".

### 6.12 SummaryCard and FindingChip
Sections as in 5.3. Each sentence is followed by chips like `F-000044`. Chip: mono 12 px, `--bg-subtle`, 4 px radius, focusable, click selects the finding and opens the evidence panel. States: loading (skeleton, elapsed time after 5 s, Cancel), empty ("Not generated yet." + Generate button), error (message + Retry + "Use template summary"), fallback (label "Generated without AI"), invalid-output handled as error. Never render model text that failed validation.

### 6.13 EmptyState, ErrorState, Skeleton
- EmptyState: title (16/500), one sentence, optional single action. No illustrations.
- ErrorState: what happened, what to do, Retry. No raw exception text.
- Skeleton: shapes matching the final layout (table rows, tiles, panel lines). Static pulse only if `prefers-reduced-motion: no-preference`, opacity 0.6 to 1, 1.2 s.

### 6.14 ConfirmDialog, Toast
Dialog: Radix, focus trap, `Esc` closes, destructive action is danger button on the right, default focus on Cancel. Toast: bottom-right, 5 s for success, persistent with close for errors, `role="status"` (success) or `role="alert"` (error), max 3 visible.

### 6.15 DemoDataTag
Small outlined tag "Demo data". Appears in the workspace header and on report first page whenever the investigation comes from `data/demo`.

---

## 7. Graph specification

- **Library:** Cytoscape.js. Elements come from `/graph` (section 9 of `PROJECT_SPEC.md`).
- **Default layout:** `fcose` with root domain pinned near centre-right. Toggle to `dagre` (top-down hierarchy: domain, subdomains, IPs, providers, technologies).
- **Styles:** from `lib/entityStyle.ts` (section 3.3). Node border 1.5 px `--bg-surface` (keeps glyphs separated). Selected node: 3 px `--accent` ring plus label always visible. Hovered: label visible.
- **Edges:** 1 px `--border-strong`; medium confidence dashed; low dotted; selected edge 2 px `--accent`. Arrowheads only for directional relation types (`RESOLVES_TO`, `HOSTED_ON`, `USES_TECH`, `MENTIONS`). Edge labels hidden by default; shown on hover/selection (relation type, 11 px).
- **Labels:** always visible for domain and selected/hovered nodes. Others appear when zoom >= 1.0 or when node count <= 40. Truncate at 24 characters with middle ellipsis; full value in tooltip.
- **Large graphs (> 300 nodes):** load with default filter: Domain, Subdomain, IP, Cloud provider only, and group subdomains that share one IP into a **cluster node** (compound node, click to expand). Show a notice: "Showing a filtered view of 412 nodes. Adjust filters to see more." Above 1000 nodes, refuse to render the canvas and show the table with a message.
- **Interaction:** wheel zoom (0.2 to 3), drag pan, drag node (does not persist), click select, double-click focus neighbourhood (dims non-neighbours to 25% opacity; Esc restores), Fit button, `+`/`-` keys zoom when canvas focused.
- **Keyboard/accessibility:** canvas container is focusable with instructions in `aria-describedby`: "Use the table view for keyboard navigation of all findings." The **"Show as table"** toggle swaps the canvas for the FindingsTable with identical filters. Every node/edge is reachable there. Announce node and edge counts on filter changes via a live region.
- **Export PNG:** 2x scale, white or dark background per theme, includes legend, filename `osint-<target>-graph-<yyyymmdd>.png`. The same routine feeds the report.
- **Performance targets:** initial render < 1.5 s at 300 nodes; interactions stay above 45 fps at 300 nodes on a mid-range laptop. No continuous layout animation after settle; stop the layout after 2 s max.
- **Empty:** "No relationships found for this target." with a suggestion to check the Collection details.

---

## 8. State matrix

Copy strings come from section 10. Implement every cell.

| Area | Loading | Empty | Error | Special |
|---|---|---|---|---|
| New Investigation form | Button spinner | n/a | Field errors, server alert | Consent unchecked: inline error |
| Recent investigations | 3 skeleton rows | "No investigations yet." + focus the form | Retry link | n/a |
| History | Skeleton rows | Same empty message + "Start an investigation" | Retry banner | Delete pending: row dimmed, spinner |
| Workspace shell | Skeleton header, strip, tabs | n/a | "This investigation doesn't exist or was deleted." | Cancelled / failed banners |
| Collector strip | Chips in pending | n/a | Failed chip with reason | Rate limited shows retry time if known |
| Graph | Canvas skeleton + "Building graph" | "No relationships found for this target." | Retry | Large-graph notice, > 1000 refusal |
| Findings tables | Skeleton rows | Per-tab text below | Inline error + Retry | Filters return nothing: "No findings match these filters." + Clear filters |
| Evidence panel | Skeleton lines | "Select a node or row to see where it came from." | Inline error + Retry | Truncated payload notice |
| AI summary | Skeleton + elapsed | "Not generated yet." | Error + Retry / Use template | "Generated without AI" label |
| Report export | Button spinner, then toast | n/a | Error toast with reason | Ready toast with Download action |
| Running investigation | Overview tab default; progress live | n/a | Partial results usable while running | Cancel button in header |

Per-tab empty text:

| Tab | Text |
|---|---|
| Certificates | "No certificates were found in public logs for this domain." |
| Technologies | "No technologies were detected from the homepage response." |
| Repositories | "No public repositories referenced this domain." |
| Findings | "No findings yet. Collectors are still running." (while running) / "The collectors returned no findings." (when done) |

---

## 9. URL and selection state

Single source of truth in the URL so views are shareable and refresh-safe.

| Param | Meaning |
|---|---|
| `tab` | overview, graph, findings, certificates, technologies, repositories, summary |
| `f` | Selected finding ID, e.g. `F-000044` |
| `types` | Comma list of visible entity types |
| `conf` | all, medium, high |
| `live` | `1` to show only live hosts |
| `q` | Text filter for tables |
| `panel` | `closed` when evidence panel is collapsed |
| `layout` | `force` or `hierarchy` |
| `view` | `table` when graph is shown as table |

Rules: use `router.replace` for filter and selection changes (no history spam); use `push` only for tab changes. Invalid params fall back to defaults silently.

---

## 10. Copy

Sentence case. No terminal punctuation on labels and headings; helper text and empty-state bodies end with a period. No em dashes, no "please", no exclamation marks, no "successfully", no "simply/just/easy", no marketing verbs.

| Where | String |
|---|---|
| Page title | New investigation |
| Intro | Collects publicly available information about a domain. Nothing is scanned or accessed without authorization. |
| Target type | Domain, Company |
| Company hint | Used to keep results accurate. |
| Consent | I confirm I have a lawful reason to investigate this target and understand this tool only collects publicly available information. |
| Consent error | Confirm the statement above to continue. |
| Domain error | Enter a public domain like example.com. |
| Primary CTA | Start investigation |
| Export | Export report |
| Rerun | Rerun |
| Delete dialog | Delete investigation? / This removes its findings and evidence. This can't be undone. / Delete, Cancel |
| Running | Running |
| Completed with errors | Completed with errors |
| Rate limited | Rate limited. Try again later. |
| Confidence long labels | Directly observed / Inferred from strong signal / Weak signal, verify manually |
| Evidence empty | Select a node or row to see where it came from. |
| Summary empty | Not generated yet. |
| Summary fallback label | Generated without AI |
| Summary error | Couldn't generate a summary. Retry or use the template summary. |
| Report ready | Report ready |
| Report failed | Couldn't create the report. Try again. |
| Large graph | Showing a filtered view of {n} nodes. Adjust filters to see more. |
| No filter matches | No findings match these filters. |
| Demo tag | Demo data |
| Network error | Can't reach the server. Check that the backend is running. |

---

## 11. Responsive behaviour

| Width | Behaviour |
|---|---|
| >= 1280 | Full hybrid layout: canvas + 320 px evidence panel + bottom drawer |
| 1024 to 1279 | Evidence panel 280 px; filter panel collapsed by default |
| 768 to 1023 | Evidence panel becomes a right-side overlay (Radix Dialog non-modal) opened on selection; drawer stays |
| < 768 | Graph tab shows the table view by default (graph available via toggle); evidence panel becomes a bottom sheet; tabs scroll horizontally; header actions collapse into an overflow menu |
| 360 minimum | No horizontal page scroll; tables scroll inside their container with a visible scroll hint |

Touch: targets at least 32 px; graph supports pinch zoom and tap select.

---

## 12. Accessibility checklist (must pass before Phase 6 is done)

- WCAG 2.2 AA. Contrast verified for both themes.
- Skip link "Skip to main content" as first focusable element.
- Landmarks: `header`, `nav`, `main`, `aside` (evidence), `footer`.
- Every interactive element reachable by keyboard; visible focus ring (2 px, offset 2).
- Tabs, dialogs, menus follow ARIA authoring patterns (use Radix, don't reimplement).
- Tables use real `<table>` semantics; sortable headers have `aria-sort`; virtualised tables keep `aria-rowcount` and `aria-rowindex`.
- Live regions: collector progress (polite), selection change (polite), toasts (status/alert).
- Colour never the only cue: shapes for entities, text for confidence and status.
- Reduced motion respected everywhere.
- Zoom to 200% without loss; text spacing overrides do not break layout.
- axe runs in CI on: `/`, `/investigations`, a workspace fixture (each tab), `/settings`, legal pages. Zero serious or critical violations.

---

## 13. Build order for the UI (maps to `PROJECT_SPEC.md` phases)

| Step | Scope | Done when |
|---|---|---|
| U0 (Phase 0) | `tokens.css`, Tailwind mapping, theme toggle, Button, Input, Checkbox, SegmentedControl, Badge, Skeleton, Toast, Dialog, AppShell, footer, 404/error pages | Storybook-free "kitchen sink" route (`/_ui`, dev only) shows every primitive in both themes and all states |
| U1 (Phase 2) | New Investigation, Recent table, Workspace shell, header, CollectorProgress, minimal FindingsTable, EvidencePanel | Vertical slice works with real DNS data |
| U2 (Phase 6a) | Full FindingsTable (sort, filter, virtualise), Findings/Certificates/Technologies/Repositories tabs, URL state | Keyboard-only walkthrough passes |
| U3 (Phase 6b) | GraphView, FilterPanel, toolbar, legend, drawer, table alternative, large-graph handling | 300-node fixture meets performance targets |
| U4 (Phase 7) | Overview tab, SummaryCard, FindingChip, AI states | All AI states demonstrable with fixtures |
| U5 (Phase 9) | Settings, legal pages, responsive pass, axe CI, Playwright smoke tests, visual QA | Section 14 checklist complete |

Fixtures: provide `frontend/tests/fixtures/` with 5 investigations: small (12 nodes), typical (63), large (412), empty, partial-failures. Label as demo data.

---

## 14. Visual QA checklist (end of each UI step)

Take screenshots at 1440, 1024, 768 and 390 px in light and dark, for: New Investigation, Workspace/Graph, Workspace/Findings, Workspace/AI summary, an empty state, an error state. Confirm:

- [ ] Only tokens used; no raw hex, no arbitrary spacing
- [ ] Two radii only; no card shadows; no gradients or glow
- [ ] Mono used for all technical values
- [ ] One primary button per view
- [ ] Selection stays in sync across graph, table, drawer, panel and URL
- [ ] Loading, empty, error, success verified in the browser, not just in code
- [ ] Keyboard-only run-through completed
- [ ] No fabricated numbers; demo data labelled
- [ ] Copy follows section 10 rules

---

## 15. Antigravity prompt (paste as the first message for UI work)

```
Read AGENTS.md, docs/PROJECT_SPEC.md and docs/UI_SPEC.md. UI_SPEC.md wins for anything visual.

Build the frontend as the "Hybrid workspace" defined in UI_SPEC.md, following its build order (U0 to U5).
Start with U0 only.

Rules:
1. Before writing code, give me an implementation plan for U0: files to create, dependencies from UI_SPEC section 2 only, and how you will verify.
2. Implement tokens exactly as in section 3. No raw hex or arbitrary spacing in components.
3. Use Radix primitives for dialog, tabs, popover, tooltip, checkbox, toggle group.
4. Create a dev-only /_ui route showing every primitive in light and dark and in every state.
5. Verify in the browser: keyboard focus, both themes, 1440 and 390 px widths. Run eslint, tsc, vitest and axe. Report what you ran and what you saw.
6. Do not add screens, effects, dependencies or copy that are not in the spec. If something is ambiguous, ask.
7. Stop after U0 and wait for my approval before U1.
```
