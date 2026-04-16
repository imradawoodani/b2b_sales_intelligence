"""
Cosailor API — B2B roofing sales intelligence backend
Updated to support Real-Time GAF Scraping + Perplexity Enrichment.
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
from pipeline import compute_effective_score, run_pipeline as _run_pipeline
from schemas import (
    AskRequest,
    AskResponse,
    ContractorResponse,
    ContractorsListResponse,
    PipelineStatusResponse,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="Cosailor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB init ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    # Ensures tables are created in Postgres on boot
    Base.metadata.create_all(bind=engine)


# ── Helpers ──────────────────────────────────────────────────────────────────
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
    assume_non_authorized: bool = False,
    db: Session = Depends(get_db),
):
    contractors = db.query(Contractor).all()
    scored = []
    for contractor in contractors:
        display_score = compute_effective_score(contractor, assume_non_authorized)
        scored.append((display_score, contractor))

    scored.sort(key=lambda item: (item[0] is None, -(item[0] or 0), item[1].id))
    total = len(scored)
    page = scored[offset: offset + limit]

    contractor_responses = []
    for display_score, contractor in page:
        contractor_data = ContractorResponse.model_validate(contractor).model_dump()
        contractor_data["display_score"] = display_score
        contractor_responses.append(ContractorResponse.model_validate(contractor_data))

    pipeline_run = _latest_pipeline_run(db)
    pipeline_status = pipeline_run.status if pipeline_run else "never_run"

    return ContractorsListResponse(
        contractors=contractor_responses,
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
    contractor = db.get(Contractor, contractor_id)
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    context = f"""
You are a sales intelligence assistant. Answer based on:
Name: {contractor.name} | GAF Tier: {contractor.gaf_tier} | Revenue: {contractor.estimated_annual_revenue}
Brief: {contractor.brief}
"""
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
    return AskResponse(answer=response.choices[0].message.content, contractor_id=contractor_id)


@app.post("/pipeline/run", response_model=PipelineStatusResponse)
async def trigger_pipeline(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    openai_key = os.getenv("OPENAI_API_KEY")

    if not openai_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY missing in .env")

    latest = _latest_pipeline_run(db)
    if latest and latest.status in ["running", "scraping", "enriching"]:
        return PipelineStatusResponse(
            status=latest.status,
            total=latest.total_contractors,
            processed=latest.processed_contractors,
            error=latest.error_message,
        )

    pipeline_run = PipelineRun(status="pending", started_at=datetime.now(timezone.utc))
    db.add(pipeline_run)
    db.commit()
    db.refresh(pipeline_run)

    background_tasks.add_task(
        _run_pipeline_task,
        "10013",
        openai_key,
        pipeline_run.id,
    )

    return PipelineStatusResponse(status="pending", total=0, processed=0)


async def _run_pipeline_task(
    zipcode: str, openai_key: str, run_id: int
):
    from database import SessionLocal
    db = SessionLocal()
    pipeline_run = None
    try:
        pipeline_run = db.get(PipelineRun, run_id)
        await _run_pipeline(zipcode, openai_key, db, pipeline_run)
    except Exception as exc:
        logger.error("Pipeline task error: %s", exc)
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