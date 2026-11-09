# ProofLine — Antigravity Agent Handover Document

**Subsystem:** Knowledge Ingestion, Chunking, Embedding & RAG Retrieval  
**Working Branch:** `dhruv/day1-data-contract`  
**Latest Commit ID:** `acd4096` (`feat(rag): implement RAG subsystem foundation, stages 1-3, and real estate dataset`)  
**Remote Repository:** `https://github.com/KrishV18/ProofLine.git`  
**PR Status:** Pushed to `origin/dhruv/day1-data-contract`; ready for PR creation/review into `origin/main`.  
**Date:** November 2026  

---

## 1. Project Purpose & Current Architecture

**ProofLine** is a pre-publication brand-governance and content assurance platform designed to prevent deceptive, contradictory, or non-compliant claims in marketing communications before they are published.

### Architecture Overview
- **Backend:** FastAPI application (`backend/app/`) with SQLAlchemy models (`backend/app/models/`) and Pydantic schemas (`backend/app/schemas/`).
- **Frontend:** Next.js application (`frontend/src/`) with App Router pages.
- **RAG Subsystem:** Located in `backend/app/services/rag/`, responsible for grounding the review engine in verifiable organizational guidelines, facts, terms, pricing, amenities, and statutory approvals.
- **Demonstration Dataset:** Fictional real estate marketing agency **Brick & Beyond** representing developer client **Asteria Developers** and residential project **Asteria Greens** (Sector 78, Gurugram, RERA Reg: `DEMO-HRERA-GGM-2026-0042`).

---

## 2. Agent Responsibility: RAG Subsystem

This workspace role encompasses:
1. Discovering, loading, validating, and normalizing structured knowledge assets.
2. Chunking long-form policies, brochures, and facts while maintaining hierarchical header context and source references.
3. Generating dense numerical vector embeddings via the official OpenAI API (`text-embedding-3-small`, 1536 dimensions).
4. Providing tenant-isolated similarity and keyword retrieval for draft claims.
5. Evaluating retrieval quality against curated benchmark datasets.

---

## 3. Completed Work: Stages 1–3

### Stage 1: Knowledge Loading, Validation & Normalisation
- **File:** `backend/app/services/rag/ingestion.py`
- **Capabilities:**
  - Robust directory discovery (`get_default_knowledge_dir`, `discover_knowledge_files`) using file-relative traversal and `PROOFLINE_KNOWLEDGE_DIR` overrides.
  - Safe JSON reading with syntax error handling, line/column tracking, and exclusion of test/draft folders.
  - Strict validation of IDs, source versions, approval status, ISO 8601 dates, and duplicate ID detection across files.
  - Normalisation of all 32 knowledge records into `NormalizedKnowledgeRecord` with category-tailored `searchable_text`.
- **Knowledge Sources Ingested (32 records total):**
  - `sample-data/knowledge/agency/brand-guidelines.json` (8 records)
  - `sample-data/knowledge/agency/terminology.json` (5 records)
  - `sample-data/knowledge/clients/asteria-developers/projects/asteria-greens/project-facts.json` (7 records)
  - `sample-data/knowledge/clients/asteria-developers/projects/asteria-greens/amenities.json` (6 records)
  - `sample-data/knowledge/clients/asteria-developers/projects/asteria-greens/pricing.json` (3 records)
  - `sample-data/knowledge/clients/asteria-developers/projects/asteria-greens/approvals.json` (3 records)

### Stage 2: Chunking & Token Management
- **File:** `backend/app/services/rag/chunking.py`
- **Capabilities:**
  - `DocumentChunk` model with `chunk_id`, `content`, `source_ref`, `source_version`, `header_context`, and character offsets (`char_start`, `char_end`).
  - Recursive text splitting (`split_text_with_overlap`) along natural paragraph and sentence delimiters.
  - Header-aware Markdown chunking (`chunk_markdown`) that preserves hierarchical header paths (e.g. `[Manual > 3. Financial Rules > 3.1 Prohibited Returns]`).
  - Single and batch conversion of `NormalizedKnowledgeRecord` into `DocumentChunk`.
  - Ingestion of sample document files (`sample-data/documents/*.md`).

### Stage 3: OpenAI Embedding Generation
- **File:** `backend/app/services/rag/embeddings.py`
- **Configuration:** Provider = OpenAI, Model = `text-embedding-3-small`, Dimensions = `1536`, Auth = `OPENAI_API_KEY`.
- **Capabilities:**
  - `get_embedding_client()`: Lazy credential initialization with fallback HTTP client using `httpx` (eliminating unresolved import errors if `openai` package is absent).
  - `generate_embedding(text)`: Single-text vectorization.
  - `generate_embeddings(texts, batch_size=64)`: Batch vectorization preserving 1-to-1 input ordering via OpenAI `.index` metadata.
  - `generate_query_embedding(query)`: Query vectorization using identical model and dimensions for retrieval grounding.
  - `embed_chunks(chunks)`: Pairs `DocumentChunk` with its vector to produce `EmbeddedChunk`.
  - Strict validation: Rejects non-finite values (`NaN`, `Inf`), asserts vector length is 1536, and disallows silent fake/zero-vector fallback on failures.

---

## 4. Test Suite & Validation Status

All test suites run in the virtual environment (`backend/.venv/Scripts/python.exe -m pytest`):

| Test Suite File | Passed | Skipped | Status | Details |
| :--- | :---: | :---: | :---: | :--- |
| `backend/tests/test_finding_schema.py` | 3 | 0 | **PASSED** | Core `FindingBase` and validator tests |
| `backend/tests/test_rag_ingestion.py` | 10 | 0 | **PASSED** | File discovery, counts, validation, dates, duplicate detection |
| `backend/tests/test_rag_chunking.py` | 10 | 0 | **PASSED** | Text splitting, markdown header trees, chunk offsets |
| `backend/tests/test_rag_embeddings.py` | 13 | 1 | **PASSED** | Dimensions, ordering, batching, metadata, failure handling (1 live test skipped) |
| **Total** | **36** | **1** | **ALL GREEN** | Execution time: ~0.72s |

*Note: The live API smoke test in `test_rag_embeddings.py` is safely skipped by default to prevent unintended credit consumption.*

---

## 5. Pending Stage 4: Retrieval Engine (`retrieval.py`)

**File:** `backend/app/services/rag/retrieval.py` (currently provisional scaffold).

### Objective & Requirements
1. **In-Memory & Vector Similarity Search:** Compute cosine similarity between query embedding and knowledge chunk embeddings.
2. **Tenant Isolation:** Enforce mandatory filtering by `organisation_id` (and optional `client_id` / `project_id`) on every query.
3. **Thresholding & Top-K:** Support `top_k: int = 5` and `min_score: float = 0.5` to suppress irrelevant noise.
4. **Output Structure:** Return `list[RetrievedEvidence]`:
   ```python
   @dataclass
   class RetrievedEvidence:
       chunk_id: str
       source_ref: str          # Matches FindingBase.source_ref
       source_version: int      # Matches FindingBase.source_version
       content: str             # Verifiable text excerpt
       similarity_score: float  # Cosine similarity (0.0 to 1.0)
       metadata: dict[str, Any] # Source category, owner, dates
   ```

---

## 6. Pending Stage 5: Evaluation & Quality Benchmarking (`evaluation.py`)

**File:** `backend/app/services/rag/evaluation.py` (currently provisional scaffold).

### Objective & Requirements
1. **Benchmark Datasets:**
   - Ingest `sample-data/evaluation/evaluation-dataset.json` (12 drafts: D001 through D012).
   - Compare against `sample-data/evaluation/expected-findings.json` (26 ground-truth findings).
2. **Information Retrieval (IR) Metrics:**
   - **Hit Rate @ K:** Frequency with which the expected `source_id` is present in the top-K retrieved results.
   - **Mean Reciprocal Rank (MRR @ K):** Measure of the rank position of the first relevant result.
   - **Context Precision & Recall:** Proportion of retrieved evidence relevant to flagged draft claims.
3. **Execution Script:** Add a test runner or CLI script to report quantitative retrieval metrics across the 12 scenarios.

---

## 7. Cross-Team Integration Dependencies

```
                      +------------------------------------------+
                      |         ProofLine Review Engine          |
                      +------------------------------------------+
                                     |             |
                1. Extract Claims    |             | 3. Provide Evidence
                                     v             v
       +-------------------------------+         +--------------------------------+
       |   Kalash (LLM Subsystem)      |         |   RAG Subsystem (Dhruv)        |
       |   - Claim extraction          |         |   - Ingestion & Chunking       |
       |   - Review prompt grounding   |<--------|   - OpenAI Embeddings (1536-d) |
       |   - Finding generation        |         |   - Vector & Hybrid Retrieval  |
       +-------------------------------+         +--------------------------------+
                                                           |
                                                           | 2. Persist / Query Chunks
                                                           v
                                         +--------------------------------+
                                         |   Krish (Database Subsystem)   |
                                         |   - PostgreSQL + pgvector      |
                                         |   - Tenant-isolated SQL queries|
                                         |   - Alembic migration tables   |
                                         +--------------------------------+
```

### 1. Integration with Krish (Database & Storage)
- **Vector Persistence:** Krish is implementing PostgreSQL tables and Alembic migrations. The `EmbeddedChunk` schema (`chunk_id`, `source_ref`, `source_version`, `organisation_id`, `embedding`) is designed for 1-to-1 persistence in a `knowledge_chunks` table with a `pgvector` column of dimension 1536.
- **Repository Interface:** Once Krish's database layer is ready, `retrieval.py` will query SQL/pgvector sessions instead of in-memory collections.

### 2. Integration with Kalash (LLM Claim Extraction & Review)
- **Claim Grounding:** Kalash extracts claims from draft text (e.g. *"Our 2 BHK has 1,250 sq. ft."*).
- **Evidence Contract:** The RAG retrieval engine embeds the claim via `generate_query_embedding()` and returns `RetrievedEvidence` matching `source_ref` (`AG-FACT-AREA-2BHK-03`).
- **Finding Generation:** Kalash's LLM prompt compares claim vs. evidence, generates a `Finding` citing `source_ref`, and marks `severity: "blocker"`.

---

## 8. Key Configuration, Schemas & Environment Variables

### Environment Variables (`backend/app/config.py` & `.env.example`)
| Variable | Default Value | Purpose |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | `""` | Dedicated OpenAI authentication key for embeddings |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Standard embedding model name |
| `OPENAI_EMBEDDING_DIMENSIONS` | `1536` | Output vector dimension |
| `PROOFLINE_KNOWLEDGE_DIR` | `None` (auto-detected) | Optional override for knowledge directory root |
| `LLM_API_KEY` / `LLM_MODEL` | `""` / `gemini-pro` | Kalash's LLM settings (kept completely separate) |

### Key Schemas & Data Classes
- `NormalizedKnowledgeRecord` (`ingestion.py`): Cleaned internal representation of approved knowledge.
- `DocumentChunk` (`chunking.py`): Sliced text passages with offsets and header hierarchy.
- `EmbeddedChunk` (`embeddings.py`): Chunk paired with its 1536-dimensional float vector.
- `RetrievedEvidence` (`retrieval.py`): Standard output passed into review prompt templates.

---

## 9. Known Limitations & Immediate Next Steps

### Limitations
1. **In-Memory Operation:** Embeddings and chunk retrieval currently operate in-memory pending Krish's PostgreSQL `pgvector` table migration.
2. **Binary Document Parsing:** `document_parser.py` is scaffolded; markdown documents are parsed directly, but binary `.pdf` / `.docx` pipeline integration remains pending.
3. **No External Network in Standard Sandbox:** Offline unit tests use mocked responses. Live API calls require `OPENAI_API_KEY` and bypass sandbox permissions.

### Immediate Next Steps for Next Agent
1. **Implement Stage 4 (`retrieval.py`):**
   - Implement in-memory vector index / cosine similarity function.
   - Implement `retrieve_relevant_context(query, organisation_id, top_k, min_score)`.
   - Add unit tests in `backend/tests/test_rag_retrieval.py`.
2. **Implement Stage 5 (`evaluation.py`):**
   - Wire up `evaluate_retrieval_pipeline()` to benchmark against `sample-data/evaluation/evaluation-dataset.json`.
   - Validate that clean control `D001` retrieves approved facts, while `D002`–`D012` correctly surface the contradicting or violated `source_id`s.
3. **Collaborate on PR Merge:** Coordinate with Krish and Kalash to review and merge branch `dhruv/day1-data-contract` into `main`.

