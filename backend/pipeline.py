"""
Pipeline: GAF seed data → Perplexity enrichment → GPT-4o scoring → DB

Designed for scale:
- Async/concurrent with semaphore to respect API rate limits
- Idempotent: re-running updates existing records rather than duplicating
- Each stage (enrich, score) is independent so partial failures are recoverable
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from openai import AsyncOpenAI
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Max concurrent Perplexity + OpenAI calls to avoid rate limiting
SEMAPHORE = asyncio.Semaphore(3)

# ── Perplexity uses the OpenAI SDK interface with a different base URL ──────
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
PERPLEXITY_MODEL = "sonar-pro"

SCORING_SYSTEM_PROMPT = """
You are a sales intelligence engine for a roofing materials distributor.

⚠ KEY ASSUMPTION: This distributor is NOT a GAF-authorized distributor.
This is critical because:
- GAF Master Elite contractors MUST buy from authorized distributors for Golden Pledge warranty jobs
- GAF Certified Plus contractors MUST buy from authorized distributors for Silver Pledge jobs
- Lower/no GAF certification = more purchasing flexibility = HIGHER priority for us
- Un-certified contractors have ZERO supply chain commitment and are our warmest leads

Score this contractor 0–100 using this exact rubric:

TIER FLEXIBILITY (0–25 pts) — how freely can they buy from non-authorized suppliers?
  - none (no GAF certification): 25 pts
  - certified: 20 pts
  - certified_plus: 12 pts
  - master_elite: 6 pts

ACTIVITY LEVEL (0–25 pts) — how many active jobs are they running?
  - reviews/year velocity, total review count, recency of work
  - High velocity + high volume = 20–25 pts

BUSINESS SIZE (0–25 pts) — revenue potential for us
  - Estimated annual revenue, employee/crew count, scale of operation

ACCESSIBILITY (0–25 pts) — can we reach and service them?
  - Contact completeness (phone + website = full marks for this sub-component)
  - Distance from distributor (closer = better)
  - Years in business (established = more reliable, predictable buyer)

Return ONLY a valid JSON object. No markdown, no preamble, no explanation:
{
  "priority_score": <integer 0-100>,
  "estimated_annual_revenue": <integer USD, use best estimate if unknown>,
  "revenue_confidence": "<low|medium|high>",
  "employee_count": <integer, estimate if unknown>,
  "brief": "<2-3 sentence sales brief: who they are, why/why not to call them, best angle>",
  "talking_points": ["<point 1>", "<point 2>", "<point 3>"],
  "score_breakdown": {
    "tier_flexibility": <0-25>,
    "activity_level": <0-25>,
    "business_size": <0-25>,
    "accessibility": <0-25>
  }
}
"""


async def enrich_with_perplexity(contractor_data: dict, api_key: str) -> dict:
    """
    Use Perplexity's web search to find real-world signals about a contractor:
    revenue estimates, employee count, news, etc.
    Returns a dict of enrichment signals.
    """
    client = AsyncOpenAI(api_key=api_key, base_url=PERPLEXITY_BASE_URL)

    query = (
        f"Roofing contractor business profile: {contractor_data['name']} "
        f"in {contractor_data['city']}, {contractor_data['state']}. "
        f"Find: estimated annual revenue, number of employees, years operating, "
        f"any news or notable projects. Return as JSON with keys: "
        f"estimated_annual_revenue (int USD), employee_count (int), "
        f"key_facts (list of strings), revenue_confidence (low|medium|high)."
    )

    try:
        response = await client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a business research assistant. "
                        "Return ONLY valid JSON with no markdown fences or preamble."
                    ),
                },
                {"role": "user", "content": query},
            ],
            max_tokens=500,
        )
        raw = response.choices[0].message.content.strip()
        # Strip accidental markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as exc:
        logger.warning("Perplexity enrichment failed for %s: %s", contractor_data["name"], exc)
        return {}


async def score_with_openai(contractor_data: dict, enrichment: dict, api_key: str) -> dict:
    """
    Use GPT-4o to synthesize all available signals into a priority score,
    sales brief, and talking points.
    """
    client = AsyncOpenAI(api_key=api_key)

    combined = {**contractor_data, **enrichment}
    # Add derived review velocity (reviews per year as a proxy for job volume)
    yib = combined.get("years_in_business") or 1
    combined["review_velocity_per_year"] = round(
        (combined.get("review_count") or 0) / yib, 1
    )
    # Flag contact completeness
    combined["has_phone"] = bool(combined.get("phone"))
    combined["has_website"] = bool(combined.get("website"))

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(combined)},
            ],
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as exc:
        logger.warning("GPT-4o scoring failed for %s: %s", contractor_data["name"], exc)
        return {}


async def enrich_one(contractor, openai_key: str, perplexity_key: str, db: Session):
    """
    Enrich and score a single contractor. Uses semaphore for rate limiting.
    """
    async with SEMAPHORE:
        contractor_data = {
            "name": contractor.name,
            "city": contractor.city,
            "state": contractor.state,
            "phone": contractor.phone,
            "website": contractor.website,
            "gaf_tier": contractor.gaf_tier,
            "distance_miles": contractor.distance_miles,
            "review_count": contractor.review_count,
            "avg_rating": contractor.avg_rating,
            "years_in_business": contractor.years_in_business,
        }

        logger.info("Enriching: %s", contractor.name)

        # Stage 1 — Perplexity web search
        enrichment = await enrich_with_perplexity(contractor_data, perplexity_key)

        # Stage 2 — GPT-4o scoring
        scored = await score_with_openai(contractor_data, enrichment, openai_key)

        if not scored:
            logger.warning("Skipping DB write for %s — scoring returned empty", contractor.name)
            return

        # Stage 3 — Persist to DB
        contractor.priority_score = scored.get("priority_score")
        contractor.estimated_annual_revenue = scored.get("estimated_annual_revenue")
        contractor.revenue_confidence = scored.get("revenue_confidence")
        contractor.employee_count = scored.get("employee_count")
        contractor.brief = scored.get("brief")
        contractor.talking_points = json.dumps(scored.get("talking_points", []))
        contractor.score_breakdown = json.dumps(scored.get("score_breakdown", {}))
        # Perplexity raw for auditability
        contractor.perplexity_raw = json.dumps(enrichment)
        contractor.enriched = True
        contractor.enriched_at = datetime.now(timezone.utc)

        db.commit()
        logger.info("Saved enrichment for: %s (score=%s)", contractor.name, contractor.priority_score)


async def run_pipeline(
    contractors: list,
    openai_key: str,
    perplexity_key: str,
    db: Session,
    pipeline_run,
):
    """
    Run enrichment for all contractors concurrently (bounded by SEMAPHORE).
    Updates the PipelineRun record as work completes.
    """
    pipeline_run.total_contractors = len(contractors)
    pipeline_run.status = "running"
    db.commit()

    tasks = [enrich_one(c, openai_key, perplexity_key, db) for c in contractors]

    for coro in asyncio.as_completed(tasks):
        try:
            await coro
        except Exception as exc:
            logger.error("Unexpected error during enrichment: %s", exc)
        finally:
            pipeline_run.processed_contractors += 1
            db.commit()

    pipeline_run.status = "completed"
    pipeline_run.completed_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Pipeline complete. %d/%d processed.", pipeline_run.processed_contractors, len(contractors))
