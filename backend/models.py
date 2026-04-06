from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base


class Contractor(Base):
    __tablename__ = "contractors"

    id = Column(Integer, primary_key=True, index=True)

    # --- Raw GAF data ---
    name = Column(String, nullable=False, index=True)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    phone = Column(String)
    website = Column(String)
    # master_elite | certified_plus | certified | none
    gaf_tier = Column(String, default="none")
    distance_miles = Column(Float)
    review_count = Column(Integer, default=0)
    avg_rating = Column(Float)
    years_in_business = Column(Integer)

    # --- Perplexity enrichment ---
    employee_count = Column(Integer)
    estimated_annual_revenue = Column(Integer)   # USD
    revenue_confidence = Column(String)          # low | medium | high
    perplexity_raw = Column(Text)                # raw JSON blob for auditing

    # --- GPT-4o scoring ---
    priority_score = Column(Integer)             # 0-100
    brief = Column(Text)
    talking_points = Column(Text)                # JSON array stored as string
    score_breakdown = Column(Text)               # JSON object stored as string

    # --- Pipeline metadata ---
    enriched = Column(Boolean, default=False)
    enriched_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True)
    # pending | running | completed | failed
    status = Column(String, default="pending")
    total_contractors = Column(Integer, default=0)
    processed_contractors = Column(Integer, default=0)
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)
    error_message = Column(Text)
