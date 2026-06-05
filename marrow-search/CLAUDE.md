# CLAUDE.md — Marrow Search Frontend

## Project

Mobile-friendly web app prototype of the Marrow medical-education app with a new semantic search feature. Built for a 1-day hackathon ending in a live demo. Backend (Python + vector DB) is being built separately; this codebase ships with a mock API layer that can be swapped for the real backend via an env flag.

See `PRD.md` for product context. Two sets of reference images:

- **Search mockups** (3 images) — the new search flow this project is demonstrating
- **Marrow app screenshots** (`IMG_1368.PNG`–`IMG_1374.PNG`) — the existing app shell (Home, QBank, Tests, Videos tabs) that needs to be recreated as the wrapper around the search feature

## Tech stack

- **Vite + React 18 + TypeScript** — fastest hackathon setup
- **Tailwind CSS** — utility-first styling
- **Lucide React** — icons
- **Plain `fetch()`** for API calls (no React Query for this scope)
- **No router** — single-page app; tab switching and search-modal state managed in React state

## Setup

```bash
npm create vite@latest marrow-search -- --template react-ts
cd marrow-search
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install lucide-react
npm run dev
```

Configure Tailwind to scan `./src/**/*.{ts,tsx}` and extend the theme with brand colors (see Design tokens below).

Set `tsconfig.json` to `"strict": false` initially — less friction during the hackathon.

## App architecture

A single `<App>` component manages two pieces of state:

```typescript
type AppState = {
  activeTab: 'home' | 'qbank' | 'tests' | 'videos';
  searchOpen: boolean;
};
```

- When `searchOpen === false`: render `<MobileFrame>` → active tab screen + `<BottomNav>`
- When `searchOpen === true`: render `<MobileFrame>` → `<SearchExperience>` (full-screen overlay over the current tab)

The search icon in every tab header sets `searchOpen = true`. The back arrow inside the search flow sets it back to `false`, returning to whichever tab was active.

## File structure

```
src/
  components/
    layout/
      MobileFrame.tsx          // 380px phone-shaped container
      BottomNav.tsx            // Home / QBank / Tests / Videos
      TabHeader.tsx            // Teal header used by all 4 tabs
    tabs/
      HomeTab.tsx              // IMG_1368-1371
      QBankTab.tsx             // IMG_1372
      TestsTab.tsx             // IMG_1373
      VideosTab.tsx            // IMG_1374
    home/                      // Home-tab sub-components
      ModulesCounter.tsx
      FeaturedCard.tsx
      McqOfTheDay.tsx
      SuggestedTestCard.tsx
      SolveNextCard.tsx
      WatchNextCard.tsx
      PearlsCard.tsx
      RecentUpdatesCard.tsx
      MagicModuleCard.tsx
    qbank/
      QBankTrackerCard.tsx
      SubjectListItem.tsx
    tests/
      TestProgressCard.tsx
      TestSubTabStrip.tsx
      TestListItem.tsx
    videos/
      SubjectGridCard.tsx
      WorldOfRevisionCard.tsx
    search/
      SearchExperience.tsx     // Wrapper managing search states
      SearchBar.tsx            // Search input + back arrow + filter icon
      PreSearchScreen.tsx      // Recent + trending
      AutosuggestPanel.tsx     // Live suggestions
      ResultsScreen.tsx        // Main results page
      InterpretationCard.tsx   // Blue semantic-understanding card
      ResultGroup.tsx          // Section header + cards for one content type
      ResultCard.tsx           // Individual result row
      MatchBadge.tsx           // "exact: X" / "related: Y" pill
      TypoBanner.tsx           // "Showing results for X" info banner
      NoResultsState.tsx       // Empty state + did-you-mean
      TabStrip.tsx             // All / Videos / QBank tabs in results
  hooks/
    useSearch.ts               // Search state machine
  lib/
    apiClient.ts               // Switches between mock and real backend
    mockApi.ts                 // Hard-coded responses keyed by query
  data/
    mockHome.ts                // Home tab mock content
    mockQBank.ts               // QBank tab mock content
    mockTests.ts               // Tests tab mock content
    mockVideos.ts              // Videos tab mock content
    mockContent.ts             // Search result mock content
    mockSuggestions.ts         // Autosuggest seed data
  types/
    index.ts                   // Shared TypeScript types
  App.tsx
  main.tsx
  index.css                    // Tailwind base
```

## API contract (proposed — backend not yet finalized)

Use these shapes in `mockApi.ts`. All backend calls go through `apiClient.ts` so the real endpoints can be swapped in without touching components.

### `GET /api/search?q={query}`

```typescript
type SearchResponse = {
  query: string;
  interpreted_as: string | null;
  related_concepts: string[];
  spelling_correction?: { original: string; corrected: string };
  results: SearchResult[];
  no_results?: boolean;
  suggestions?: string[];
};

type SearchResult = {
  id: string;
  type: 'video' | 'timestamp' | 'qbank' | 'module' | 'pearl' | 'clinical_q';
  title: string;
  subject: string;
  metadata: string;            // e.g., "42 min · ★ 4.7" or "34 questions"
  match_type: 'exact' | 'related';
  match_concept: string;       // e.g., "IBD" or "Ulcerative Colitis"
  is_best_match?: boolean;
  thumbnail_url?: string;
};
```

### `GET /api/suggest?q={partial_query}`

```typescript
type SuggestResponse = {
  query: string;
  suggestions: {
    text: string;              // bold portion
    context?: string;          // subtitle
    type: 'concept' | 'subtopic' | 'intent' | 'disambiguation';
  }[];
};
```

Switch between mock and real backend via env var:

```
VITE_USE_MOCK_API=true               # default for hackathon
VITE_API_BASE_URL=http://localhost:8000  # for when backend is ready
```

## Mock data — required demo queries

`mockApi.ts` must return well-tuned responses for these queries:

| Query | Behavior |
|---|---|
| `heart failure` | Grouped results across video/QBank/pearl, no spelling correction |
| `IBD` | Interpretation card showing "Inflammatory Bowel Disease" with UC + Crohn's as related concepts |
| `MI` | Expand to "Myocardial Infarction"; show cardio content |
| `mechanism of beta blockers in HF` | Natural-language query; results that look like the system understood intent |
| `pantaprazole` | `spelling_correction` set; results for Pantoprazole |
| `bowl inflamation` | `no_results: true`; `suggestions: ["Inflammatory Bowel Disease", "Ulcerative Colitis", "Bowel obstruction"]` |
| (anything else) | Fallback to a small generic result set |

All result rows should include realistic-looking medical content metadata.

## Tab screen mock data requirements

Each tab needs static mock data that visually matches the screenshots. Don't wire interactivity into these — they're purely visual.

### `mockHome.ts`
- `modulesCompleted: 780`
- `featuredTest`: title "Grand Test 17", "5 sections, 40 MCQs each", live status
- `mcqOfTheDay`: full antenatal screening / CAH question with 4 options (Dexamethasone, Betamethasone, Hydrocortisone, Prednisolone)
- `suggestedTest`: "Clinical Mini Test 4 - Management Protocols", LIVE, 20 questions, 21 mins, expires "05 Jun - 10:00"
- `solveNext`: "National Health Programmes II - NLEP, NTEP & NACO", Community Medicine, 4.6 stars, 24 MCQs
- `watchNext`: "Pharmacokinetics: Metabolism", Pharmacology, 4.6 stars, 38 min
- `pearlsCount: 2165`
- `recentUpdates`: last updated date (3 June 2026)
- `magicModule`: "Module 13 LIVE now!"

### `mockQBank.ts`
- Title "QBank Edition 8"
- Subjects with module progress: Anatomy (63/63), Biochemistry (28/28), Physiology (43/43), Pharmacology (67/67), Microbiology (35/35), Pathology (70/71)
- Bookmark count: 36
- Solve Next: same module as Home

### `mockTests.ts`
- Three sub-tabs (Grand / Mini / Subject) — Grand Tests active by default
- Tests grouped by month:
  - JUN (Current): Grand Test 17 (LIVE, live till 08 Jun, 210 mins, 200 MCQs), INICET Recall - May 2026 (24 Jun, 180 mins, 200 MCQs)
  - JUL (Upcoming): Grand Test 18 (01 Jul), Grand Test 19 (15 Jul), National NEET-PG Mock 2026
- All tests have PRO badge

### `mockVideos.ts`
- Title "Videos Edition 8"
- Top buttons: Downloaded, Sample Videos
- World of Revision card with NEW badge
- Watch Next: same Pharmacokinetics video as Home
- Subject grid (2×2 visible, more below): Anatomy (1/84), Biochemistry (1/53), Physiology (0/62), Pharmacology (4/75)

## Design tokens

Add to `tailwind.config.js` under `theme.extend.colors`:

```js
{
  brand: {
    teal: '#5DCAA5',            // primary teal (header bg)
    'teal-dark': '#0F6E56',     // dark teal (active text, dark badges)
    'teal-pale': '#E1F5EE',     // pale teal (chip bg, match pills)
    blue: '#378ADD',            // accent blue (content-type icons, links)
    'blue-pale': '#E6F1FB',     // pale blue (icon circle bg)
    amber: '#FAEEDA',           // highlight amber (snippet bg, banner, featured)
    'pearl-yellow': '#F9A825',  // Pearls tile
    'magic-green': '#E8F5E9',   // Magic Module tile bg
    'progress-green': '#9CCC65' // module progress bars
  },
  surface: {
    page: '#F7F7F5',            // page background outside content
  }
}
```

Other tokens:
- Radius: `rounded-lg` (8px) standard, `rounded-xl` (12px) cards, `rounded-[32px]` mobile frame
- Borders: thin, low-opacity neutral (`border border-black/10`)
- Typography: system font stack — no custom font for v1
- Text weights: 400 regular, 500 medium only — no 600/700

## Mobile frame component

The whole app renders inside a phone-shaped 380px-wide container so the projected demo looks like the mockups:

```tsx
// Sketch — adjust dimensions as needed
<div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
  <div className="w-[380px] h-[820px] bg-white rounded-[32px] border-[10px] border-black overflow-hidden shadow-2xl flex flex-col">
    {children}
  </div>
</div>
```

For real mobile devices, optionally hide the frame on small viewports and let the app fill the screen.

## Build priority

Build in this order. Stop wherever time runs out — the search flow is the hero; do not let tab-screen polish eat into search time.

1. **App shell** — MobileFrame, BottomNav (with tab switching), TabHeader, and stub tab screens (just colored placeholders is fine to start)
2. **Search flow** — full pipeline: SearchBar, PreSearchScreen, AutosuggestPanel, ResultsScreen with InterpretationCard + MatchBadge + ResultGroup + best-match star + related searches at bottom
3. **Search edge states** — TypoBanner, NoResultsState
4. **Home tab** — flesh out the screen to match IMG_1368–1371 (highest visual priority of the four tabs since judges see it first)
5. **QBank tab** — IMG_1372
6. **Tests tab** — IMG_1373
7. **Videos tab** — IMG_1374

Tab screens can ship at 70% fidelity if pressed. Search must hit 100%.

## Code conventions

- TypeScript with `strict: false` initially
- Components in PascalCase, one per file
- Hooks `useCamelCase`
- Shared types in `src/types/index.ts`; component-local types inline
- Tailwind utility classes inline; extract repeating patterns into components, not utility CSS
- No CSS modules / styled-components / emotion / SCSS
- Mock data is text-only (no real images) — use Lucide icons or plain divs for thumbnail placeholders
- Subject/content icons can be Lucide icons in colored circles (e.g., `<Heart>` for cardio, `<Pill>` for pharmacology, etc.)

## What NOT to build

- Filter modal
- Concept / definition cards (textbook style)
- AI summary cards
- Real backend integration (handled via env flag)
- Drilling into any content (videos, modules, MCQ answer reveal, pearl detail)
- Hamburger menu / bookmark icon functionality (visual only)
- Authentication
- Dark mode
- Animations beyond `transition-colors` / `transition-opacity`
- React Router

## Demo expectations

The app is projected live on a screen. Two parts to the demo:

1. **App shell walkthrough (~30 sec)**: tap through Home → QBank → Tests → Videos to show the app feels real
2. **Search flow (~2 min)**: run the three hero queries (`MI`, `mechanism of beta blockers in HF`, `pantaprazole`)

The hero queries (see mock data table) must work flawlessly. Everything else is supporting cast. Plan to record a backup video in case the venue Wi-Fi flakes.
