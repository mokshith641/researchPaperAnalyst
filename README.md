# Research Paper Assistant 🚀

A production-ready, full-stack AI application that allows users to upload research papers (PDFs), index them into a PostgreSQL database using the `pgvector` extension, and chat with them using Retrieval-Augmented Generation (RAG).

## 🛠️ Tech Stack

### Frontend
- **Framework**: React 19 / Next.js 15 (App Router, TypeScript)
- **Styling**: Tailwind CSS (with Glassmorphic Theme)
- **Data Fetching & State**: Axios, TanStack React Query (v5)
- **Forms**: React Hook Form
- **Icons**: Lucide React

### Backend
- **Framework**: FastAPI (Python 3.10)
- **Database ORM**: SQLAlchemy 2.0 (Async)
- **Validation**: Pydantic v2
- **RAG & Embeddings**: LangChain, OpenAI, and Groq LLMs
- **PDF Extraction**: PyMuPDF (fitz)

### Database & Storage
- **Database**: PostgreSQL with `pgvector` extension
- **File Storage**: Local Disk Storage (with abstract interface ready for Supabase Storage buckets)

---

## 🏗️ Architecture & RAG Pipeline

```
  ┌─────────────────┐        Upload         ┌──────────────────┐
  │  PDF Documents  ├──────────────────────>│  PyMuPDF Parser  │
  └─────────────────┘                       └────────┬─────────┘
                                                     │
                                                     ▼ Clean & Split
  ┌─────────────────┐        Search         ┌────────┴─────────┐
  │   User Query    ├──────────────────────>│ Page-bound Chunks│
  └────────┬────────┘                       └────────┬─────────┘
           │                                         │
           ▼ Embed Query                             ▼ Embed Chunks
  ┌────────┴────────┐    Cosine Similarity  ┌────────┴─────────┐
  │ Vector Database │<─────────────────────>│ pgvector Storage │
  └────────┬────────┘                       └──────────────────┘
           │ Top-K Matches
           ▼
  ┌────────┴────────┐    Prompt & Stream    ┌──────────────────┐
  │ LLM Generator   ├──────────────────────>│   SSE Response   │
  │ (OpenAI / Groq) │                       │  (with citations)│
  └─────────────────┘                       └──────────────────┘
```

1. **Text Extraction**: PyMuPDF parses the PDF page-by-page. Text is cleaned of null bytes, normalized, and page bounds are recorded.
2. **Page-Bound Chunking**: Text is split into overlapping chunks (e.g. 1000 characters) page-by-page. This ensures each chunk represents exactly one page, providing 100% accurate page citations.
3. **Embeddings & pgvector**: Vector embeddings are generated for each chunk (local HuggingFace `all-MiniLM-L6-v2` or OpenAI `text-embedding-3-small`) and stored inside a PostgreSQL `vector` column.
4. **Retrieval (Semantic Search)**: When a query is made, it is embedded and matched using cosine distance (`DocumentChunk.embedding.cosine_distance`) to select the top-K chunks.
5. **Streaming Chat**: LangChain compiles the prompt containing the retrieved context block, conversation history logs, and the new query. The LLM response streams in real time via Server-Sent Events (SSE) along with source citation structures.

---

## 🗺️ Database Design

We implement normalized SQL tables with index optimizations and cascade deletes:
- **`users`**: Manages credentials, unique emails, and hashed passwords.
- **`papers`**: Stores document metadata (page count, title, processing state) and generated summaries.
- **`document_chunks`**: Stores raw text fragments and their matching high-dimensional vector embeddings.
- **`conversations`**: Tracks messaging threads.
- **`messages`**: Records chronological chat history and citation lists.
- **`processing_jobs`**: Logs background parsing job metrics and error traces.

---

## ⚙️ Environment Variables

Create a `.env` file in the root or set it inside `docker-compose.yml`:

```env
# Database configuration
DATABASE_URL=postgresql+asyncpg://rpa_user:rpa_password@db:5432/rpa_db

# Security settings
JWT_SECRET=super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Vector embedding configuration
# PROVIDER: 'huggingface' (runs free locally) or 'openai'
EMBEDDING_PROVIDER=huggingface
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
OPENAI_API_KEY=your-openai-api-key-here

# LLM Generator configuration
# PROVIDER: 'groq' or 'openai'
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL_NAME=llama-3.1-70b-versatile
OPENAI_MODEL_NAME=gpt-4o-mini
```

---

## 🚀 Quick Start (Docker Compose)

The easiest way to run the entire stack (PostgreSQL + pgvector, FastAPI, and Next.js) is using Docker Compose:

1. Clone this repository to your computer.
2. Configure your API keys in the `docker-compose.yml` (e.g. `GROQ_API_KEY` or `OPENAI_API_KEY`).
3. Build and launch:
   ```bash
   docker-compose up --build
   ```
4. Access the web interface at `http://localhost:3000`. The API docs are available at `http://localhost:8000/docs`.

---

## 🛠️ Manual Development Setup

If you prefer to run services manually for local debugging:

### 1. Database
Make sure you have a PostgreSQL server running with the `pgvector` extension installed. Run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. Backend Setup
1. Move to the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv env
   .\env\Scripts\activate  # On Windows
   source env/bin/activate # On Unix/macOS
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

### 3. Frontend Setup
1. Move to the frontend folder:
   ```bash
   cd ../frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install --legacy-peer-deps
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. Open `http://localhost:3000` in your browser.

---

## 🧪 Running Tests

The backend includes a unit and integration test suite using `pytest`. To run tests:

```bash
cd backend
.\env\Scripts\pytest
```

---

## ☁️ Deployment

- **Database**: Deploy a managed PostgreSQL instance using **Supabase** or **Neon**, and enable the `pgvector` extension.
- **Backend API**: Deploy the `/backend` folder to **Render**, **Railway**, or **Fly.io** using the provided `Dockerfile`. Set the appropriate environment variables.
- **Frontend App**: Deploy the `/frontend` folder to **Vercel** or **Netlify**. Set the `NEXT_PUBLIC_API_URL` variable pointing to your deployed Backend API.

