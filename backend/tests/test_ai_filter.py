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


def _make_output_line(custom_id: str, content: str) -> str:
    return json.dumps({
        "custom_id": custom_id,
        "response": {
            "body": {
                "choices": [{"message": {"content": content}}]
            }
        },
    })


def _make_mock_client(jobs: list[Job], results: dict[int, dict]) -> MagicMock:
    """Build a fully-mocked AsyncOpenAI client.

    results: mapping of job_id → {"hide": bool, "reason": str}
    """
    client = MagicMock()

    # files.create
    file_obj = MagicMock()
    file_obj.id = "file-123"
    client.files.create = AsyncMock(return_value=file_obj)

    # files.content
    output_lines = "\n".join(
        _make_output_line(f"job-{job.id}", json.dumps(results.get(job.id, {"hide": False, "reason": ""})))
        for job in jobs
    )
    file_content = MagicMock()
    file_content.text = output_lines
    client.files.content = AsyncMock(return_value=file_content)

    # batches.create
    batch = MagicMock()
    batch.id = "batch-456"
    batch.status = "completed"
    batch.output_file_id = "file-out-789"
    batch.request_counts = MagicMock(completed=len(jobs))
    client.batches.create = AsyncMock(return_value=batch)

    # batches.retrieve — return completed immediately
    client.batches.retrieve = AsyncMock(return_value=batch)

    return client


# ---- _build_jsonl ----

def test_build_jsonl_includes_full_description():
    job = Job(id=1, seek_url="/j/x", title="Engineer", description="<p>Python dev</p>")
    data = json.loads(ai_filter_service._build_jsonl([job], "gpt-4o-mini").split(b"\n")[0])
    assert data["custom_id"] == "job-1"
    user_msg = data["body"]["messages"][1]["content"]
    assert "Python dev" in user_msg
    assert "<p>" not in user_msg  # HTML stripped


def test_build_jsonl_handles_none_description():
    job = Job(id=2, seek_url="/j/y", title="Dev", description=None)
    data = json.loads(ai_filter_service._build_jsonl([job], "gpt-4o-mini").split(b"\n")[0])
    assert "Description: \n" in data["body"]["messages"][1]["content"] or "Description:" in data["body"]["messages"][1]["content"]


# ---- _parse_json ----

def test_parse_json_plain():
    result = ai_filter_service._parse_json('{"hide": true, "reason": "Civil engineer"}')
    assert result == {"hide": True, "reason": "Civil engineer"}


def test_parse_json_strips_markdown_fences():
    content = '```json\n{"hide": false, "reason": ""}\n```'
    result = ai_filter_service._parse_json(content)
    assert result == {"hide": False, "reason": ""}


# ---- run_filter ----

async def test_run_filter_hides_matching_job():
    job = _make_job("/j/civil-batch", "Civil Engineer", "Build bridges")
    mock_client = _make_mock_client([job], {job.id: {"hide": True, "reason": "Civil engineering role"}})

    with patch("ai_filter_service._client", mock_client):
        await ai_filter_service.run_filter()

    with Session(engine) as s:
        updated = s.get(Job, job.id)
        assert updated.is_hidden is True
        assert updated.hide_reason == "Civil engineering role"

    status = ai_filter_service.get_status()
    assert status["hidden"] >= 1
    assert status["status"] == "done"


async def test_run_filter_keeps_non_matching_job():
    job = _make_job("/j/python-batch", "Senior Python Developer", "FastAPI microservices")
    mock_client = _make_mock_client([job], {job.id: {"hide": False, "reason": ""}})

    with patch("ai_filter_service._client", mock_client):
        await ai_filter_service.run_filter()

    with Session(engine) as s:
        updated = s.get(Job, job.id)
        assert updated.is_hidden is False
        assert updated.hide_reason is None


async def test_run_filter_skips_already_hidden_jobs():
    hidden_job = _make_job("/j/already-hidden-batch", "Electrical Engineer", "High voltage", is_hidden=True)
    visible_job = _make_job("/j/visible-batch", "Python Dev", "Django")
    mock_client = _make_mock_client([visible_job], {visible_job.id: {"hide": False, "reason": ""}})

    with patch("ai_filter_service._client", mock_client):
        await ai_filter_service.run_filter()

    # The JSONL sent to OpenAI should not contain the hidden job
    call_args = mock_client.files.create.call_args
    jsonl_bytes = call_args[1]["file"][1].read()
    ids_sent = [json.loads(line)["custom_id"] for line in jsonl_bytes.decode().strip().split("\n")]
    assert f"job-{hidden_job.id}" not in ids_sent


async def test_run_filter_truncates_reason_to_60_chars():
    job = _make_job("/j/long-reason-batch", "ASP.NET Developer", "ASP.NET MVC required")
    long_reason = "A" * 80
    mock_client = _make_mock_client([job], {job.id: {"hide": True, "reason": long_reason}})

    with patch("ai_filter_service._client", mock_client):
        await ai_filter_service.run_filter()

    with Session(engine) as s:
        updated = s.get(Job, job.id)
        assert updated.hide_reason is not None
        assert len(updated.hide_reason) <= 60


async def test_run_filter_skips_bad_json_line():
    job1 = _make_job("/j/bad-json-batch", "PM Construction", "Build roads")
    job2 = _make_job("/j/good-json-batch", "VP Engineering", "Lead 50 engineers")

    # Manually craft output with one bad line
    bad_content = "NOT VALID JSON {{{"
    bad_response = {"custom_id": f"job-{job1.id}", "response": {"body": {"choices": [{"message": {"content": bad_content}}]}}}
    bad_line = json.dumps(bad_response)
    good_line = _make_output_line(f"job-{job2.id}", json.dumps({"hide": True, "reason": "Leadership role"}))

    file_content = MagicMock()
    file_content.text = f"{bad_line}\n{good_line}"

    mock_client = _make_mock_client([job1, job2], {})
    mock_client.files.content = AsyncMock(return_value=file_content)

    # Also update batch to say 2 jobs
    batch = MagicMock()
    batch.id = "batch-456"
    batch.status = "completed"
    batch.output_file_id = "file-out-789"
    batch.request_counts = MagicMock(completed=2)
    mock_client.batches.create = AsyncMock(return_value=batch)
    mock_client.batches.retrieve = AsyncMock(return_value=batch)

    with patch("ai_filter_service._client", mock_client):
        await ai_filter_service.run_filter()

    with Session(engine) as s:
        updated2 = s.get(Job, job2.id)
        assert updated2.is_hidden is True

    assert ai_filter_service.get_status()["status"] == "done"


async def test_run_filter_cancel():
    job = _make_job("/j/cancel-batch", "Software Engineer", "Python")
    mock_client = _make_mock_client([job], {})

    # Make the batch stay "in_progress" so the cancel path triggers
    in_progress_batch = MagicMock()
    in_progress_batch.id = "batch-cancel"
    in_progress_batch.status = "in_progress"
    in_progress_batch.output_file_id = None
    in_progress_batch.request_counts = MagicMock(completed=0)
    mock_client.batches.create = AsyncMock(return_value=in_progress_batch)

    retrieve_count = 0

    async def mock_retrieve(batch_id):
        nonlocal retrieve_count
        retrieve_count += 1
        # Signal cancel on first retrieve
        ai_filter_service._state["cancel_requested"] = True
        return in_progress_batch

    mock_client.batches.retrieve = mock_retrieve
    mock_client.batches.cancel = AsyncMock()

    with patch("ai_filter_service._client", mock_client), \
         patch("asyncio.sleep", new=AsyncMock()):
        await ai_filter_service.run_filter()

    assert ai_filter_service.get_status()["status"] == "cancelled"
    mock_client.batches.cancel.assert_called_once_with("batch-cancel")


async def test_run_filter_empty_jobs():
    # No visible jobs → status goes to done immediately
    ai_filter_service._state["status"] = "idle"
    mock_client = MagicMock()

    with Session(engine) as s:
        for j in s.exec(ai_filter_service.select(Job).where(Job.is_hidden == False)).all():  # noqa: E712
            j.is_hidden = True
            s.add(j)
        s.commit()

    with patch("ai_filter_service._client", mock_client):
        await ai_filter_service.run_filter()

    assert ai_filter_service.get_status()["status"] == "done"
    mock_client.files.create.assert_not_called()


# ---- Routes ----

from fastapi.testclient import TestClient
from main import app

_test_client = TestClient(app)


def test_filter_status_endpoint_returns_idle():
    ai_filter_service._state["status"] = "idle"
    r = _test_client.get("/api/ai-filter/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "idle"
    assert "total_jobs" in data
    assert "completed" in data
    assert "hidden" in data
    assert "batch_id" in data


def test_filter_run_returns_409_when_active():
    for active_status in ("uploading", "submitted"):
        ai_filter_service._state["status"] = active_status
        r = _test_client.post("/api/ai-filter/run")
        assert r.status_code == 409
    ai_filter_service._state["status"] = "idle"


def test_filter_cancel_sets_flag():
    ai_filter_service._state["cancel_requested"] = False
    r = _test_client.post("/api/ai-filter/cancel")
    assert r.status_code == 200
    assert ai_filter_service._state["cancel_requested"] is True
    ai_filter_service._state["cancel_requested"] = False
