from datetime import datetime

from pydantic import BaseModel, Field


class QuestionResponse(BaseModel):
    id: int
    text: str
    slug: str
    created_at: datetime


class OpinionSubmit(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Your opinion text")
    region: str | None = Field(None, max_length=64, description="Your region (country/area)")


class OpinionResponse(BaseModel):
    hash: str
    anonymized_text: str
    language: str | None
    region: str | None
    trust_score: float
    created_at: datetime


class OpinionWithDistance(BaseModel):
    hash: str
    anonymized_text: str
    region: str | None
    trust_score: float


class SubmitResponse(BaseModel):
    hash: str
    anonymized_text: str
    language: str | None
    nearest: list[OpinionWithDistance]
    bridge: OpinionWithDistance | None


class ClusterPoint(BaseModel):
    hash: str
    x: float
    y: float
    region: str | None
    text_preview: str


class VisualizationResponse(BaseModel):
    question: QuestionResponse
    points: list[ClusterPoint]
    total_opinions: int


class SummaryResponse(BaseModel):
    question: QuestionResponse
    summary: str
    total_opinions: int
