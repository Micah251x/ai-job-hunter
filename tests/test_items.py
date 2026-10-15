import copy
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from job_hunter.models.job import Job, JobAnalysis
from job_hunter.persistence.items import from_item, to_item

@pytest.fixture
def job_data() -> dict:
    return {
        "source": "lever",
        "company": "minted",
        "source_job_id": "4f2a",
        "title": "Senior Software Engineer",
        "url": "https://jobs.lever.co/minted/4f2a",
        "description": "Build things.",
        "status": "queued",
        "first_seen_at": datetime(2026, 10, 13, tzinfo=timezone.utc),
    }


@pytest.fixture
def job(job_data) -> Job:
    return Job(**job_data)


@pytest.fixture
def analyzed_job(job_data) -> Job:
    # Built fresh rather than with model_copy(update=...), which skips validation
    job_data["status"] = "analyzed"
    job_data["analysis"] = JobAnalysis(
        match_score=85,
        strengths=["Python"],
        gaps=["Go"],
        reason="Solid backend fit.",
    )
    return Job(**job_data)


# to_item


def test_to_item_includes_computed_fields(job):
    item = to_item(job)

    assert item["job_key"] == "lever#minted#4f2a"
    assert item["content_hash"] == job.content_hash


def test_to_item_omits_none_fields(job):
    item = to_item(job)

    assert "salary_min" not in item
    assert "expires_at" not in item
    assert "analysis" not in item


def test_to_item_uses_plain_strings(job):
    item = to_item(job)

    assert type(item["status"]) is str
    assert item["first_seen_at"] == "2026-10-13T00:00:00Z"


def test_to_item_flattens_match_score(analyzed_job):
    item = to_item(analyzed_job)

    assert item["match_score"] == 85
    assert item["analysis"]["recommendation"] == "apply"


def test_to_item_without_analysis_has_no_match_score(job):
    assert "match_score" not in to_item(job)


# from_item


def test_round_trip_without_analysis(job):
    assert from_item(to_item(job)) == job


def test_round_trip_with_analysis(analyzed_job):
    assert from_item(to_item(analyzed_job)) == analyzed_job


def test_from_item_does_not_mutate_input(analyzed_job):
    item = to_item(analyzed_job)
    original = copy.deepcopy(item)

    from_item(item)

    assert item == original


def test_from_item_accepts_decimals(analyzed_job):
    # boto3 returns every DynamoDB number as Decimal.
    item = to_item(analyzed_job)
    item["salary_max"] = Decimal("150000")
    item["match_score"] = Decimal("85")
    item["analysis"]["match_score"] = Decimal("85")

    restored = from_item(item)

    assert restored.salary_max == 150000
    assert restored.analysis.match_score == 85