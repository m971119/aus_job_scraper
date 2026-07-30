import json
from unittest.mock import AsyncMock, MagicMock, patch

from models import Job
from database import engine
from sqlmodel import Session

import ai_filter_service


def _make_job(seek_url: str, title: str, description: str = "", is_hidden: bool = False) -> Job:
    with Session(engine) as s:
        job = Job(
            seek_url=seek_url,
            seek_urls="[]",
            title=title,
            description=description,
            listed_dates="[]",
            is_hidden=is_hidden,
        )
        s.add(job)
        s.commit()
        s.refresh(job)
        return job


def test_parse_response_plain_json():
    content = '[{"id": 1, "hide": true, "reason": "Civil engineer"}]'
    result = ai_filter_service._parse_response(content)
    assert result == [{"id": 1, "hide": True, "reason": "Civil engineer"}]


def test_parse_response_strips_markdown_fences():
    content = '```json\n[{"id": 2, "hide": false, "reason": ""}]\n```'
    result = ai_filter_service._parse_response(content)
    assert result == [{"id": 2, "hide": False, "reason": ""}]


def test_build_batch_payload_truncates_description():
    job = Job(id=99, seek_url="/j/x", title="Engineer", description="x" * 600)
    payload = ai_filter_service._build_batch_payload([job])
    assert len(payload[0]["description"]) == 500


def test_build_batch_payload_handles_none_description():
    job = Job(id=98, seek_url="/j/y", title="Dev", description=None)
    payload = ai_filter_service._build_batch_payload([job])
    assert payload[0]["description"] == ""


async def test_run_filter_hides_matching_job():
    job = _make_job("/j/civil-test", "Civil Engineer", "Build bridges and roads")

    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps([
        {"id": job.id, "hide": True, "reason": "Civil engineering role"}
    ])

    with patch("ai_filter_service.litellm.acompletion", new=AsyncMock(return_value=mock_resp)):
        await ai_filter_service.run_filter()

    with Session(engine) as s:
        updated = s.get(Job, job.id)
        assert updated.is_hidden is True
        assert updated.hide_reason == "Civil engineering role"

    status = ai_filter_service.get_status()
    assert status["hidden"] >= 1
    assert status["status"] == "done"


async def test_run_filter_keeps_non_matching_job():
    job = _make_job("/j/python-dev", "Senior Python Developer", "FastAPI microservices")

    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps([
        {"id": job.id, "hide": False, "reason": ""}
    ])

    with patch("ai_filter_service.litellm.acompletion", new=AsyncMock(return_value=mock_resp)):
        await ai_filter_service.run_filter()

    with Session(engine) as s:
        updated = s.get(Job, job.id)
        assert updated.is_hidden is False
        assert updated.hide_reason is None


async def test_run_filter_skips_already_hidden_jobs():
    job = _make_job("/j/already-hidden", "Electrical Engineer", "High voltage", is_hidden=True)

    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps([])

    with patch("ai_filter_service.litellm.acompletion", new=AsyncMock(return_value=mock_resp)) as mock_llm:
        await ai_filter_service.run_filter()

    # Already-hidden job should not appear in any batch sent to the LLM
    all_ids_sent = []
    for call in mock_llm.call_args_list:
        user_msg = call.kwargs["messages"][-1]["content"]
        batch = json.loads(user_msg)
        all_ids_sent.extend(item["id"] for item in batch)
    assert job.id not in all_ids_sent


async def test_run_filter_truncates_reason_to_60_chars():
    job = _make_job("/j/asp-net", "ASP.NET Developer", "ASP.NET MVC required")

    long_reason = "A" * 80
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps([
        {"id": job.id, "hide": True, "reason": long_reason}
    ])

    with patch("ai_filter_service.litellm.acompletion", new=AsyncMock(return_value=mock_resp)):
        await ai_filter_service.run_filter()

    with Session(engine) as s:
        updated = s.get(Job, job.id)
        assert updated.hide_reason is not None
        assert len(updated.hide_reason) <= 60


async def test_run_filter_continues_after_bad_json_batch():
    job1 = _make_job("/j/bad-json", "PM Construction", "Build roads")
    job2 = _make_job("/j/good-json", "VP Engineering", "Lead 50 engineers")

    call_count = 0

    async def mock_llm(**kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        if call_count == 1:
            mock_resp.choices[0].message.content = "NOT VALID JSON {{{"
        else:
            mock_resp.choices[0].message.content = json.dumps([
                {"id": job2.id, "hide": True, "reason": "Leadership role"}
            ])
        return mock_resp

    with patch("ai_filter_service.litellm.acompletion", new=mock_llm), \
         patch("ai_filter_service.BATCH_SIZE", 1):
        await ai_filter_service.run_filter()

    with Session(engine) as s:
        updated2 = s.get(Job, job2.id)
        assert updated2.is_hidden is True

    assert ai_filter_service.get_status()["status"] == "done"


async def test_run_filter_cancel():
    # Two jobs, BATCH_SIZE=1 so there are two batches.
    # After the first batch the mock sets cancel_requested so the second batch is skipped.
    _make_job("/j/cancel-a", "Software Engineer A", "Python")
    _make_job("/j/cancel-b", "Software Engineer B", "JavaScript")

    call_count = 0

    async def mock_llm(**kwargs):
        nonlocal call_count
        call_count += 1
        ai_filter_service._state["cancel_requested"] = True  # signal cancel after first batch
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps([])
        return mock_resp

    with patch("ai_filter_service.litellm.acompletion", new=mock_llm), \
         patch("ai_filter_service.BATCH_SIZE", 1):
        await ai_filter_service.run_filter()

    assert call_count == 1  # second batch never ran
    assert ai_filter_service.get_status()["status"] == "cancelled"
