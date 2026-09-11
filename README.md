# Document Intelligence Platform

An end-to-end AI-powered platform that accepts financial documents (Invoice,
Balance Sheet, Profit & Loss, Cash Flow Statement) as PDF/JPG/PNG, validates
them, extracts every visible field and table using OCR + an LLM, runs
financial reconciliation checks, stores results, and serves everything
through a REST API and an HTML dashboard.

Built as a 3-day AI Engineer Internship technical case study.

## 1. Solution Overview & Architecture

```
Frontend (HTML/CSS/JS)
      ↓
FastAPI Backend (single service, serves both API + frontend)
      ↓
Stage 1: Document Validation      — file type, integrity, page count
Stage 2: Text Extraction / OCR    — PyMuPDF (native PDF) + Tesseract (scanned/image)
Stage 3: AI Field & Table Extraction — Google Gemini, structured JSON output
Stage 4: Financial Validation     — rule-based reconciliation per document type
      ↓
Persistence — SQLite via SQLAlchemy
      ↓
Structured JSON response + dashboard
```

See `docs/architecture.png` for the visual diagram.

The frontend and backend are deployed as **one FastAPI service** (Jinja2
templates + static files served alongside the REST API) rather than two
separate deployments — this satisfies the spec's requirement for an
HTML/CSS frontend connected to the deployed Python API, while keeping the
deployment surface minimal for a 3-day project.

## 2. Technology Stack & Reasoning

| Layer | Choice | Why |
|---|---|---|
| API framework | FastAPI | Async, automatic OpenAPI/Swagger docs, strong typing via Pydantic |
| OCR (scanned docs) | Tesseract (`pytesseract`) | Free, local, no API key, no rate limits — reliable under a tight deadline |
| Native PDF text | PyMuPDF (`fitz`) | Fast, accurate text extraction for non-scanned PDFs; also used for page counting/validation |
| LLM extraction | Google Gemini (`gemini-2.0-flash`) | Free tier, strong structured-JSON output, handles financial-document nuance well |
| Database | SQLite via SQLAlchemy | Zero-config, file-based, swappable for Postgres/MySQL by changing `DATABASE_URL` only |
| Frontend | Plain HTML/CSS/JS (Jinja2 templates) | Matches spec exactly (no separate frontend stack required); minimal complexity |

## 3. Local Setup Instructions

Prerequisites: Python 3.11+, [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed and on your PATH.

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env        # then fill in GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000 for the dashboard, http://127.0.0.1:8000/docs for Swagger.

Run tests:
```bash
cd backend
pytest tests/ -v
```

## 4. Environment Variables (`.env.example`)

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Your free Gemini API key from https://aistudio.google.com/apikey |
| `GEMINI_MODEL` | Defaults to `gemini-2.0-flash` |
| `DATABASE_URL` | Defaults to local SQLite; set to a Postgres/MySQL URL in production |
| `MAX_PAGES` | Document page limit (default 3, per spec) |
| `MAX_FILE_SIZE_MB` | Upload size limit (default 15 MB) |
| `VALIDATION_TOLERANCE` | Allowed numeric variance for financial checks (default ±1.0) |
| `LOG_LEVEL` | Logging verbosity (default INFO) |

No real secrets are committed — see `.env.example`.

## 5. Deployed URLs

- Frontend: `<fill in after deploying>`
- Backend API base: `<fill in after deploying>`
- Swagger/OpenAPI docs: `<deployed URL>/docs`
- Public GitHub repository: `<fill in>`

## 6. API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/documents/process` | Upload and process a document |
| GET | `/api/v1/documents/{document_name}` | Latest structured result by name |
| GET | `/api/v1/documents` | List all processed documents (dashboard) |
| GET | `/api/v1/health` | Health check |

**POST /api/v1/documents/process** (multipart/form-data)
```
file: <document.pdf>
document_type: invoice | balance_sheet | profit_and_loss | cash_flow_statement
```

Example (curl):
```bash
curl -X POST http://localhost:8000/api/v1/documents/process \
  -F "file=@sample_invoice.pdf" \
  -F "document_type=invoice"
```

**GET /api/v1/documents/{document_name}**
```bash
curl http://localhost:8000/api/v1/documents/sample_invoice.pdf
```

**GET /api/v1/documents**
```bash
curl http://localhost:8000/api/v1/documents
```

Sample responses for all of the above are in `sample_outputs/`.

## 7. OCR / LLM Services Used

- **Text extraction**: PyMuPDF for native PDF text; falls back to Tesseract OCR
  automatically per-page when a page has little/no extractable native text
  (i.e. it's a scanned image). Images (JPG/PNG) always go through Tesseract.
- **LLM**: Google Gemini (`gemini-2.0-flash`), free tier, called once per
  document with the full extracted text and a document-type-specific prompt
  that enforces: null for missing values (never invent), evidence/source
  text per field, and per-period extraction for multi-year statements.

## 8. Confidence Scoring

Not implemented (optional per spec). The extraction prompt does ask the LLM
for source-text evidence and page numbers per field, which is used as the
grounding/traceability mechanism instead.

## 9. Financial Validation Rules & Tolerance

| Document | Checks |
|---|---|
| Invoice | `subtotal + tax − discount ≈ total_amount`; `sum(line_items.amount) ≈ subtotal` (if line items present) |
| Balance Sheet | `total_liabilities + total_equity ≈ total_assets` |
| Profit & Loss | `revenue − cost_of_sales ≈ gross_profit`; `gross_profit − operating_expenses ≈ operating_profit`; `operating_profit − tax ≈ net_profit` |
| Cash Flow Statement | `operating + investing + financing ≈ net_change_in_cash`; `opening_cash + net_change_in_cash ≈ closing_cash` |

Numeric tolerance: **±1.0** (currency unit), configurable via
`VALIDATION_TOLERANCE`, to absorb rounding differences in source documents.

If any input field a check needs is `null`/missing, that check returns
`NOT_APPLICABLE` rather than assuming a value — never a false PASS or FAIL.

## 10. Database / Persistence

SQLite (file `docintel.db`), accessed exclusively through
`app/repositories/document_repository.py` (SQLAlchemy ORM). Each processed
document is stored as a row with the full structured JSON result in a JSON
column, plus indexed columns (`document_name`, `created_at`) for fast
dashboard listing and "latest result by name" lookups. Swapping to
Postgres/MySQL requires only changing `DATABASE_URL`.

## 11. Known Limitations

- Multi-period (multi-year) financial statements: the LLM is instructed to
  extract each period separately, but the current financial-validation layer
  runs checks against a single flat set of fields rather than looping over
  every period automatically — for a 10-year consolidated statement, checks
  run reliably against the primary/most recent period.
- No confidence scoring implemented (optional per spec).
- No automated document-type classification (out of scope per spec — type is
  selected by the user in the frontend).
- OCR quality on low-resolution scans depends entirely on Tesseract's default
  settings; no image pre-processing (deskew, binarization) is applied yet.
- Single free-tier LLM call per document with no retry/backoff on transient
  Gemini rate-limit errors beyond a single graceful failure.

## 12. What I'd Change for Production

- Loop financial validation checks over every extracted period/year, not just one.
- Add image pre-processing before OCR (deskew, contrast normalization) to
  improve extraction accuracy on low-quality scans.
- Add retry/backoff and a fallback OCR/LLM provider for resilience.
- Move to Postgres, add DB migrations (Alembic), and add authentication on
  the API and dashboard.
- Add a real confidence-scoring mechanism (e.g. cross-checking OCR text
  against LLM-extracted values).
- Async/background job processing (task queue) instead of synchronous
  request handling, for larger documents or higher throughput.

## 13. AI Coding Assistants Used

Claude (Anthropic) was used throughout: architecture design, backend service
implementation (validation, OCR orchestration, extraction prompting,
financial validation logic, API routes), frontend (dashboard + result page),
test suite, and this documentation. All logic was reviewed and tested
(`pytest tests/ -v`, 14/14 passing) against synthetic and real sample
documents before submission.
