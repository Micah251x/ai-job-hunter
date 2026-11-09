import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from job_hunter.adapters.lever import (
    _location,
    _posted_at,
    _salary,
    _strip_html,
    parse_posting,
    parse_postings,
)
from job_hunter.models.job import JobSource, JobStatus, RemoteStatus

FIXTURE = Path(__file__).parent / "fixtures" / "lever_spotify.json"
SEEN_AT = datetime(2026, 11, 1, tzinfo=timezone.utc)


@pytest.fixture
def postings() -> list[dict]:
    # Fresh copy from disk for every test, so one test can't change another's data.
    return json.loads(FIXTURE.read_text())


# --- whole-response tests (real saved data) ---


def test_parses_every_posting(postings):
    jobs = parse_postings(postings, "Spotify", SEEN_AT)

    assert len(jobs) == len(postings)


def test_maps_identity_fields(postings):
    raw = postings[0]
    job = parse_posting(raw, "Spotify", SEEN_AT)

    assert job.source == JobSource.LEVER
    assert job.company == "spotify"
    assert job.source_job_id == raw["id"]
    assert job.title == raw["text"]
    assert job.url == raw["hostedUrl"]
    assert job.status == JobStatus.QUEUED
    assert job.first_seen_at == SEEN_AT
    assert job.job_key == f"lever#spotify#{raw['id']}"


def test_description_has_no_html(postings):
    raw = postings[0]
    job = parse_posting(raw, "Spotify", SEEN_AT)

    assert "<li>" not in job.description
    assert raw["lists"][0]["text"] in job.description
    assert raw["additionalPlain"].strip() in job.description


def test_bad_posting_is_skipped(postings, caplog):
    bad = dict(postings[0], text="")  # copy with an empty title

    jobs = parse_postings([bad, postings[1]], "Spotify", SEEN_AT)

    assert len(jobs) == 1
    assert jobs[0].source_job_id == postings[1]["id"]
    assert bad["id"] in caplog.text


def test_missing_id_raises(postings):
    # A posting without an id is a broken API response, not a bad job: fail loudly.
    raw = dict(postings[0])
    del raw["id"]

    with pytest.raises(KeyError):
        parse_posting(raw, "Spotify", SEEN_AT)


# --- helper tests (small handmade inputs) ---


@pytest.mark.parametrize(
    "workplace_type, expected",
    [
        ("remote", RemoteStatus.REMOTE),
        ("hybrid", RemoteStatus.HYBRID),
        ("on-site", RemoteStatus.ONSITE),
        ("unspecified", RemoteStatus.UNKNOWN),
        (None, RemoteStatus.UNKNOWN),
    ],
)
def test_remote_status(postings, workplace_type, expected):
    raw = dict(postings[0], workplaceType=workplace_type)
    job = parse_posting(raw, "Spotify", SEEN_AT)

    assert job.remote_status == expected


def test_location_prefers_all_locations():
    posting = {"categories": {"location": "NYC", "allLocations": ["NYC", "Remote"]}}

    assert _location(posting) == "NYC; Remote"


@pytest.mark.parametrize(
    "posting, expected",
    [
        ({"categories": {"location": "NYC"}}, "NYC"),
        ({"categories": {"location": "NYC", "allLocations": []}}, "NYC"),
        ({"categories": {}}, None),
        ({}, None),
    ],
)
def test_location_fallbacks(posting, expected):
    assert _location(posting) == expected


def test_strip_html():
    assert _strip_html("<li>Python &amp; SQL</li><li>AWS</li>") == "Python & SQL\nAWS"


@pytest.mark.parametrize(
    "salary_range, expected",
    [
        (None, (None, None, None)),
        ({}, (None, None, None)),
        (
            {"min": 60, "max": 80, "currency": "USD", "interval": "per-hour-wage"},
            (None, None, None),
        ),
        (
            {"min": 140000, "max": 170000, "currency": "USD", "interval": "per-year-salary"},
            (140000, 170000, "USD"),
        ),
    ],
)
def test_salary(salary_range, expected):
    assert _salary({"salaryRange": salary_range}) == expected


def test_posted_at_converts_milliseconds():
    assert _posted_at(1787345749120) == datetime(
        2026, 8, 21, 20, 55, 49, 120000, tzinfo=timezone.utc
    )


def test_posted_at_none():
    assert _posted_at(None) is None
