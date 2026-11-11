"""Decide whether a job matches the search config."""

import re
from datetime import timedelta, datetime

from job_hunter.config import SearchConfig
from job_hunter.models.job import Job, RemoteStatus


def _find_word(text: str, words: list[str]) -> str | None:
    lowercase_text = text.lower()

    for word in words:
        word_check = re.search(rf"\b{re.escape(word)}\b", lowercase_text)

        if word_check:
            return word

    return None


def filter_job(job: Job, config: SearchConfig, now: datetime) -> str | None:
    excluded = _find_word(job.title, config.titles_exclude)

    if excluded:
        return f"title excluded: {excluded}"

    if not _find_word(job.title, config.titles_include):
        return "title not a match"

    location = job.location_raw or ""

    if job.remote_status == RemoteStatus.REMOTE and not config.remote_ok:
        return "remote not wanted"

    if (
        job.remote_status == RemoteStatus.HYBRID
        and not _find_word(location, config.hybrid_locations)
    ):
        return "hybrid outside commute area"

    if (
        job.remote_status == RemoteStatus.ONSITE
        and not _find_word(location, config.onsite_locations)
    ):
        return "onsite outside commute area"

    if (
        job.salary_max is not None
        and config.min_salary is not None
        and job.salary_max < config.min_salary
    ):
        return "salary below minimum"

    if (
        job.posted_at is not None
        and now - job.posted_at > timedelta(days=config.max_age_days)
    ):
        return "posting too old"

    return None