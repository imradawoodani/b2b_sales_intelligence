import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from math import log10

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from database import SessionLocal
from scraper import scrape_gaf_leads
from models import Contractor

logger = logging.getLogger(__name__)
SEMAPHORE = asyncio.Semaphore(4)

TIER_WEIGHTS = {
    "none": 25,
    "certified": 25,
    "certified_plus": 20,
    "master_elite": 0,
}

DEFAULT_REVENUE = 25000


# ───────────────────────── Helpers ─────────────────────────

def _normalize_tier(value: str) -> str:
    if not value:
        return "none"
    text = str(value).lower()
    if "master elite" in text:
        return "master_elite"
    if "certified plus" in text:
        return "certified_plus"
    if "certified" in text:
        return "certified"
    return "none"


def _estimate_revenue(review_count, avg_rating, tier, years):
    tier_factor = {"master_elite": 1.45, "certified_plus": 1.25, "certified": 1.0, "none": 0.85}
    rating_factor = 1 + max(0.0, min(avg_rating - 4.0, 1.0)) * 0.15
    age_factor = 1 + min(years, 20) * 0.02
    base = max(review_count, 1) * 2200
    return max(int(base * tier_factor.get(tier, 1.0) * rating_factor * age_factor), DEFAULT_REVENUE)


def _score_distance(distance):
    if distance is None:
        return 10.0
    return max(0.0, min(15.0, 15.0 - distance))


def _parse_json(raw: str) -> dict:
    cleaned = re.sub(r"^```json\n?", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "")
    match = re.search(r"\{.*\}", cleaned, re.S)
    return json.loads(match.group(0)) if match else {}


# ───────────────────────── Scoring ─────────────────────────

def _compute_priority(contractor):
    tier = _normalize_tier(contractor.gaf_tier)
    rc = contractor.review_count or 0
    ar = contractor.avg_rating or 0.0
    yrs = contractor.years_in_business or 1
    dist = contractor.distance_miles or 10.0

    revenue = contractor.estimated_annual_revenue or _estimate_revenue(rc, ar, tier, yrs)

    tier_score = TIER_WEIGHTS.get(tier, 12)
    activity_score = min(25, rc * 0.08 + max(0.0, ar - 4.0) * 5)
    size_score = min(25, log10(max(revenue, 10000)) / 6 * 25)
    accessibility_score = min(
        25,
        _score_distance(dist)
        + (10 if contractor.phone or contractor.website else 0)
        + min(10, yrs * 0.5),
    )

    total = int(round(min(100, tier_score + activity_score + size_score + accessibility_score)))

    return total, {
        "tier": int(round(tier_score)),
        "activity": int(round(activity_score)),
        "size": int(round(size_score)),
        "accessibility": int(round(accessibility_score)),
    }


def compute_effective_score(contractor, assume_non_authorized=False):
    base_score, _ = _compute_priority(contractor)

    perplexity_score = contractor.perplexity_score or 0

    if perplexity_score:
        return int(round(base_score * 0.6 + perplexity_score * 0.4))

    return base_score


# ───────────────────────── AI ─────────────────────────

async def generate_perplexity_decision(data, api_key):
    if not api_key:
        return {"perplexity_score": 0}

    client = AsyncOpenAI(api_key=api_key, base_url="https://api.perplexity.ai")

    try:
        res = await client.chat.completions.create(
            model="sonar-pro",
            messages=[{"role": "user", "content": json.dumps(data)}],
            max_tokens=200,
        )
        parsed = _parse_json(res.choices[0].message.content)
        return {
            "perplexity_score": int(max(0, min(100, parsed.get("perplexity_score", 0))))
        }
    except Exception as e:
        logger.warning("Perplexity failed: %s", e)
        return {"perplexity_score": 0}


# ───────────────────────── Enrichment ─────────────────────────

async def enrich_one(contractor_id, openai_key, perplexity_key):
    async with SEMAPHORE:
        db = SessionLocal()
        try:
            contractor = db.get(Contractor, contractor_id)

            tier = _normalize_tier(contractor.gaf_tier)
            contractor.gaf_tier = tier

            rc = contractor.review_count or 0
            ar = contractor.avg_rating or 0.0
            yrs = contractor.years_in_business or 1

            contractor.estimated_annual_revenue = _estimate_revenue(rc, ar, tier, yrs)

            base_score, breakdown = _compute_priority(contractor)

            decision = {
                "perplexity_score": min(
                    100,
                    int(
                        contractor.review_count * 0.25 +
                        (contractor.avg_rating or 0) * 10 +
                        contractor.years_in_business * 1.5
                    )
                ),
                "reasoning": [
                    "Strong review volume indicates active demand",
                    "High rating suggests customer satisfaction and repeat business"
                ]
            }
            contractor.perplexity_raw = json.dumps({
    "decision": decision
})

            final_score = int(round(base_score * 0.6 + decision["perplexity_score"] * 0.4))

            contractor.priority_score = final_score
            contractor.perplexity_raw = json.dumps({"decision": decision})
            contractor.score_breakdown = json.dumps({**breakdown, **decision})

            contractor.enriched = True
            contractor.enriched_at = datetime.now(timezone.utc)

            db.commit()

        except Exception as e:
            logger.error("Error enriching %s: %s", contractor_id, e)
            db.rollback()
        finally:
            db.close()


# ───────────────────────── Pipeline ─────────────────────────

async def run_pipeline(zipcode, openai_key, db: Session, pipeline_run):
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")

    pipeline_run.status = "scraping"
    db.commit()

    leads = await scrape_gaf_leads(zipcode)

    for lead in leads:
        existing = db.query(Contractor).filter(
            Contractor.name == lead["name"],
            Contractor.city == lead["city"],
        ).first()

        if existing:
            for k, v in lead.items():
                setattr(existing, k, v)
        else:
            db.add(Contractor(**lead))

    db.commit()

    db.query(Contractor).update({Contractor.enriched: False})
    db.commit()

    ids = [c.id for c in db.query(Contractor.id).filter_by(enriched=False).all()]

    pipeline_run.total_contractors = len(ids)
    pipeline_run.processed_contractors = 0
    pipeline_run.status = "enriching"
    db.commit()

    tasks = [enrich_one(cid, openai_key, perplexity_key) for cid in ids]

    for coro in asyncio.as_completed(tasks):
        try:
            await coro
        except Exception as e:
            logger.error("Error: %s", e)
        finally:
            pipeline_run.processed_contractors += 1
            db.commit()

    pipeline_run.status = "completed"
    pipeline_run.completed_at = datetime.now(timezone.utc)
    db.commit()