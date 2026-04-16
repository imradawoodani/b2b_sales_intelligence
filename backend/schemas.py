from pydantic import BaseModel, field_validator
from typing import Optional, List, Any
from datetime import datetime
import json


class ContractorResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    gaf_tier: Optional[str] = "none"
    distance_miles: Optional[float] = None
    review_count: Optional[int] = 0
    avg_rating: Optional[float] = None
    years_in_business: Optional[int] = None
    employee_count: Optional[int] = None
    estimated_annual_revenue: Optional[int] = None
    revenue_confidence: Optional[str] = None
    priority_score: Optional[int] = None
    display_score: Optional[int] = None
    perplexity_score: Optional[int] = None
    perplexity_insights: Optional[List[str]] = None
    brief: Optional[str] = None
    talking_points: Optional[List[str]] = None
    score_breakdown: Optional[dict] = None
    enriched: bool = False
    enriched_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("talking_points", mode="before")
    @classmethod
    def parse_talking_points(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

    @field_validator("perplexity_insights", mode="before")
    @classmethod
    def parse_perplexity_insights(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

    @field_validator("score_breakdown", mode="before")
    @classmethod
    def parse_score_breakdown(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v


class ContractorsListResponse(BaseModel):
    contractors: List[ContractorResponse]
    total: int
    pipeline_status: Optional[str] = None


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    contractor_id: int


class PipelineStatusResponse(BaseModel):
    status: str
    total: int
    processed: int
    error: Optional[str] = None
