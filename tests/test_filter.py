from datetime import datetime, timedelta, timezone

import pytest

from job_hunter.config import SearchConfig
from job_hunter.filter import filter_job
from job_hunter.models.job import Job, JobSource, JobStatus, RemoteStatus


NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


@pytest.fixture
def config() -> SearchConfig:
    return SearchConfig(
        titles_include=["software engineer", "php"],
        titles_exclude=["sales", "intern"],
        skills=["aws"],
        remote_ok=True,
        hybrid_locations=["austin"],
        onsite_locations=[],
        min_salary=150000,
        max_age_days=30,
        search_terms=["cloud engineer"],
    )


def make_job(**overrides) -> Job:
    fields = {
        "source": JobSource.LEVER,
        "company": "ElevelLabs",
        "source_job_id": "2a55dc9-x326-551b-oa4e-c3245ls5b75h",
        "title": "software engineer",
        "url": "https://jobs.lever.co/elevenlabs/2a55dc9-x326-551b-oa4e-c3245ls5b75h",
        "description": "Build and maintain web applications using PHP, JavaScript, and MySQL.",
        "status": JobStatus.QUEUED,
        "first_seen_at": NOW,
        "remote_status": RemoteStatus.REMOTE,
    }

    fields.update(overrides)

    return Job(**fields)


def test_rejects_excluded_title(config):
    job = make_job(title="Sales Engineer")
    result = filter_job(job, config, NOW)

    assert result == "title excluded: sales"


def test_whole_word_only(config):
    job = make_job(title="Internal Tools Software Engineer")
    result = filter_job(job, config, NOW)

    assert result is None


def test_rejects_unmatched_title(config):
    job = make_job(title="Graphic Designer")
    result = filter_job(job, config, NOW)

    assert result == "title not a match"


def test_keeps_hybrid_in_commute_area(config):
    job = make_job(remote_status=RemoteStatus.HYBRID, location_raw="Austin TX")
    result = filter_job(job, config, NOW)

    assert result is None


def test_rejects_hybrid_outside_area(config):
    job = make_job(remote_status=RemoteStatus.HYBRID, location_raw="Chicago IL")
    result = filter_job(job, config, NOW)

    assert result == "hybrid outside commute area"


def test_keeps_unknown_remote_status(config):
    job = make_job(remote_status=RemoteStatus.UNKNOWN)
    result = filter_job(job, config, NOW)

    assert result is None


def test_rejects_low_salary(config):
    job = make_job(salary_max=149999)
    result = filter_job(job, config, NOW)

    assert result == "salary below minimum"


def test_rejects_old_posting(config):
    job = make_job(posted_at=NOW - timedelta(days=45))
    result = filter_job(job, config, NOW)

    assert result == "posting too old"


def test_keeps_good_job(config):
    job = make_job()
    result = filter_job(job, config, NOW)

    assert result is None

