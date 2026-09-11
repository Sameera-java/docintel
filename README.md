\# Document Intelligence Platform



An end-to-end AI-powered platform that accepts financial documents (Invoice,

Balance Sheet, Profit \& Loss, Cash Flow Statement) as PDF/JPG/PNG, validates

them, extracts every visible field and table using OCR + an LLM, runs

financial reconciliation checks, stores results, and serves everything

through a REST API and an HTML dashboard.



Built as a 3-day AI Engineer Internship technical case study.



\## 1. Solution Overview \& Architecture



Frontend (HTML/CSS/JS)

↓

FastAPI Backend (single service, serves both API + frontend)

↓

Stage 1: Document Validation — file type, integrity, page count

Stage 2: Text Extraction / OCR — PyMuPDF (native PDF) + Gemini vision (scanned/image)

Stage 3: AI Field \& Table Extraction — Google Gemini, structured JSON output

Stage 4: Financial Validation — rule-based reconciliation per document type

↓

Persistence — SQLite via SQLAlchemy

↓

Structured JSON response + dashboard





See `docs/architecture.png` for the visual diagram.



The frontend and backend are deployed as \*\*one FastAPI service\*\* (Jinja2

templates + static files served alongside the REST API) rather than two

separate deployments — this satisfies the spec's requirement for an

HTML/CSS frontend connected to the deployed Python API, while keeping the

deployment surface minimal for a 3-day project.



\## 2. Technology Stack \& Reasoning



| Layer | Choice | Why |

|---|---|---|

| API framework | FastAPI | Async, automatic OpenAPI/Swagger docs, strong typing via Pydantic |

| OCR (scanned docs) | Gemini vision (multimodal) | No system-level install required (works identically on any host, including free-tier PaaS like Render, which block installing OS binaries); reuses the same API key already needed for extraction |

| Native PDF text | PyMuPDF (`fitz`) | Fast, accurate text extraction for non-scanned PDFs; also used for page counting/validation |

| LLM extraction | Google Gemini (`gemini-3.6-flash`) | Free tier, strong structured-JSON output, handles financial-document nuance well |

| Database | SQLite via SQLAlchemy | Zero-config, file-based, swappable for Postgres/MySQL by changing `DATABASE\_URL` only |

| Frontend | Plain HTML/CSS/JS (Jinja2 templates) | Matches spec exactly (no separate frontend stack required); minimal complexity |



\## 3. Local Setup Instructions



Prerequisites: Python 3.11+. No system-level OCR install required.



```bash

cd backend

pip install -r requirements.txt

cp ../.env.example .env        # then fill in GEMINI\_API\_KEY

uvicorn app.main:app --reload --port 8000

```



Open http://127.0.0.1:8000 for the dashboard, http://127.0.0.1:8000/docs for Swagger.



Run tests:

```bash

cd backend

pytest tests/ -v

```



\## 4. Environment Variables (`.env.example`)



| Variable | Purpose |

|---|---|

| `GEMINI\_API\_KEY` | Your free Gemini API key from https://aistudio.google.com/apikey |

| `GEMINI\_MODEL` | Defaults to `gemini-3.6-flash` |

| `DATABASE\_URL` | Defaults to local SQLite; set to a Postgres/MySQL URL in production |

| `MAX\_PAGES` | Document page limit (default 3, per spec) |

| `MAX\_FILE\_SIZE\_MB` | Upload size limit (default 15 MB) |

| `VALIDATION\_TOLERANCE` | Allowed numeric variance for financial checks (default ±1.0) |

| `LOG\_LEVEL` | Logging verbosity (default INFO) |



No real secrets are committed — see `.env.example`.



\## 5. Deployed URLs



\- Frontend: https://docintel-jpk2.onrender.com/

\- Backend API base: https://docintel-jpk2.onrender.com/api/v1

\- Swagger/OpenAPI docs: https://docintel-jpk2.onrender.com/docs

\- Public GitHub repository: https://github.com/Sameera-java/docintel



Note: the deployed instance runs on Render's free tier, which spins down

after inactivity — the first request after idle time may take 30-60 seconds

to respond while the instance wakes up. Subsequent requests are fast.



\## 6. API Reference



| Method | Endpoint | Purpose |

|---|---|---|

| POST | `/api/v1/documents/process` | Upload and process a document |

| GET | `/api/v1/documents/{document\_name}` | Latest structured result by name |

| GET | `/api/v1/documents` | List all processed documents (dashboard) |

| GET | `/api/v1/health` | Health check |



\*\*POST /api/v1/documents/process\*\* (multipart/form-data)



file: <document.pdf>

document\_type: invoice | balance\_sheet | profit\_and\_loss | cash\_flow\_statement





Example (curl):

```bash

curl -X POST http://localhost:8000/api/v1/documents/process \\

&#x20; -F "file=@sample\_invoice.pdf" \\

&#x20; -F "document\_type=invoice"

```



\*\*GET /api/v1/documents/{document\_name}\*\*

```bash

curl http://localhost:8000/api/v1/documents/sample\_invoice.pdf

```



\*\*GET /api/v1/documents\*\*

```bash

curl http://localhost:8000/api/v1/documents

```



Sample responses for all of the above are in `sample\_outputs/`.

\## 7. OCR / LLM Services Used



\- \*\*Text extraction\*\*: PyMuPDF for native PDF text; falls back to sending the

&#x20; page image to Gemini's vision capability for transcription when a page has

&#x20; little/no extractable native text (i.e. it's a scanned image). Images

&#x20; (JPG/PNG) always go through Gemini vision. Using the same LLM for OCR and

&#x20; extraction (rather than a separate local OCR engine) avoids any

&#x20; system-level install, so behavior is identical on a laptop and on a

&#x20; hosting platform.

\- \*\*LLM\*\*: Google Gemini (`gemini-3.6-flash`), free tier, called once per

&#x20; document with the full extracted text and a document-type-specific prompt

&#x20; that enforces: null for missing values (never invent), evidence/source

&#x20; text per field, and per-period extraction for multi-year statements.



\## 8. Confidence Scoring



Not implemented (optional per spec). The extraction prompt does ask the LLM

for source-text evidence and page numbers per field, which is used as the

grounding/traceability mechanism instead.



\## 9. Financial Validation Rules \& Tolerance



| Document | Checks |

|---|---|

| Invoice | `subtotal + tax − discount ≈ total\_amount`; `sum(line\_items.amount) ≈ subtotal` (if line items present) |

| Balance Sheet | `total\_liabilities + total\_equity ≈ total\_assets` |

| Profit \& Loss | `revenue − cost\_of\_sales ≈ gross\_profit`; `gross\_profit − operating\_expenses ≈ operating\_profit`; `operating\_profit − tax ≈ net\_profit` |

| Cash Flow Statement | `operating + investing + financing ≈ net\_change\_in\_cash`; `opening\_cash + net\_change\_in\_cash ≈ closing\_cash` |



Numeric tolerance: \*\*±1.0\*\* (currency unit), configurable via

`VALIDATION\_TOLERANCE`, to absorb rounding differences in source documents.



If any input field a check needs is `null`/missing, that check returns

`NOT\_APPLICABLE` rather than assuming a value — never a false PASS or FAIL.



\## 10. Database / Persistence



SQLite (file `docintel.db`), accessed exclusively through

`app/repositories/document\_repository.py` (SQLAlchemy ORM). Each processed

document is stored as a row with the full structured JSON result in a JSON

column, plus indexed columns (`document\_name`, `created\_at`) for fast

dashboard listing and "latest result by name" lookups. Swapping to

Postgres/MySQL requires only changing `DATABASE\_URL`.



\## 11. Known Limitations



\- Gemini's free tier caps at 20 requests/day per model. Since OCR (for scanned

&#x20; documents) and extraction each make one call, a handful of scanned documents

&#x20; can exhaust the daily quota. A paid tier removes this cap for production use.

\- Multi-period (multi-year) financial statements: the LLM is instructed to

&#x20; extract each period separately, but the current financial-validation layer

&#x20; runs checks against a single flat set of fields rather than looping over

&#x20; every period automatically — for a 10-year consolidated statement, checks

&#x20; run reliably against the primary/most recent period.

\- No confidence scoring implemented (optional per spec).

\- No automated document-type classification (out of scope per spec — type is

&#x20; selected by the user in the frontend).

\- OCR quality on low-resolution scans depends on Gemini's vision

&#x20; capability; no image pre-processing (deskew, binarization) is applied yet.

\- Single free-tier LLM call per document with no retry/backoff on transient

&#x20; Gemini rate-limit errors beyond a single graceful failure.



\## 12. What I'd Change for Production



\- Loop financial validation checks over every extracted period/year, not just one.

\- Add image pre-processing before OCR (deskew, contrast normalization) to

&#x20; improve extraction accuracy on low-quality scans.

\- Add retry/backoff and a fallback OCR/LLM provider for resilience.

\- Move to Postgres, add DB migrations (Alembic), and add authentication on

&#x20; the API and dashboard.

\- Add a real confidence-scoring mechanism (e.g. cross-checking OCR text

&#x20; against LLM-extracted values).

\- Async/background job processing (task queue) instead of synchronous

&#x20; request handling, for larger documents or higher throughput.



\## 13. AI Coding Assistants Used



Claude (Anthropic) was used throughout: architecture design, backend service

implementation (validation, OCR orchestration, extraction prompting,

financial validation logic, API routes), frontend (dashboard + result page),

test suite, and this documentation. All logic was reviewed and tested

(`pytest tests/ -v`, 14/14 passing) against synthetic and real sample

documents before submission.

