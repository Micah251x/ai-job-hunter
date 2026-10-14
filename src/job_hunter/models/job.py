"""Internal job model.

Every source adapter produces a job. Nothing downstream knows which source a job came from except via Job.source.
"""

import hashlib
from enum import StrEnum
from typing import Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

KEY_SEPARATOR = "#"

class JobSource(StrEnum):
    HIMALAYAS  = "himalayas"
    GREENHOUSE = "greenhouse"
    LEVER      = "lever"
    ASHBY      = "ashby"

class RemoteStatus(StrEnum):
    REMOTE  = "remote"
    HYBRID  = "hybrid"
    ONSITE  = "onsite"
    UNKNOWN = "unknown"

class JobStatus(StrEnum):
    FILTERED = "filtered" #rejected by the deterministic filter, never queued
    QUEUED   = "queued" #passed the filter, message sent to sqs
    ANALYZED = "analyzed" #LLM analysis stored
    FAILED   = "failed" #analysis failed permanently (landed in the DLQ)
    NOTIFIED = "notified" #included in digest email

class Recommendation(StrEnum):
    PRIORITY_APPLY = "priority_apply"
    APPLY          = "apply"
    REVIEW         = "review"
    REJECT         = "reject"

class JobAnalysis(BaseModel):
    """Validates the LLM's response

    Strict on purpose: junk from the LLM should raise ValidationError, which
    leads to a retry and eventually the DLQ, not bad data in DynamoDB
    """

    model_config = ConfigDict(extra="forbid")

    match_score: int = Field(ge=0, le=100)
    strengths: list[str]
    gaps: list[str]
    reason: str = Field(min_length=1)

    @computed_field
    @property
    def recommendation(self) -> Recommendation:
        #Deterministic code owns the tiers; the LLM only supplies the score.
        if self.match_score >= 90:
            return Recommendation.PRIORITY_APPLY
        if self.match_score >= 80:
            return Recommendation.APPLY
        if self.match_score >= 70:
            return Recommendation.REVIEW
        return Recommendation.REJECT
    
class Job(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # identity
    source: JobSource
    company: str = Field(min_length=1)
    source_job_id: str = Field(min_length=1)

    # posting content
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    location_raw: str | None = None
    description: str
    
    # deterministic facts (set by adapter/filter, never by the LLM)
    remote_status: RemoteStatus = RemoteStatus.UNKNOWN
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    posted_at: AwareDatetime | None = None

    # bookkeeping
    status: JobStatus
    filter_reason: str | None = None
    first_seen_at: AwareDatetime
    expires_at: int | None = None
    analysis: JobAnalysis | None = None

    @field_validator("company", "source_job_id")
    @classmethod
    def reject_key_separator(cls, value: str) -> str:
        if KEY_SEPARATOR in value:
            raise ValueError(f"must not contain {KEY_SEPARATOR!r}")
        return value

    @field_validator("company")
    @classmethod
    def lowercase_company(cls, value: str) -> str:
        return value.lower()

    @field_validator("salary_min", "salary_max")
    @classmethod
    def zero_salary_means_unpublished(cls, value: int | None) -> int | None:
        # An API reporting 0 means "not published", not unpaid work.
        if value == 0:
            return None
        if value is not None and value < 0:
            raise ValueError("salary must not be negative")
        return value

    @model_validator(mode="after")
    def check_salary_range(self) -> Self:
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must not exceed salary_max")
        return self

    @computed_field
    @property
    def job_key(self) -> str:
        return KEY_SEPARATOR.join((self.source, self.company, self.source_job_id))

    @computed_field
    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.description.encode("utf-8")).hexdigest()
