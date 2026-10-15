"""Translate between Job models and DynamoDB items.

The code that actually talks to DynamoDB (later) calls these"""

from typing import Any
from job_hunter.models.job import Job

# Derived by the model. Stored so DynamoDB can key and compare on them, but
# Job won't accept them back as input (extra="forbid").
COMPUTED_FIELDS = frozenset({"job_key", "content_hash"})

# copied out of the nested analysis map because a GSI key must be top-level.
FLATTENED_FIELDS = frozenset({"match_score"})


def to_item(job: Job) -> dict[str, Any]:
    # mode="json": enums -> plain strings, datetimes -> ISO-8601 strings.
    # exclude_none: absent, not NULL. TTL and GSI keys need the attribute missing
    item = job.model_dump(mode="json", exclude_none=True)
    if job.analysis is not None:
        item["match_score"] = job.analysis.match_score
    return item


def from_item(item: dict[str, Any]) -> Job:
    # Build new dicts rather than deleting keys, so the caller's item is untouched
    data = {
        key: value
        for key, value in item.items()
        if key not in COMPUTED_FIELDS | FLATTENED_FIELDS
    }
    if "analysis" in data:
        data["analysis"] = {
            key: value
            for key, value in data["analysis"].items()
            if key != "recommendation"
        }
    return Job.model_validate(data)
