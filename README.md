# Marrow-ito Search

Semantic search prototype for NEET-PG content
(Subjects → Topics → Lessons → QBanks → MCQs, plus Videos and Tests).

The repo has two independent parts:

| Part | Path | Stack |
| --- | --- | --- |
| **Backend** — Flask API + data pipeline | `./` (`app/`, `scripts/`, `data/`) | Python 3.10+, Flask 3, MongoDB, FAISS |
| **Frontend** — search UI | `./marrow-search/` | React 19, TypeScript, Vite, Tailwind |

The backend runs on `http://127.0.0.1:5001` and the frontend dev server points
at it via `VITE_API_BASE_URL`.

---

## Prerequisite: MedMCQA dataset

Both the subject extraction and the MCQ ingestion steps need a **MedMCQA**
dump. Download it and place it in the repo (e.g. `data/medmcqa.json`). A JSON
array (`medmcqa.json`) or line-delimited JSONL (`medmcqa.jsonl`) is accepted —
the loaders auto-detect the format. Each record must include at least
`question`, `subject_name`, and the answer/option fields.

> The dataset is **not** committed to the repo. Obtain it from the official
> MedMCQA source and reference its path when running the scripts below.

---

## Backend

### Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** for dependency management
- **MongoDB** running locally (or reachable via URI)
- **`medmcqa.json`** (see the prerequisite above)

### Setup

From the repo root:

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment (create a .env if you need non-default values)
cat > .env <<'EOF'
MONGO_URI=mongodb://localhost:27017
MONGO_DB=marrow_ito_search
FLASK_HOST=127.0.0.1
FLASK_PORT=5001
FLASK_DEBUG=true
EOF
```

All `.env` values are optional; the defaults above are baked into
`app/config.py`.

### Run the API

```bash
uv run python run.py
```

The Flask app serves both the JSON API (`/api/...`) and the server-rendered
browse pages at <http://127.0.0.1:5001>. With an empty DB you'll see
"No subjects yet" — populate the taxonomy next.

### Populate the taxonomy

Run in order. All scripts read/write under `data/`.

#### 1. Extract canonical subjects from the MedMCQA dump

Maps the raw MedMCQA `subject_name` values (21 distinct, some outdated naming)
to the canonical NEET-PG 2026 taxonomy (19 subjects in 3 categories).

```bash
uv run python scripts/extract_subjects.py data/medmcqa.json
# writes: data/subjects.json
```

#### 2. Enrich subjects with topics and lessons

Scrapes the public NEET-PG syllabus reference page and populates each subject's
`topics` and `lessons` (sub-topics).

```bash
uv run python scripts/enrich_syllabus.py
# reads:  data/subjects.json
# writes: data/subjects_with_syllabus.json
```

> Psychiatry and Anesthesia aren't on the syllabus reference page — they'll
> show as empty in the output. Edit the JSON to add them manually if needed.

#### 3. Seed MongoDB

Inserts Subjects, Topics, Lessons, and one QBank per Lesson, with proper
ObjectId references between them.

```bash
uv run python scripts/seed_taxonomy.py
```

Re-running drops and recreates the four owned collections by default. Pass
`--no-drop` to append instead.

#### 4. Ingest MCQs (semantic match to lessons)

Samples MedMCQA records, embeds each MCQ via PubMedBERT, searches a per-subject
FAISS index built from the seeded lessons, and inserts each MCQ into the
matched lesson's qbank — but only if cosine similarity meets the threshold.
Heavy deps (`torch`, `sentence-transformers`, `faiss-cpu`) live in a separate
group and need a one-time install.

```bash
# One-time: install ingest deps (~700MB, includes PyTorch)
uv sync --group ingest

# Then run (first run downloads the embedding model ~500MB)
uv run --group ingest python scripts/ingest_mcqs.py data/medmcqa.json
# defaults: --sample-size 500 --threshold 0.6 \
#           --model pritamdeka/S-PubMedBert-MS-MARCO
```

Re-runs dedupe by MedMCQA `id` (stored as `source_id` on the MCQ doc).

#### 5. Build the search indexes

Additional scripts under `scripts/` build the FAISS search, notes, transcript,
and recent-updates indexes that power the `/api/search` endpoint (e.g.
`build_search_index.py`, `build_notes_index.py`, `build_transcript_index.py`).

### Browse the data

After seeding, open <http://127.0.0.1:5001> to walk the hierarchy:

```
/                       list of subjects
/subjects/<id>          topics under a subject
/topics/<id>            lessons under a topic
/lessons/<id>           qbanks and videos for a lesson
/qbanks/<id>            MCQs in a qbank
/mcqs/<id>              MCQ detail
/videos/<id>            video detail
/tests                  list of tests
/tests/<id>             MCQs in a test
```

### Backend layout

```
marrow_ito/
├── pyproject.toml          # uv-managed (Flask 3, PyMongo, Pydantic v2)
├── run.py                  # entry point
├── app/
│   ├── __init__.py         # Flask app factory
│   ├── config.py           # env-driven settings
│   ├── db.py               # singleton Mongo client + collection names
│   ├── models/             # Pydantic v2 models
│   ├── repositories/       # thin per-entity Mongo wrappers
│   ├── routes/             # api.py, search.py, browse.py, crud.py, ...
│   ├── services/           # search, embedder, autocomplete, synonyms, ...
│   └── templates/          # Jinja templates (server-rendered HTML)
├── scripts/                # data extraction, seeding, ingest, index builds
└── data/                   # generated JSON inputs + FAISS indexes
```

---

## Frontend (`marrow-search`)

React + TypeScript + Vite single-page app for the search experience.

### Prerequisites

- **Node.js 18+**
- **npm** (a `package-lock.json` is committed)

### Setup

```bash
cd marrow-search
npm install
```

### Configure the API endpoint

The client reads two Vite env vars (create `marrow-search/.env.local`):

```
# Talk to the local backend instead of the bundled mock data
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=http://127.0.0.1:5001
```

- `VITE_USE_MOCK_API` defaults to mock mode (`true`). Set it to `false` to call
  the real backend.
- `VITE_API_BASE_URL` defaults to `http://localhost:8000` — point it at the
  Flask backend (`http://127.0.0.1:5001`) when running live.

### Run the dev server

```bash
npm run dev
```

Vite prints a local URL (default <http://localhost:5173>). Make sure the
backend is running first if you've disabled mock mode.

### Other scripts

```bash
npm run build      # type-check + production build to dist/
npm run preview    # serve the production build locally
npm run lint       # eslint
```

---

## Out of scope right now

- **Auth, CI, tests**: POC scope.
