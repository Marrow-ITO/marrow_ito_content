# Marrow-ito-search

Standalone Flask app for prototyping semantic search across NEET-PG content
(Subjects → Topics → Lessons → QBanks → MCQs, plus Videos and Tests).
Independent of the parent `rounds_api` codebase: its own venv, its own MongoDB
database, its own dependencies.

## Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** for dependency management
- **MongoDB** running locally (or reachable via URI)

## Setup

From this directory (`marrow_ito_search/`):

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env if your Mongo isn't on localhost:27017 or you want a different DB name
```

`.env` defaults:

```
MONGO_URI=mongodb://localhost:27017
MONGO_DB=marrow_ito_search
FLASK_HOST=127.0.0.1
FLASK_PORT=5001
FLASK_DEBUG=true
```

## Run the app

```bash
uv run python run.py
```

Open <http://127.0.0.1:5001>. With an empty DB you'll see "No subjects yet" —
populate the taxonomy next.

## Populate the taxonomy

Three scripts, run in order. All read/write under `data/`.

### 1. Extract canonical subjects from a MedMCQA dump

Maps the raw MedMCQA `subject_name` values (21 distinct, some outdated naming)
to the canonical NEET-PG 2026 taxonomy (19 subjects in 3 categories).

```bash
uv run python scripts/extract_subjects.py /path/to/medmcqa.jsonl
# writes: data/subjects.json
```

### 2. Enrich subjects with topics and lessons

Scrapes the prepladder NEET-PG syllabus page and populates each subject's
`topics` and `lessons` (sub-topics).

```bash
uv run python scripts/enrich_syllabus.py
# reads:  data/subjects.json
# writes: data/subjects_with_syllabus.json
```

> Psychiatry and Anesthesia aren't on the prepladder page — they'll show as
> empty in the output. Edit the JSON to add them manually if needed.

### 3. Seed MongoDB

Inserts Subjects, Topics, Lessons, and one QBank per Lesson, with proper
ObjectId references between them. MCQs / Videos / Tests collections are not
touched.

```bash
uv run python scripts/seed_taxonomy.py
```

Re-running drops and recreates the four owned collections by default. Pass
`--no-drop` to append instead.

### 4. Ingest MCQs (semantic match to lessons)

Samples MedMCQA records, embeds each MCQ via PubMedBERT, searches a per-subject
FAISS index built from the seeded lessons, and inserts each MCQ into the
matched lesson's qbank — but only if cosine similarity meets the threshold.
Heavy deps (`torch`, `sentence-transformers`, `faiss-cpu`) live in a separate
group and need a one-time install.

```bash
# One-time: install ingest deps (~700MB, includes PyTorch)
uv sync --group ingest

# Then run (first run downloads the embedding model ~500MB)
uv run --group ingest python scripts/ingest_mcqs.py /path/to/medmcqa.jsonl
# defaults: --sample-size 500 --threshold 0.6 \
#           --model pritamdeka/S-PubMedBert-MS-MARCO
```

Re-runs dedupe by MedMCQA `id` (stored as `source_id` on the MCQ doc).

## Browse the data

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

## Project layout

```
marrow_ito_search/
├── pyproject.toml          # uv-managed (Flask 3, PyMongo, Pydantic v2)
├── .env.example
├── run.py                  # entry point
├── app/
│   ├── __init__.py         # Flask app factory
│   ├── config.py           # env-driven settings
│   ├── db.py               # singleton Mongo client + collection names
│   ├── models/             # Pydantic v2 models (Subject, Topic, Lesson,
│   │                       #   QBank, Video, MCQ, Test)
│   ├── repositories/       # thin per-entity Mongo wrappers
│   ├── routes/browse.py    # hierarchical browse routes
│   └── templates/          # Jinja templates (server-rendered HTML)
├── scripts/
│   ├── extract_subjects.py
│   ├── enrich_syllabus.py
│   └── seed_taxonomy.py
└── data/                   # generated JSON inputs (gitignored if you choose)
```

## Out of scope right now

- **Search**: the actual semantic-search layer this app exists to prototype —
  not built yet.
- **MCQ / Video / Test population**: schema is defined, collections stay empty
  until a separate ingestion script lands.
- **Tests, auth, CI**: POC scope.
