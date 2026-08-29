from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Dimension(str, Enum):
    RESOURCE = "RESOURCE"
    MEANING = "MEANING"
    VISIBILITY = "VISIBILITY"
    EXPERIENCE = "EXPERIENCE"
    PRODUCT = "PRODUCT"
    CONVERSION = "CONVERSION"
    ADVOCACY = "ADVOCACY"
    REGENERATION = "REGENERATION"


class Reliability(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNRATED = "UNRATED"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    ACCEPTED = "ACCEPTED"
    EDITED = "EDITED"
    REJECTED = "REJECTED"


class HypothesisStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"


class EvidenceNeedPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceNeedStatus(str, Enum):
    OPEN = "OPEN"
    COLLECTED = "COLLECTED"
    DISMISSED = "DISMISSED"


class Place(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    location: Optional[str] = None
    place_type: Optional[str] = None
    description: Optional[str] = None
    diagnostic_scope: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Evidence(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    place_id: UUID
    title: str
    source_type: str
    source_name: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    url: Optional[str] = None
    file_reference: Optional[str] = None
    excerpt: str
    notes: Optional[str] = None
    reliability: Reliability = Reliability.UNRATED
    scope: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    place_id: UUID
    statement: str
    dimension: Dimension
    evidence_ids: list[UUID]
    generated_by: str = "human"
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    original_statement: Optional[str] = None
    human_revision: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Gap(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    place_id: UUID
    from_dimension: Dimension
    to_dimension: Dimension
    description: str
    finding_ids: list[UUID] = Field(default_factory=list)
    status: str = "CANDIDATE"


class Hypothesis(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    place_id: UUID
    gap_id: Optional[UUID] = None
    statement: str
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)
    contradicting_evidence_ids: list[UUID] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.UNKNOWN
    confidence_reason: Optional[str] = None
    status: HypothesisStatus = HypothesisStatus.DRAFT
    human_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EvidenceNeed(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    place_id: UUID
    related_hypothesis_id: UUID
    question: str
    why_it_matters: str
    recommended_method: Optional[str] = None
    priority: EvidenceNeedPriority = EvidenceNeedPriority.MEDIUM
    status: EvidenceNeedStatus = EvidenceNeedStatus.OPEN
    created_at: datetime = Field(default_factory=datetime.utcnow)
