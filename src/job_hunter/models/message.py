"""The SQS message that tells the worker which job to analyze.

Claim check: the message carries only the key. The job itself lives in 
DynamoDB, which stays the single source of truth.
"""

from pydantic import BaseModel, ConfigDict, Field


class JobMessage(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    job_key: str = Field(min_length=1)


def to_body(message: JobMessage) -> str:
    return message.model_dump_json()


def from_body(body: str) -> JobMessage:
    return JobMessage.model_validate_json(body)