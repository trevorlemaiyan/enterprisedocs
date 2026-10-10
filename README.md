# EnterpriseDocs AI

A company knowledge-base assistant built on **retrieval-augmented generation (RAG)**. Employees ask questions in plain English; the system finds the relevant passages in the company's policy documents and answers **using only those passages, with citations** (document, page and section).

> "How many days of annual leave do employees get?"
> → *Full-time employees are entitled to 21 working days per leave year [1].*
> Source [1]: `Leave_Policy.pdf`, page 1, section "2. Annual Leave"

The sample knowledge base is four fictional Acme Services Ltd policies (HR, Leave, IT Support, Procurement). It is the companion to [OpsAgent](https://github.com/trevorlemaiyan/opsagent): OpsAgent acts on business *data*, EnterpriseDocs answers from business *documents*.

## Features

- PDF, text and Markdown ingestion with automatic removal of repeating headers and footers
- **Section-aware chunking**: chunks never cross a heading, so every answer cites a real section and page
- Pluggable embeddings: offline default for zero-setup, or semantic embeddings (e.g. Qwen via OpenRouter) by changing `.env`
- Persistent vector index with exact cosine search; rebuilt automatically if the embedding model changes
- **Grounded answers**: the model sees only retrieved passages, must cite them by number, and the API checks the citations are real
- **No-answer guard**: if nothing relevant is retrieved, the model is not called and the system says so instead of guessing
- Idempotent ingestion: unchanged files are skipped, edited files replaced, deleted files removed
- Safe document upload (type allow-list, size limit, path-traversal protection, rollback on failure)
- Retrieval evaluation script with an honest, measured report
- REST API with Swagger docs, interactive Web UI, Docker Compose, 130 tests, GitHub Actions CI

## Architecture

```text
                INGESTION (on startup, POST /ingest, POST /documents)
 PDF / TXT / MD ──► loader ──► chunker ──► embedder ──► vector store
                    (pages,    (by section,  (text →     (matrix on disk,
                     strip      ~900 chars,   vector)     cosine search)
                     footers)   overlap)

                QUESTION ANSWERING (POST /ask)
 question ──► embedder ──► vector store ──► top-k passages
                                                │
                              score < MIN_SCORE for all? ──yes──► "I couldn't find that
                                                │                  in the company documents."
                                                no                 (LLM is not called)
                                                ▼
                       LLM (Qwen via OpenRouter): answer ONLY from the
                       numbered passages and cite them as [1], [2] ...
                                                │
                                                ▼
                  answer + sources (document, page, section, snippet, score)
                  citations validated: invented [n] are ignored
```

## Technology stack

Python · FastAPI · NumPy · pypdf · Pydantic · httpx · Qwen (via OpenRouter) · Docker · pytest · GitHub Actions

## Quick start

```bash
cd enterprisedocs
docker compose up --build        # search works immediately, no keys needed
```

API at http://localhost:8000, interactive docs at http://localhost:8000/docs. The four sample documents are indexed on first start.

To enable **answer generation** (`POST /ask`), create a `.env`:

```bash
cp .env.example .env
```

```env
LLM_PROVIDER=openrouter
LLM_MODEL=<exact model ID from the OpenRouter model page>
OPENROUTER_API_KEY=<your key>
```

For **semantic embeddings** (recommended for real use, see "Evaluation" below):

```env
EMBEDDING_PROVIDER=openrouter
EMBEDDING_MODEL=qwen/qwen3-embedding-0.6b
```

Changing the embedding model rebuilds the index automatically on the next start. Then run `python -m scripts.evaluate` to check retrieval quality and tune `MIN_SCORE`.

**Never commit `.env`**; it is in `.gitignore`.

Without Docker:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API & Web UI

| Method | Path | Description |
|---|---|---|
| GET | `/` | Interactive Web UI (Ask AI, Search, Document Manager) |
| GET | `/health` | Liveness, plus document and chunk counts |
| POST | `/ask` | Answer a question with citations (needs an LLM) |
| POST | `/search` | Retrieval only, no LLM: shows exactly what the model would be given |
| GET | `/documents` | List indexed documents |
| POST | `/documents` | Upload a PDF, TXT or MD file and index it |
| DELETE | `/documents/{name}` | Delete an uploaded document |
| POST | `/ingest` | Re-scan the documents folder (`?force=true` re-indexes everything) |

Real output from `POST /search` with `{"query": "How many days of annual leave do employees get?", "top_k": 2}`:

```json
{
  "min_score": 0.1,
  "results": [
    {
      "id": 1,
      "document": "Leave_Policy.pdf",
      "page": 1,
      "section": "2. Annual Leave",
      "snippet": "Full-time employees are entitled to 21 working days of paid annual leave per leave year. Leave accrues at 1.75 days per month. ...",
      "score": 0.3705,
      "relevant": true
    },
    {
      "id": 2,
      "document": "Leave_Policy.pdf",
      "page": 1,
      "section": "3. Carrying Leave Forward",
      "snippet": "Employees may carry forward a maximum of five unused annual leave days into the next leave year. ...",
      "score": 0.3213,
      "relevant": true
    }
  ]
}
```

`POST /ask` returns `{"answer": "...", "grounded": true|false, "sources": [...]}`. `grounded` is true when the answer cites at least one retrieved passage; `sources` then holds only the cited passages, numbered to match the `[n]` markers in the answer. If the model does not cite anything, `grounded` is false and all retrieved passages are returned so a reader can check for themselves.

Real output from `POST /ask` with `{"question": "How many days of annual leave do employees get?"}`:

```json
{
  "answer": "Full-time employees are entitled to 21 working days of paid annual leave per leave year, which accrues at 1.75 days per month [1].",
  "grounded": true,
  "sources": [
    {
      "id": 1,
      "document": "Leave_Policy.pdf",
      "page": 1,
      "section": "2. Annual Leave",
      "snippet": "Full-time employees are entitled to 21 working days of paid annual leave per leave year. Leave accrues at 1.75 days per month. Leave must be approved in advance by the employee's line manager through the HR portal. ...",
      "score": 0.3705
    }
  ]
}
```

## Evaluation

`python -m scripts.evaluate` measures retrieval only (no LLM), so it is fast, free and repeatable. It uses 31 questions in `data/eval_questions.json`.

Results with the **offline default embedder** (top_k = 4, MIN_SCORE = 0.10):

| Question group | Right document ranked #1 | Right document in top 4 | Answer passage in top 4 |
|---|---|---|---|
| In-scope, using the documents' own words (18) | 18/18 | 18/18 | 18/18 |
| Paraphrased, different words (8) | 4/8 | 6/8 | 3/8 |

Off-topic questions rejected by the relevance threshold: **4/5**. (The miss was "What is the company's share price today?", which scored 0.16 because it shares generic words like "company" with the policies. In `/ask` it would reach the LLM, whose prompt says to refuse when the passages don't answer.)

**How to read these numbers honestly:**

- The default embedder is **lexical** (hashed words and word pairs). It matches wording, not meaning, which is why paraphrases such as "holiday days" for "annual leave" mostly fail. In `/ask` those questions get the safe "couldn't find that" reply rather than a guess.
- It exists so the project and its tests run with no key or download. For real use, switch to semantic embeddings and **re-run this script**; the paraphrase row is the one to watch. I have not measured a semantic embedder here, so I make no claim about its numbers.
- I wrote the questions and the documents, so the in-scope score is optimistic. The set is small, and `MIN_SCORE` (0.10) was chosen on it: low enough that no valid question is refused, accepting that a borderline off-topic one can slip through. Treat it as a starting point and re-tune with real employee questions.

## Design decisions

- **Heading-aware chunking.** A policy section is the natural unit of meaning. Splitting by section keeps each chunk self-contained and makes citations precise. Long sections are split on sentence boundaries with overlap so a fact at a boundary is not cut in half.
- **Embedder behind an interface.** The vector store records which embedder built the index. Change the model and the index is rebuilt instead of silently comparing incompatible vectors.
- **Exact search over a NumPy matrix.** Vectors are normalised, so cosine similarity is one matrix product. For a document library of this size it is exact and fast; the store class has a handful of methods and could be swapped for pgvector or Qdrant.
- **Refuse rather than guess.** Below the relevance threshold the LLM is never called. Above it, the prompt requires an exact refusal phrase when the passages don't contain the answer.
- **Citations are checked, not trusted.** Cited numbers outside the retrieved range are ignored, and an answer with no valid citation is flagged `grounded: false`.
- **Documents are untrusted input.** The prompt tells the model to ignore instructions found inside passages. This reduces prompt-injection risk; it does not eliminate it.
- **Errors are safe.** API errors never include upstream response bodies, stack traces or keys; those go to the log only.
- **Atomic persistence.** The index is written to a temp file and renamed, and an unreadable index is rebuilt rather than crashing startup.

## Known limits

- **No authentication.** Anyone who can reach the API can upload documents. Put it behind auth before exposing it.
- **Scanned PDFs are not supported** (no OCR). Tables are extracted as plain text and may lose structure.
- **Heading detection** expects numbered headings (`1.`, `2.1`) or Markdown `#` headings. Other layouts fall back to one section per document, which still works but cites less precisely.
- **Single process.** The index lives in memory per process; running several workers would give each its own copy.
- **One-shot questions.** No conversation memory, no re-ranking, no hybrid keyword + vector search.
- The sample documents are fictional and invented for this demo.

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

130 tests, no network or API key needed (they use the offline embedder and a scripted fake LLM). They cover the chunker (headings, pages, overlap, edge cases), loaders (including corrupt PDFs and footer removal), both embedders (including an HTTP-mocked API embedder and a check that vectors don't depend on Python's per-process hash seed), the vector store (search, replace, persistence, corrupt index), the service (incremental ingest, rebuild on embedder change, citations, the no-answer guard, upload safety) and the API. A retrieval-quality regression test runs the evaluation set.

I checked that the key safety tests can fail by deliberately breaking the relevance filter, the filename sanitiser and the citation validation in a scratch copy; each break was caught.

## Project structure

```text
enterprisedocs/
├── app/
│   ├── main.py              # app factory, startup ingest, safe error handlers
│   ├── config.py            # settings from environment
│   ├── api/                 # routes and request/response schemas
│   ├── ingestion/           # loaders (PDF/TXT/MD) and the chunker
│   ├── embeddings/          # Embedder interface, offline hashing, API embedder
│   ├── vectorstore/         # persistent NumPy store
│   ├── llm/                 # provider abstraction (OpenRouter / OpenAI)
│   └── rag/                 # service, prompts, evaluation
├── docs/                    # the four sample policy PDFs
├── data/eval_questions.json # retrieval evaluation set
├── scripts/                 # evaluate.py, make_sample_docs.py
├── tests/
├── Dockerfile, docker-compose.yml
└── .github/workflows/ci.yml
```

`python -m scripts.make_sample_docs` regenerates the sample PDFs (needs `reportlab`).

## Roadmap

- Real `/ask` transcripts and a semantic-embedding evaluation in this README
- pgvector backend for the vector store
- Hybrid keyword + vector search and a re-ranking step
- Authentication, and per-document access control
- A LangChain / LlamaIndex version of the pipeline for comparison
- Hand relevant questions to OpsAgent and vice versa
