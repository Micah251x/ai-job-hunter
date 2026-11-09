"""Translate Lever's postings API response into Job models.

API: https://api.lever.co/v0/postings/{company}?mode=json
Field-by-field decisions are in docs/field-mapping.md.

This module only translates. Fetching over HTTP happens elsewhere, so these
functions can be tested with saved JSON and no network.
"""

import html
import logging
import re
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from job_hunter.models.job import Job, JobSource, JobStatus, RemoteStatus

logger = logging.getLogger(__name__)

# Lever's workplaceType -> RemoteStatus. Anything not listed becomes UNKNOWN.
WORKPLACE_TYPES: dict[str, RemoteStatus] = {
    "remote": RemoteStatus.REMOTE,
    "on-site": RemoteStatus.ONSITE,
    "hybrid": RemoteStatus.HYBRID,
}


def parse_postings(
    postings: list[dict[str, Any]], company: str, seen_at: datetime
) -> list[Job]:
    """Translate a whole API response. One bad posting doesn't sink the rest."""
    jobs = []
    for posting in postings:
        try:
            parsed_posting = parse_posting(posting, company, seen_at)
            jobs.append(parsed_posting)
        except ValidationError:
            logger.warning("Skipping invalid Lever posting %s", posting.get("id"))
    return jobs


def parse_posting(posting: dict[str, Any], company: str, seen_at: datetime) -> Job:
    """Translate one Lever posting into a Job. Raises ValidationError if invalid."""
    salary_min, salary_max, salary_currency = _salary(posting)
    return Job(
        source=JobSource.LEVER,
        company=company,
        source_job_id=posting["id"],
        title=posting["text"],
        url=posting["hostedUrl"],
        location_raw=_location(posting),
        remote_status=WORKPLACE_TYPES.get(
            posting.get("workplaceType"),
            RemoteStatus.UNKNOWN,
        ),
        description=_description(posting),
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        posted_at=_posted_at(posting.get("createdAt")),
        status=JobStatus.QUEUED,
        first_seen_at=seen_at,
    )


def _location(posting: dict[str, Any]) -> str | None:
    categories = posting.get("categories", {})
    all_locations = categories.get("allLocations", [])

    if all_locations:
        return "; ".join(all_locations)

    return categories.get("location")


def _description(posting: dict[str, Any]) -> str:
    pieces = []
    description_plain = posting.get("descriptionPlain")

    if description_plain:
        pieces.append(description_plain)

    lists = posting.get("lists", [])

    for section in lists:
        heading = section.get("text")
        content = section.get("content")

        if heading:
            pieces.append(heading)

        if content:
            pieces.append(_strip_html(content))

    additional_plain = posting.get("additionalPlain")

    if additional_plain:
        pieces.append(additional_plain)

    return "\n\n".join(pieces)


def _strip_html(text: str) -> str:
    text = text.replace("</li>", "\n")
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)

    return text.strip()


def _salary(posting: dict[str, Any]) -> tuple[int | None, int | None, str | None]:
    """Return (min, max, currency). All None when Lever doesn't publish a salary."""
    salary = posting.get("salaryRange")

    if not salary:
        return None, None, None

    interval = salary.get("interval")

    if interval != "per-year-salary":
        return None, None, None

    salary_min = salary.get("min")
    salary_max = salary.get("max")
    salary_currency = salary.get("currency")

    return salary_min, salary_max, salary_currency


def _posted_at(created_at: int | None) -> datetime | None:
    if created_at is None:
        return None

    total_seconds = created_at / 1000

    return datetime.fromtimestamp(total_seconds, tz=timezone.utc)
