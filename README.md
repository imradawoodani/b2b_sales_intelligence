# B2B Sales Intelligence Platform

This repository implements a proof-of-concept sales intelligence platform for a roofing distributor. It is designed to load contractor leads, enrich them with AI summaries and decision signals, compute a priority score, and present the results in a browser UI.

## Architecture Overview

### Backend
- `backend/main.py` — FastAPI app with routes for:
  - `/contractors` — list contractors
  - `/contractors/{id}` — contractor details
  - `/pipeline/run` — trigger the seed-driven pipeline
  - `/pipeline/status` — check pipeline progress
  - `/contractors/{id}/ask` — question endpoint for AI Q&A
- `backend/database.py` — SQLAlchemy setup, using `DATABASE_URL` or local SQLite default
- `backend/models.py` — ORM models for `Contractor` and `PipelineRun`
- `backend/schemas.py` — Pydantic response models used by FastAPI
- `backend/scraper.py` — loads seed contractor leads from `seed_data.json`
- `backend/pipeline.py` — pipeline orchestration, enrichment, scoring, and OpenAI integration
- `backend/seed_data.py` — loads static GAF seed data from JSON

### Frontend
- `frontend/src/App.jsx` — app shell, pipeline trigger, data fetch and view toggle
- `frontend/src/components/ContractorList.jsx` — card-based lead list
- `frontend/src/components/ContractorTable.jsx` — table view of leads
- `frontend/src/components/SidePanel.jsx` — lead detail panel with AI brief and Perplexity signal
- `frontend/src/api.js` — REST client for backend endpoints

### Data Flow
1. `frontend` requests contractor list and pipeline status from the backend
2. `/pipeline/run` triggers the backend pipeline in a background task
3. `backend/scraper.py` loads contractors from `seed_data.json`
4. Contractors are persisted in the database via SQLAlchemy
5. `pipeline.py` enriches each contractor:
   - normalizes contractor tier
   - estimates revenue and employee count
   - computes a deterministic `base_score`
   - calls OpenAI for `brief` and `talking_points`
   - calls OpenAI again for a Perplexity-style decision score and reasoning
   - combines deterministic score and OpenAI decision score into final `priority_score`
6. Frontend displays contractors, score, tier, estimated revenue, distance, brief, and Perplexity insights

## Key Features

- Seed-driven contractor load from static GAF sample data
- Simple pipeline orchestration with background execution and progress status
- Deterministic score math for reliability
- OpenAI-powered sales brief generation
- OpenAI-powered Perplexity-style decision signal to influence priority
- React + Vite frontend with list/table views and detail panel

## Scoring Logic

The pipeline computes a `base_score` using:
- `tier` weight (`master_elite`, `certified_plus`, `certified`, `none`)
- review activity and average rating
- estimated business size / revenue
- accessibility via distance and contact availability

Then it blends that score with the AI decision signal:
- `final_score = round(base_score * 0.65 + perplexity_score * 0.35)`

This keeps the score grounded in deterministic business rules while still allowing AI reasoning to adjust priorities.

## Setup

### Backend

1. Create and activate a virtual environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   ```
2. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in `backend/` with:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   PERPLEXITY_API_KEY=your_perplexity_api_key
   PERPLEXITY_API_URL=https://api.perplexity.ai/v1/answers
   DATABASE_URL=sqlite:///./leads.db
   ```
4. Start the backend:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend

1. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Run the frontend dev server:
   ```bash
   npm run dev
   ```
3. Open the app in the browser at the provided Vite URL.

### Running the pipeline

- Trigger enrichment:
  ```bash
  curl -X POST http://localhost:8000/pipeline/run
  ```
- Check status:
  ```bash
  curl http://localhost:8000/pipeline/status
  ```

## Deployment & Productionization

### Backend
- Use a managed database such as PostgreSQL instead of local SQLite.
- Replace the built-in development server with production-grade deployment:
  - `gunicorn -k uvicorn.workers.UvicornWorker main:app`
- Run asynchronous pipelines in a proper queue system:
  - Celery, RQ, or a hosted task queue
- Add API authentication and authorization for secure access.
- Add logging, monitoring, and error reporting.
- Add retry logic and rate limiting for OpenAI calls.

### Frontend
- Build static assets:
  ```bash
  npm run build
  ```
- Serve the build from a CDN or static host.
- Add user authentication and session-based access.
- Add better filtering, search, pagination, and saved views.

### Infrastructure
- Store secrets securely via environment variables or a secrets manager
- Use a managed Postgres or hosted SQLite alternative if required
- Add a simple CI/CD pipeline to run tests, linting, and deployment
- Add observability: request metrics, database health, pipeline job metrics

## Tradeoffs

### What this version takes care of
- A minimal end-to-end pipeline from data ingestion to UI presentation
- Clear separation between backend API, pipeline logic, and frontend UI
- Simple database persistence and seed-based testing data
- Reliable deterministic scoring combined with AI reasoning
- Basic pipeline status reporting

### What is intentionally simplified
- No live GAF scraping or production web search crawl
- No multi-tenant or user-based access controls
- No full search/filter interface for contractors
- No dedicated pipeline worker queue or retry strategy
- Frontend is a lightweight MVP rather than a feature-rich CRM dashboard

## Improvements Given More Time

### Data & pipeline
- Add live GAF scraping / extraction from the public contractor listing
- Move to a real ETL pipeline with worker queues and batch processing
- Store full contract history and lead activity in normalized tables
- Add metadata tracking for pipeline runs and contractor updates
- Add export and bulk action support for the sales team

### AI & scoring
- Use OpenAI for structured extraction of contractor capabilities and specialties
- Add explainable scoring factors surfaced in the UI
- Create a more robust `perplexity_score` prompt and validation layer
- Add contract-level signals such as relationship status, channel fit, and recent bids

### UI / UX
- Add inline filters, sorting, paging, and search by geography
- Add a real chat interface for follow-up questions
- Add lead cards with actionable next steps, priority reasons, and status labels
- Improve visual polish and mobile responsiveness

## Notes
- The pipeline currently uses seed data for deterministic onboarding and development.
- The OpenAI integration is used for sales summaries and a Perplexity-style decision signal, not for raw scoring math alone.
- The current `DATABASE_URL` default is SQLite; production should use PostgreSQL or another managed database.

