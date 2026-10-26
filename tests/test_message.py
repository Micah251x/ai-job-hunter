import pytest
from pydantic import ValidationError

from job_hunter.models.message import JobMessage, from_body, to_body


@pytest.fixture
def message() -> JobMessage:
    return JobMessage(job_key="lever#minted#4f2a")


def test_round_trip(message):
    body = to_body(message)
    restored = from_body(body)

    assert message == restored


def test_to_body_exact_json(message):
    assert to_body(message) == '{"job_key":"lever#minted#4f2a"}'



def test_body_not_json_raises():
    with pytest.raises(ValidationError):
        from_body("not json")



def test_body_missing_job_key_raises():
    with pytest.raises(ValidationError):
        from_body("{}")



def test_body_extra_field_raises():
    with pytest.raises(ValidationError):
        from_body('{"job_key":"lever#minted#4f2a", "field":"key"}')



def test_empty_job_key_raises():
    with pytest.raises(ValidationError):
        from_body('{"job_key":""}')



def test_message_is_frozen(message):
    with pytest.raises(ValidationError) as exc_info:
        message.job_key = "something"

    assert exc_info.value.errors()[0]["type"] == "frozen_instance"
