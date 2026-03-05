"""Pydantic models for reports and generation requests — v2."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReportStatus(str, Enum):
    DRAFT = "draft"
    EDITED = "edited"
    FINAL = "final"


class GenerateRequest(BaseModel):
    dictated_text: str = Field(..., min_length=1)
    doctor_id: str = Field(..., min_length=1)
    report_type: str = Field(..., min_length=1, description="e.g. CT, MRI, X-Ray, Ultrasound, PET")
    body_region: str = Field(..., min_length=1, description="e.g. Chest, Abdomen, Brain, Spine")


class AgentTraceEntry(BaseModel):
    agent: str
    success: bool
    confidence: float = 0.0
    revision: int | None = None
    error: str | None = None


class GroundingInfo(BaseModel):
    is_grounded: bool = True
    overall_confidence: float = 0.0
    section_scores: dict[str, float] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    hallucinated_claims: list[str] = Field(default_factory=list)


class ReviewInfo(BaseModel):
    overall_quality: float = 0.0
    medical_accuracy: float = 0.0
    terminology_correctness: float = 0.0
    completeness: float = 0.0
    style_adherence: float = 0.0
    critical_issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    id: str
    doctor_id: str
    input_text: str
    findings: str
    impressions: str
    recommendations: str
    report_type: str = ""
    body_region: str = ""
    status: ReportStatus = ReportStatus.DRAFT
    grounding: GroundingInfo = Field(default_factory=GroundingInfo)
    review: ReviewInfo = Field(default_factory=ReviewInfo)
    revisions: int = 0
    decision: str = ""
    pipeline_trace: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = ""


class ReportVersion(BaseModel):
    version: int
    findings: str
    impressions: str
    recommendations: str
    status: ReportStatus
    edited_at: datetime


class ReportResponse(BaseModel):
    id: str
    doctor_id: str
    input_text: str
    findings: str
    impressions: str
    recommendations: str
    report_type: str = ""
    body_region: str = ""
    status: ReportStatus = ReportStatus.DRAFT
    versions: list[ReportVersion] = []
    grounding: GroundingInfo | None = None
    review: ReviewInfo | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportUpdate(BaseModel):
    findings: str | None = None
    impressions: str | None = None
    recommendations: str | None = None
