# Marrow Semantic Search — Backend PRD

## Context

1-day hackathon project. The backend powers a new semantic search feature for Marrow's medical-education app, replacing keyword-only search with a vector-based semantic search. Frontend (React) is built separately and ships with a mock API layer that will be swapped for this backend when ready.

Final goal: live demo. Three hero queries must work flawlessly:

- `MI` → expand to Myocardial Infarction, return cardio content
- `mechanism of beta blockers in HF` → natural-language semantic match
- `pantaprazole` → spell-correct to Pantoprazole, return PPI content

See `PRD.md` for product context.

## What the backend does

1. Index a curated corpus of mock medical content (video transcript chunks, QBank explanations, pearls, modules) into a vector DB
2. Handle natural-language queries with semantic understanding
3. Expand medical abbreviations (MI → Myocardial Infarction)
4. Correct typos (pantaprazole → Pantoprazole)
5. Detect no-results cases and suggest related concepts
6. Return structured JSON matching the frontend's expected contract

## Tech stack

- **Python 3.10+**
- **FastAPI** — async HTTP API, auto-generates OpenAPI docs, near-zero setup
- **ChromaDB** — vector storage that runs locally, no signup, persists to disk
- **sentence-transformers** (`all-MiniLM-L6-v2` is fast and good enough) — free embeddings that run locally; alternative is OpenAI `text-embedding-3-small` if you want slightly better quality
- **pyspellchecker** or **thefuzz** — typo correction
- **uvicorn** — to serve the API

```bash
pip install fastapi uvicorn chromadb sentence-transformers pyspellchecker
```

## API contract (must match — frontend is built against it)

### `GET /api/search`

Query param: `q` (required) — the user's search query.

Response shape:

```json
{
  "query": "MI",
  "interpreted_as": "Myocardial Infarction",
  "related_concepts": ["STEMI", "NSTEMI", "Acute Coronary Syndrome"],
  "spelling_correction": null,
  "results": [
    {
      "id": "vid_001",
      "type": "video",
      "title": "Acute Myocardial Infarction — Diagnosis",
      "subject": "Medicine",
      "metadata": "42 min · ★ 4.7",
      "match_type": "exact",
      "match_concept": "MI",
      "is_best_match": true,
      "thumbnail_url": null
    }
  ],
  "no_results": false,
  "suggestions": []
}
```

Notes:
- `type` is one of: `"video" | "timestamp" | "qbank" | "module" | "pearl" | "clinical_q"`
- `match_type` is `"exact"` (matched the user's literal query) or `"related"` (matched a related concept like UC when user searched IBD)
- `is_best_match` is `true` for exactly one result across all results (the highest-relevance one)
- `metadata` is a pre-formatted display string — the frontend renders it as-is

**Typo case** — `spelling_correction` is set:

```json
{
  "query": "pantaprazole",
  "interpreted_as": "Pantoprazole",
  "spelling_correction": { "original": "pantaprazole", "corrected": "Pantoprazole" },
  "related_concepts": ["Omeprazole", "Esomeprazole", "PPI"],
  "results": [...],
  "no_results": false
}
```

**No-results case** — `no_results: true` with concept suggestions:

```json
{
  "query": "bowl inflamation",
  "no_results": true,
  "suggestions": ["Inflammatory Bowel Disease", "Ulcerative Colitis", "Bowel obstruction"],
  "results": [],
  "interpreted_as": null,
  "related_concepts": []
}
```

### `GET /api/suggest`

For the autosuggest dropdown as the user types. Lower priority — skip if time runs out.

Query param: `q` — the partial query.

Response:

```json
{
  "query": "IBD",
  "suggestions": [
    { "text": "IBD", "context": "Inflammatory Bowel Disease", "type": "concept" },
    { "text": "Ulcerative Colitis", "context": "a type of IBD", "type": "subtopic" },
    { "text": "Crohn's Disease", "context": "a type of IBD", "type": "subtopic" },
    { "text": "IBD — management", "context": "common intent", "type": "intent" },
    { "text": "IBD vs IBS", "context": "frequently confused", "type": "disambiguation" }
  ]
}
```

Suggestion types: `concept` | `subtopic` | `intent` | `disambiguation`.

For the hackathon, autosuggest can be served from a hand-curated lookup table keyed by query prefix — semantic suggest is overkill for one day.

## Pipeline architecture

```
User query
   │
   ▼
[1] Preprocess
    - Lowercase, strip
    - Abbreviation expansion (MI → Myocardial Infarction)
    - Spell correction (pantaprazole → Pantoprazole)
   │
   ▼
[2] Embed query (sentence-transformers)
   │
   ▼
[3] Vector search (ChromaDB top-K=20, cosine similarity)
   │
   ▼
[4] Post-process
    - Filter low-similarity (threshold ~0.4) → no_results path
    - Tag each result with match_type (exact / related)
    - Mark single best_match (highest score)
    - Sort/group by content_type for the response
   │
   ▼
JSON response
```

## Data model — content corpus

Each chunk indexed in ChromaDB:

```python
{
  "id": str,                # unique, e.g. "vid_001"
  "type": str,              # video | timestamp | qbank | module | pearl | clinical_q
  "title": str,
  "subject": str,           # "Cardiology", "Gastroenterology", "Pharmacology", ...
  "content": str,           # the text actually embedded (transcript paragraph,
                            # MCQ explanation, pearl content, etc.)
  "metadata": dict          # type-specific display fields (duration, rating, etc.)
}
```

The `content` field is what gets embedded. The `title` is shown to the user, but embedding the body text is what gives semantic search its power.

## Mock corpus — what to curate

Target: ~150–200 chunks. Focus the bulk on subjects relevant to the demo queries:

- **Cardiology** (~50 chunks) — heart failure, beta blockers, MI/STEMI/NSTEMI, arrhythmias, valvular disease
- **Gastroenterology** (~40 chunks) — IBD, Ulcerative Colitis, Crohn's, GERD, peptic ulcers, Pantoprazole/PPIs
- **Pharmacology** (~40 chunks) — beta blockers, ACE inhibitors, diuretics, PPIs, drug mechanisms
- **Filler** (~20 chunks) — neurology, respiratory, endocrine to make non-demo queries return something plausible

Each subject should include a mix of content types — videos, QBank, pearls, modules — so the result grouping has variety to show.

Don't try to source real Marrow content — write plausible mock text yourself, or ask Claude to generate it. The data wrangling is the time sink to avoid.

## Required demo queries — expected backend behavior

| Query | Expected response |
|---|---|
| `heart failure` | Direct semantic match. No `interpreted_as`, no `spelling_correction`. Return ~8–10 HF results grouped across videos/QBank/pearls. |
| `IBD` | `interpreted_as: "Inflammatory Bowel Disease"`, `related_concepts: ["Ulcerative Colitis", "Crohn's Disease"]`. Return IBD/UC/Crohn's content; mark `match_type` correctly (exact for IBD content, related for UC/Crohn's). |
| `MI` | `interpreted_as: "Myocardial Infarction"`, `related_concepts: ["STEMI", "NSTEMI", "Acute Coronary Syndrome"]`. Cardiology results only. |
| `mechanism of beta blockers in HF` | No `interpreted_as`. Natural-language semantic match against beta blocker pharmacology + HF management content. The single highest-relevance result is `is_best_match: true`. |
| `pantaprazole` | `spelling_correction: {original: "pantaprazole", corrected: "Pantoprazole"}`, `interpreted_as: "Pantoprazole"`. Return Pantoprazole/PPI content. |
| `bowl inflamation` | `no_results: true`, `suggestions: ["Inflammatory Bowel Disease", "Ulcerative Colitis", "Bowel obstruction"]`, empty `results`. |
| (anything else) | Fallback: top-K semantic matches with no expansion or correction. Always return at least 3–5 results to avoid empty-state weirdness. |

**These six queries must look impressive.** Tune the index, thresholds, and dictionaries until they do. Hard-code edge cases if needed — this is a demo, not production.

## Abbreviation dictionary

Curate ~30–50 entries. Hardcode in Python:

```python
ABBREVIATIONS = {
    "MI": "Myocardial Infarction",
    "HF": "Heart Failure",
    "CHF": "Congestive Heart Failure",
    "HFrEF": "Heart Failure with Reduced Ejection Fraction",
    "HFpEF": "Heart Failure with Preserved Ejection Fraction",
    "ACS": "Acute Coronary Syndrome",
    "IBD": "Inflammatory Bowel Disease",
    "UC": "Ulcerative Colitis",
    "GERD": "Gastroesophageal Reflux Disease",
    "PPI": "Proton Pump Inhibitor",
    "HTN": "Hypertension",
    "DM": "Diabetes Mellitus",
    "T2DM": "Type 2 Diabetes Mellitus",
    "COPD": "Chronic Obstructive Pulmonary Disease",
    "TB": "Tuberculosis",
    "ARDS": "Acute Respiratory Distress Syndrome",
    "CKD": "Chronic Kidney Disease",
    "AKI": "Acute Kidney Injury",
    # ... extend to ~30–50
}

RELATED_CONCEPTS = {
    "Inflammatory Bowel Disease": ["Ulcerative Colitis", "Crohn's Disease"],
    "Myocardial Infarction": ["STEMI", "NSTEMI", "Acute Coronary Syndrome"],
    "Heart Failure": ["HFrEF", "HFpEF", "Cardiomyopathy"],
    "Pantoprazole": ["Omeprazole", "Esomeprazole", "PPI"],
    # ...
}
```

Logic: if query (case-insensitive) is in `ABBREVIATIONS`, set `interpreted_as` to the expanded form, look up `RELATED_CONCEPTS` for that form, and embed the expanded form (not the abbreviation) for the vector search.

## Spell correction

Use `pyspellchecker` with a custom medical dictionary:

```python
from spellchecker import SpellChecker

spell = SpellChecker(language=None, distance=2)
spell.word_frequency.load_words([
    "pantoprazole", "omeprazole", "esomeprazole", "rabeprazole",
    "atorvastatin", "rosuvastatin",
    "metoprolol", "carvedilol", "bisoprolol",
    # ... ~100 commonly-tested drug names + conditions
])
```

Flow:
1. Try the query as-is against the corpus first
2. If top vector similarity is below a confidence threshold (~0.55), check if `spell.correction(query)` differs from the query
3. If yes, search with the corrected term and set `spelling_correction` in the response

Drug names yield the highest spell-correction value for med students — seed the dictionary with the most commonly-tested ones.

## No-results detection

Trigger `no_results: true` when **both**:
- Top vector similarity is below ~0.4
- Spell correction doesn't yield a confident alternative

For `suggestions`, use the closest semantic concepts in the index. For the demo, you can also hard-code a small fallback map for known-bad queries (e.g., `bowl inflamation` → `[IBD, UC, Bowel obstruction]`) to ensure the demo case lands.

## Build priority (with rough time estimates)

For ~8–10 working hours:

1. **FastAPI skeleton + ChromaDB setup** — `/search` endpoint returning hardcoded JSON. Verify the frontend can hit it and parse the response. (~1 hr)
2. **Index ~150 mock content chunks** with sentence-transformers embeddings. (~2 hr — most of this is writing the mock content)
3. **Real semantic search** wired into `/search`. Top-K retrieval, no post-processing yet. (~1 hr)
4. **Abbreviation expansion layer** + `related_concepts` lookup. (~1 hr)
5. **Spell correction** for the typo case. (~1 hr)
6. **No-results detection + suggestions**. (~1 hr)
7. **Tune for the 6 hero queries** — adjust thresholds, fix individual queries, hard-code edge cases as needed. **This step matters more than people realize.** (~1 hr)
8. **`/suggest` endpoint** from a hand-curated lookup table, if time allows. (~1 hr — skip if behind)

If you're falling behind, the safest cuts are:
- Drop `/suggest` (the frontend can skip the autosuggest screen)
- Drop the `clinical_q` and `timestamp` content types (focus on video/qbank/pearl/module)

Never cut: the 6 hero queries must work.

## Performance

Not critical for a demo — judges aren't benchmarking. But:
- Pre-load the embedding model on server startup, not per request
- Local ChromaDB is fast enough out of the box
- Aim for <1s response time end-to-end

## What NOT to build

- Authentication / authorization
- Real-time content ingestion / re-indexing
- Hybrid (vector + BM25) search — pure vector is fine for the demo
- Result personalization
- Multi-tenancy
- Logging / observability beyond `print()` statements
- Database for users / sessions
- Rate limiting
- Docker / containerization (just `uvicorn main:app --reload`)

## Deployment

Run locally. Both frontend and backend run on the presenter's laptop for the demo. CORS needs to be open so the frontend can hit `http://localhost:8000`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # fine for hackathon
    allow_methods=["*"],
    allow_headers=["*"],
)
```

If the venue has flaky Wi-Fi, both processes still run locally — no cloud dependency.

## Coordination with frontend

The frontend currently uses mock data matching the API contract above. Once `/search` is returning real responses, swap by setting `VITE_USE_MOCK_API=false` and `VITE_API_BASE_URL=http://localhost:8000` in the frontend's `.env`.

Test the integration with at least one query (`heart failure` is a good first one — no expansion/correction logic involved) before tuning the others.
