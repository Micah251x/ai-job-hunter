from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from job_hunter.models.job import (
    Job,
    JobAnalysis,
    JobSource,
    JobStatus,
    Recommendation,
    RemoteStatus,
)


@pytest.fixture
def valid_job_data() -> dict:
    """Minimal valid input. tests copy and mutate this instead of rebuilding it."""
    return{
        "source": "lever",
        "company": "minted",
        "source_job_id": "4f2a",
        "title": "Senior Software Engineer",
        "url": "https://jobs.lever.co/minted/4f2a",
        "description": "Build things.",
        "status": "queued",
        "first_seen_at": datetime(2026, 10,13, tzinfo=timezone.utc),
    }


def make_analysis(match_score: int) -> JobAnalysis:
    return JobAnalysis(
        match_score=match_score,
        strengths=["Python"],
        gaps=["Go"],
        reason="Solid backend fit.",
    )

#job: construction

def test_valid_job_builds(valid_job_data):
    job = Job(**valid_job_data)

    assert job.source is JobSource.LEVER
    assert job.status is JobStatus.QUEUED
    assert job.remote_status is RemoteStatus.UNKNOWN
    assert job.analysis is None


def test_missing_required_field_raises(valid_job_data):
    del valid_job_data["title"]
    with pytest.raises(ValidationError):
        Job(**valid_job_data)


def test_unknown_field_raises(valid_job_data):
    valid_job_data["salry_max"] = 150_000
    with pytest.raises(ValidationError):
        Job(**valid_job_data)

def test_invalid_enum_raises(valid_job_data):
    valid_job_data["source"] = "indeed"
    with pytest.raises(ValidationError):
        Job(**valid_job_data)


def test_naive_datetime_raises(valid_job_data):
    valid_job_data["first_seen_at"] = datetime(2026, 10,13)
    with pytest.raises(ValidationError):
        Job(**valid_job_data)


# job: identity


def test_job_key_is_assembled(valid_job_data):
    assert Job(**valid_job_data).job_key == "lever#minted#4f2a"


def test_job_key_cannot_be_passed_in(valid_job_data):
    valid_job_data["job_key"] = "lever#someone-else#9999"
    with pytest.raises(ValidationError):
        Job(**valid_job_data)


def test_company_is_lowercase(valid_job_data):
    valid_job_data["company"] = "Minted"
    assert Job(**valid_job_data).job_key == "lever#minted#4f2a"


@pytest.mark.parametrize("field", ["company", "source_job_id"])
def test_separator_in_key_component_raises(valid_job_data, field):
    valid_job_data[field] = "a#b"
    with pytest.raises(ValidationError):
        Job(**valid_job_data)


#job: salary

def test_zero_salary_becomes_none(valid_job_data):
    valid_job_data["salary_min"] = 0
    valid_job_data["salary_max"] = 0
    job = Job(**valid_job_data)

    assert job.salary_min is None
    assert job.salary_max is None


def test_negative_salary_raises(valid_job_data):
    valid_job_data["salary_max"] = -1
    with pytest.raises(ValidationError):
        Job(**valid_job_data)


def test_salary_min_above_max_raises(valid_job_data):
    valid_job_data["salary_min"] = 200_000
    valid_job_data["salary_max"] = 150_000
    with pytest.raises(ValidationError):
        Job(**valid_job_data)


#job: content hash


def test_content_hash_changes_with_description(valid_job_data):
    original = Job(**valid_job_data)
    valid_job_data["description"] = "Build different things."
    changed = Job(**valid_job_data)

    assert original.content_hash != changed.content_hash


def test_content_hash_is_stable(valid_job_data):
    assert Job(**valid_job_data).content_hash == Job(**valid_job_data).content_hash


#job: persistence round trip


def test_round_trip_requires_stripping_computed_fields(valid_job_data):
    job = Job(**valid_job_data)
    dumped = job.model_dump()

    with pytest.raises(ValidationError):
        Job.model_validate(dumped)

    stripped = {k: v for k, v in dumped.items() if k not in {"job_key", "content_hash"}}
    assert Job.model_validate(stripped) == job


# JobAnalysis


def test_job_accepts_analysis(valid_job_data):
    valid_job_data["analysis"] = make_analysis(85)
    job = Job(**valid_job_data)

    assert job.analysis.recommendation is Recommendation.APPLY


@pytest.mark.parametrize("score", [-1, 101, 150])
def test_match_score_out_of_range_raises(score):
    with pytest.raises(ValidationError):
        make_analysis(score)


def test_recommendation_cannot_be_passed_in():
    with pytest.raises(ValidationError):
        JobAnalysis(
            match_score=95,
            strengths=[],
            gaps=[],
            reason="x",
            recommendation="reject",
        )


def test_empty_reason_raises():
    with pytest.raises(ValidationError):
        JobAnalysis(match_score=50, strengths=[], gaps=[], reason="")


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100, Recommendation.PRIORITY_APPLY),
        (90, Recommendation.PRIORITY_APPLY),
        (89, Recommendation.APPLY),
        (80, Recommendation.APPLY),
        (79, Recommendation.REVIEW),
        (70, Recommendation.REVIEW),
        (69, Recommendation.REJECT),
        (0, Recommendation.REJECT),
    ],
)
def test_recommendation_tier_boundaries(score, expected):
    assert make_analysis(score).recommendation is expected