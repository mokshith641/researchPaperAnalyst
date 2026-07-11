# System Architecture & Application Flow

This document details the system design, tech stack, and execution flows for the **Research Paper Analyst** application.

---

## 1. System Technology Stack

The application is structured as a decoupled Full-Stack single page application (SPA):

```
+--------------------------------------------------------------------+
|                         CLIENT FRONTEND                            |
|             Vite + React (v18) + TypeScript + Tailwind             |
|          State: React Query  |  Routing: React Router DOM          |
+------------------------------------+-------------------------------+
                                     | (REST HTTP / SSE)
                                     v
+--------------------------------------------------------------------+
|                         BACKEND SERVICE                            |
|                     FastAPI (Python REST App)                      |
|            Authentication: PyJWT  |  Embedding: FastEmbed          |
+------------------------------------+-------------------------------+
                                     |
              +----------------------+----------------------+
              | (SQLAlchemy Async)                          | (REST API)
              v                                             v
+-----------------------------+               +-----------------------------+
|      SQL DATABASE           |               |       VECTOR SEARCH         |
| PostgreSQL / SQLite (rpa.db)|               |        Qdrant Cloud         |
| Stores Users, metadata,     |               | Stores vector embeddings    |
| messages and text chunks    |               | of text chunks for queries  |
+-----------------------------+               +-----------------------------+
```

* **Frontend SPA**: Vite + React + TypeScript, Tailwind CSS, Lucide icons, React Hook Form, Axios client with JWT refresh interceptors, and React Router DOM.
* **Backend API**: FastAPI (Python) using asynchronous SQLAlchemy, Pydantic data schemas, PyPDF for text extraction, FastEmbed for vector generation, and PyJWT for user authentication.
* **SQL Store**: SQLite (`rpa.db`) for local developer fallback or PostgreSQL with pgvector for production. Stores credentials, conversation logs, and paper metadata.
* **Vector Store**: Qdrant Cloud handles high-dimensional similarity searches.
* **AI Model Providers**: FastEmbed offline text embeddings, and Groq (Llama 3.3-70b-versatile) or OpenAI (gpt-4o-mini) for retrieval-augmented answer generation.

---

## 2. Core Execution Flows

### A. Authentication & Session Flow

1. **User Signup**:
   * Client posts email, password, and name to `/api/auth/register`.
   * Backend hashes password using `bcrypt` and inserts record in SQLite/Postgres.
   * Backend returns JWT access token and refresh token.
2. **User Login**:
   * Client posts email/password credentials to `/api/auth/login`.
   * Backend verifies hash and returns tokens.
   * Client stores tokens in `localStorage`.
3. **Session Interceptor**:
   * Axios request interceptor attaches the JWT token to the `Authorization` header (`Bearer <token>`).
   * Axios response interceptor intercepts any `401 Unauthorized` errors. If a refresh token is present, it posts it to `/api/auth/refresh` to fetch a new access token, then retries the original failed request seamlessly.

---

### B. PDF Upload & Background Indexing Flow

This flow parses papers and populates both databases in a non-blocking background worker:

```
[User uploads PDF] 
       |
       v
1. API validates extension and file size (< 25MB)
       |
       v
2. Saves PDF to backend 'uploads/' storage path
       |
       v
3. Creates 'Paper' metadata & 'ProcessingJob' in SQL DB (Status: pending)
       |
       v
4. Spawns Background Task (run_process_pdf_background)
       |
  +----+----+
  |
  v
5. PDF Extraction: PyPDF extracts text page-by-page.
  |
  v
6. Chunking: Segments page texts into overlapping logical blocks (e.g. 500 characters).
  |
  v
7. Embeddings: Generates 384-dimensional vector embeddings for each chunk via FastEmbed.
  |
  v
8. SQL Insert: Inserts chunk content and metadata into 'document_chunks' table.
  |
  v
9. Vector DB Sync: Upserts chunk texts and metadata into Qdrant Cloud 'research_papers' collection.
  |
  v
10. Summarization: Extracts first/last pages, queries Groq/OpenAI to generate abstract, key points, and ELI5.
  |
  v
11. Update Status: Updates processing job and paper status to 'completed'.
```

---

### C. Semantic Vector Search Flow

Allows querying across the entire research paper library using natural concepts:

1. **Query Entry**: User enters a text query (e.g., *"What is the architecture of the parser?"*) in the dashboard search bar.
2. **Vectorization**: Backend generates a query embedding vector via `FastEmbed`.
3. **Similarity Search**: Queries Qdrant Cloud using the cosine similarity metric. Results are scoped by a payload filter ensuring `user_id == current_user.id`.
4. **Resolution**: Matches are resolved against the SQL database to fetch the associated document chunk and parent paper metadata.
5. **Presentation**: Results are displayed with similarity scores (e.g., *Match: 92%*) and the matching excerpt text.

---

## D. Retrieval-Augmented Generation (RAG) Chat Flow

Streams answers to user questions with clickable source citations:

```
[User types question in Chat space]
       |
       v
1. Client establishes connection to stream endpoint
   POST /api/chat/conversations/{id}/messages
       |
       v
2. Vector Retrieval: Queries Qdrant Cloud for chunks matching the question
   (optionally filtered by selected paper IDs)
       |
       v
3. Prompt Compilation: Packages context excerpts into the LLM system prompt:
   "Answer the question using ONLY the provided context:
    Excerpt 1 (Page X, Paper Y)..."
       |
       v
4. Chat Invocation: Calls LLM (Groq Llama 3.3 / OpenAI GPT-4o-mini)
       |
       +----> Streams citation source metadata to client
       |      (Paper IDs, titles, page numbers, excerpt texts)
       |
       +----> Streams text tokens to client using Server-Sent Events (SSE)
              ("token" events)
       |
       v
5. Client UI updates streaming text block in real-time.
   Upon completion, citation source buttons are rendered. 
   Clicking a citation opens the context excerpt drawer.
```
