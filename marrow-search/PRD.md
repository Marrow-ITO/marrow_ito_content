# Marrow Semantic Search — Hackathon PRD

## Context

Marrow is a medical education app for Indian med students preparing for NEET-PG, INI-CET, and FMGE. Current search is keyword-only on titles, missing concept-based and natural-language queries.

This is a 1-day hackathon prototype demonstrating semantic search inside a faithful recreation of the Marrow app shell. Day ends in a live demo.

Team: 1 backend dev (Python + vector DB), 1 frontend dev (this codebase). Frontend uses mock data until the backend is ready.

## Product principle

Input is intelligent — natural language, synonyms, abbreviations, and typos all handled. **Output is Marrow content only.** No AI-generated summaries. The system surfaces existing content more accurately; it does not write content.

## Goals for the demo

Two parts:

1. **App shell**: a believable Marrow app the judges can tap through — Home, QBank, Tests, Videos tabs all rendering visibly correct first-level screens.
2. **Three hero search flows** that must work flawlessly:
   - Synonym / abbreviation expansion — e.g., "MI" → Myocardial Infarction content
   - Natural-language query — e.g., "mechanism of beta blockers in HF"
   - Typo correction — e.g., "pantaprazole" → Pantoprazole

The search experience is the hero. The tab screens set context so judges feel they're looking at the real product.

## App shell — bottom tabs and first-level screens

Four tabs in the bottom nav. Each renders one screen. No drill-down into content. Every tab header includes a search icon (top right) that launches the search flow.

See screenshots `IMG_1368.PNG` through `IMG_1374.PNG` for visual reference. Match the existing Marrow design language — light teal headers, clean cards, generous spacing, system sans-serif.

### Home tab (IMG_1368, IMG_1369, IMG_1370, IMG_1371)

Scrollable feed with:

- Teal header with hamburger menu, "Marrow" wordmark + "PRO" badge, bookmark icon, search icon
- Big circular progress counter ("780 Modules completed")
- **Featured** section — Grand Test card with laurel-wreath visual
- "Live Now | NEET Pattern" indicator
- **MCQ of the Day** with full question text and 4 options (A–D). Mock content: pregnant woman / congenital adrenal hyperplasia / drug of choice — options Dexamethasone, Betamethasone, Hydrocortisone, Prednisolone
- **Suggested Tests of the Day** — Clinical Mini Test card with LIVE badge and expiry
- **Solve Next** — module card based on "your last solved module"
- **Watch Next** — video card based on "your last watched video"
- **Pearls** card (yellow tile, "2165 pearls")
- **Recent Updates** card
- **Magic Module** card (green tile, "Module 13 LIVE now!")
- "Share Marrow" link

### QBank tab (IMG_1372)

- Teal header with title "QBank Edition 8"
- **QBank tracker** card with trend-up icon (chevron)
- "Solve Next" horizontal row with last attempted module
- Two side-by-side cards: **Bookmarks** (count) and **Custom Module** ("Customised MCQs")
- **Subject list** — each row: circular subject icon, subject name, green progress bar with "X/Y modules" caption. At least: Anatomy, Biochemistry, Physiology, Pharmacology, Microbiology, Pathology

### Tests tab (IMG_1373)

- Teal header with title "Tests"
- Sub-tab strip: **Grand Tests** (active), Mini Tests, Subject Tests — visual only, no switching needed
- "Your overall progress in GTs" card with chart icon
- Year selector row ("MAY 2025–26" style)
- Month groupings: "JUN (Current Month)" and "JUL (Upcoming Month)"
- Test cards under each month: title, schedule (Live till / Live on), duration, MCQ count, PRO badge, optional LIVE indicator with red dot
- The current-month live test gets a light yellow highlight background

### Videos tab (IMG_1374)

- Teal header with title "Videos Edition 8"
- Two top buttons: **Downloaded** and **Sample Videos**
- **World of Revision** featured card (yellow tile, "NEW" badge)
- **Watch Next** card with the user's next video
- "Subjects" label + "Sort by: Default" dropdown (visual only)
- **2-column grid of subjects** — each card has a large circular icon (top), subject name, "X/Y modules" with green progress bar

## Search flow (launched from search icon in any tab header)

The search experience overlays the active tab — full screen, with its own back arrow that returns to whatever tab was open.

Three screens for the search flow (see earlier mockups already shared):

### Pre-search screen

Empty state shown when the user enters search.

- Teal header with search bar (placeholder: "Search videos, QBank, tests…") and back arrow
- "Recent searches" — 4 chips (e.g., Cardiac cycle, Anti-TB drugs, Renal physiology, MI management)
- "Trending in NEET-PG · This week" — numbered list of 4 trending topics, each with a trend-up arrow on the right
- Bottom nav visible (matches the rest of the app)

### Autosuggest

Live suggestions as the user types.

- Search bar showing typed query
- Suggestion list; each row: search icon + bold term + subtitle context + up-arrow (tap fills query into the search bar)
- Suggestion types: concept expansion, subtopic, common intent, disambiguation

### Results

- Search bar with the query and a filter icon (visual only)
- Blue interpretation card: "Showing results for [query] · understood as [canonical]" with related-concept chips
- Tab strip — All, Videos, QBank, Modules, Pearls
- Results grouped by content type with section headers (e.g., "VIDEOS & TIMESTAMPS · 3")
- Each card: thumbnail, title, metadata line, match badge ("exact: X" or "related: Y")

## Edge states in the search flow

### Spelling correction (typo)

Light info banner (NOT red — use neutral or amber): "Showing results for [corrected] · Search instead for '[original]'". Normal results for the corrected term shown below.

### No results

Empty state with magnifying glass icon, message "No exact matches for [query]," and a "Did you mean a concept like…" panel with related-concept chips.

### Synonym expansion

Interpretation card explains: "[term A] = [term B] — showing results for both spellings." Related concepts as chips below.

## Build priority

Build in this order. The search flow is the hero — do not let tab polish eat search time.

1. **App shell** — bottom nav with 4 tabs, working tab switching, MobileFrame wrapper
2. **Search flow** — pre-search → autosuggest → results screen with interpretation card, match badges, grouping, best-match star
3. **Home tab** — visually faithful to the screenshot, mock content
4. **QBank tab** — visually faithful, mock content
5. **Tests tab** — visually faithful, mock content
6. **Videos tab** — visually faithful, mock content
7. **Search edge states** — typo banner, no-results, synonym expansion

If time runs short, tab screens can ship at 70% fidelity. The search flow must hit 100%.

## Out of scope

- Filter modal
- Concept cards (textbook-style definitions)
- AI summary cards
- Real Marrow data integration
- Authentication
- Native mobile app
- Drilling into any content (videos, modules, QBank questions, pearls)
- Hamburger menu / bookmark icon functionality
- Dark mode
- Animations beyond basic transitions

## Mock data — demo-prepped queries

The frontend ships with a mock API layer keyed by query string. These queries must produce well-tuned results:

| Query | Expected behavior |
|---|---|
| `heart failure` | Grouped results across video/QBank/pearl |
| `IBD` | Interpretation card with UC + Crohn's as related concepts |
| `MI` | Expand to Myocardial Infarction; cardio content |
| `mechanism of beta blockers in HF` | Natural-language query; matched-snippet style results |
| `pantaprazole` | Typo banner; results for Pantoprazole |
| `bowl inflamation` | No-results state + did-you-mean IBD / UC |
| (anything else) | Fallback to a small generic result set |

## Design

Match the screenshots visually. Brand palette:

- Primary teal: `#5DCAA5` — header background (also seen slightly lighter/cyan in some screens; let the dev tune)
- Dark teal: `#0F6E56` — active text, dark badges
- Pale teal: `#E1F5EE` — chip backgrounds, match pills
- Accent blue: `#378ADD` — content-type icons, hyperlinks
- Highlight amber: `#FAEEDA` — matched-snippet background, typo banner, featured cards
- Pearl yellow: `#FBC02D` to `#F9A825` range — Pearls tile
- Magic green: `#E8F5E9` to `#C8E6C9` — Magic Module tile
- Progress green: `#9CCC65` — progress bars
- Content white, light gray `#F7F7F5` page background

Typography: system sans-serif. Generous spacing, rounded corners (8–12px), thin neutral borders. Mobile-first 380px content width inside a phone-frame container so the projected demo looks like the mockups.

## Demo flow (for the live presentation)

1. Open app on Home tab — let the modules counter and MCQ of the day register with judges
2. Tap through QBank → Tests → Videos to show the shell is real
3. Return to Home, tap the search icon
4. Run hero query 1 (synonym — `MI`)
5. Run hero query 2 (natural language — `mechanism of beta blockers in HF`)
6. Run hero query 3 (typo — `pantaprazole`)
7. Closing 30 seconds: phase 1 → 2 → 3 roadmap (what we'd build next)
