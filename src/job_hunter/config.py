"""Search preferences, loaded from config/search.yaml."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, field_validator


class SearchConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    titles_include: list[str]
    titles_exclude: list[str]
    skills: list[str]
    hybrid_locations: list[str]
    onsite_locations: list[str]
    search_terms: list[str]
    remote_ok: bool
    min_salary: int | None
    max_age_days: int

    @field_validator(
        "titles_include",
        "titles_exclude",
        "skills",
        "hybrid_locations",
        "onsite_locations",
        "search_terms",
    )
    @classmethod
    def lowercase_lists(cls, value: list[str]) -> list[str]:
        return [item.lower() for item in value]


def load_config(path: Path) -> SearchConfig:
    text = path.read_text()
    data = yaml.safe_load(text)
    config = SearchConfig.model_validate(data)

    return config
