"""
Cosailor API — B2B roofing sales intelligence backend

Routes:
  GET  /health                      liveness check
  GET  /contractors                 paginated, sorted lead list
  GET  /contractors/{id}            single contractor detail
  POST /contractors/{id}/ask        live Q&A about a contractor
  POST /pipeline/run                trigger enrichment pipeline (async)
  GET  /pipeline/status             latest pipeline run status
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Contractor, PipelineRun
from pipeline import run_pipeline as _run_pipeline
from schemas import (
    AskRequest,
    AskResponse,
    ContractorResponse,
    ContractorsListResponse,
    PipelineStatusResponse,
)
from seed_data import SEED_CONTRACTORS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="Cosailor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB init + seed on startup ─────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    _seed_contractors_if_empty()


def _seed_contractors_if_empty():
    db = next(get_db())
    try:
        if db.query(Contractor).count() == 0:
            logger.info("Seeding %d contractors...", len(SEED_CONTRACTORS))
            for data in SEED_CONTRACTORS:
                db.add(Contractor(**data))
            db.commit()
            logger.info("Seed complete.")
    finally:
        db.close()


# ── Helper ───────────────────────────────────────────────────────────────────
def _latest_pipeline_run(db: Session) -> PipelineRun | None:
    return db.query(PipelineRun).order_by(desc(PipelineRun.started_at)).first()


# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/contractors", response_model=ContractorsListResponse)
def list_contractors(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Returns contractors sorted by priority_score descending.
    Un-enriched contractors fall to the bottom (null scores sort last).
    """
    query = db.query(Contractor).order_by(
        # NULLs last: enriched contractors with scores come first
        Contractor.priority_score.is_(None),
        desc(Contractor.priority_score),
    )
    total = query.count()
    contractors = query.offset(offset).limit(limit).all()

    pipeline_run = _latest_pipeline_run(db)
    pipeline_status = pipeline_run.status if pipeline_run else None

    return ContractorsListResponse(
        contractors=[ContractorResponse.model_validate(c) for c in contractors],
        total=total,
        pipeline_status=pipeline_status,
    )


@app.get("/contractors/{contractor_id}", response_model=ContractorResponse)
def get_contractor(contractor_id: int, db: Session = Depends(get_db)):
    contractor = db.get(Contractor, contractor_id)
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")
    return ContractorResponse.model_validate(contractor)


@app.post("/contractors/{contractor_id}/ask", response_model=AskResponse)
async def ask_about_contractor(
    contractor_id: int,
    body: AskRequest,
    db: Session = Depends(get_db),
):
    """
    Live Q&A: answer ad-hoc questions about a specific contractor.
    Uses all known data as context so answers are grounded in real signals.
    """
    contractor = db.get(Contractor, contractor_id)
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    talking_points = []
    if contractor.talking_points:
        try:
            talking_points = json.loads(contractor.talking_points)
        except Exception:
            pass

    context = f"""
You are a sales intelligence assistant for a roofing materials distributor.
Answer the sales rep's question about this contractor based on the data below.
Be concise and actionable. If data is missing, say so and suggest how to find it.

ASSUMPTION: This distributor is NOT GAF-authorized. Contractors tied to GAF's
authorized supply chain (Master Elite, Certified Plus) are harder to convert.

--- CONTRACTOR DATA ---
Name: {contractor.name}
Location: {contractor.city}, {contractor.state}
GAF Certification Tier: {contractor.gaf_tier}
Phone: {contractor.phone or 'unknown'}
Website: {contractor.website or 'none listed'}
Distance from distributor: {contractor.distance_miles} miles
Review count: {contractor.review_count}
Average rating: {contractor.avg_rating}/5.0
Years in business: {contractor.years_in_business}
Estimated employees: {contractor.employee_count or 'unknown'}
Estimated annual revenue: {'${:,}'.format(contractor.estimated_annual_revenue) if contractor.estimated_annual_revenue else 'unknown'}
Revenue confidence: {contractor.revenue_confidence or 'unknown'}
Priority score: {contractor.priority_score}/100

AI Brief: {contractor.brief or 'Not yet generated — run the pipeline first.'}
Talking points: {', '.join(talking_points) if talking_points else 'None yet'}
""".strip()

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": body.question},
        ],
        max_tokens=400,
    )

    return AskResponse(
        answer=response.choices[0].message.content,
        contractor_id=contractor_id,
    )


@app.post("/pipeline/run", response_model=PipelineStatusResponse)
async def trigger_pipeline(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger the enrichment pipeline as a background job.
    Returns immediately — poll /pipeline/status for progress.
    Idempotent: will not start a new run if one is already running.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")

    if not openai_key or not perplexity_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY and PERPLEXITY_API_KEY must both be set in .env",
        )

    # Prevent duplicate runs
    latest = _latest_pipeline_run(db)
    if latest and latest.status == "running":
        return PipelineStatusResponse(
            status="running",
            total=latest.total_contractors,
            processed=latest.processed_contractors,
        )

    contractors = db.query(Contractor).all()
    pipeline_run = PipelineRun(status="pending", started_at=datetime.now(timezone.utc))
    db.add(pipeline_run)
    db.commit()
    db.refresh(pipeline_run)

    # Kick off in background — API returns immediately
    background_tasks.add_task(
        _run_pipeline_task,
        contractors,
        openai_key,
        perplexity_key,
        pipeline_run.id,
    )

    return PipelineStatusResponse(
        status="running",
        total=len(contractors),
        processed=0,
    )


async def _run_pipeline_task(
    contractors, openai_key: str, perplexity_key: str, run_id: int
):
    """Background task wrapper — opens its own DB session."""
    db = next(get_db())
    try:
        pipeline_run = db.get(PipelineRun, run_id)
        # Re-fetch contractors in this session
        fresh_contractors = db.query(Contractor).all()
        await _run_pipeline(fresh_contractors, openai_key, perplexity_key, db, pipeline_run)
    except Exception as exc:
        logger.error("Pipeline task error: %s", exc)
        pipeline_run = db.get(PipelineRun, run_id)
        if pipeline_run:
            pipeline_run.status = "failed"
            pipeline_run.error_message = str(exc)
            db.commit()
    finally:
        db.close()


@app.get("/pipeline/status", response_model=PipelineStatusResponse)
def pipeline_status(db: Session = Depends(get_db)):
    latest = _latest_pipeline_run(db)
    if not latest:
        return PipelineStatusResponse(status="never_run", total=0, processed=0)
    return PipelineStatusResponse(
        status=latest.status,
        total=latest.total_contractors,
        processed=latest.processed_contractors,
        error=latest.error_message,
    )
