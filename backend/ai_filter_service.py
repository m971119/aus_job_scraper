import asyncio
import io
import json
import logging
import pathlib
from pydantic import BaseModel
from openai import AsyncOpenAI
from sqlmodel import Session, select

from ai_config import strip_html
from database import engine
from models import Job

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
_STATE_FILE = pathlib.Path("data/ai_filter_batch.json")

_client = AsyncOpenAI()

_state: dict = {
    "status": "idle",       # idle | uploading | submitted | done | error | cancelled
    "total_jobs": 0,
    "completed": 0,
    "hidden": 0,
    "batch_id": None,
    "error": None,
    "cancel_requested": False,
}

_FILTER_SYSTEM = """\
You are filtering job listings for a software engineer seeking AI, backend, frontend, or full-stack roles.

Decide if this job should be hidden because it clearly does not match.

Hide the job if ANY of these rules apply:
- Leadership-only role: Principal Engineer, Engineering Lead/Manager, VP/Director of Engineering
- Non-software PM: Project Manager or Product Manager for construction, infrastructure, civil, or non-tech domains
- Non-software engineering discipline: Electrical, Civil, Mechanical, or Structural Engineer
- Requires ASP.NET as a core or mandatory skill
- Clearly states that only Permanent Resideent or Citizen can apply
- Clearly outside AI/software/web/data/cloud engineering

If there is reasonable doubt, do NOT hide — only filter obvious mismatches.

Return ONLY a JSON object, no markdown, no other text:
{"hide": <bool>, "reason": "<max 60 chars, empty string if not hiding>"}
"""


class FilterResult(BaseModel):
    hide: bool
    reason: str = ""


def get_status() -> dict:
    return {k: v for k, v in _state.items() if k != "cancel_requested"}


def _reset() -> None:
    _state.update({
        "status": "uploading",
        "total_jobs": 0,
        "completed": 0,
        "hidden": 0,
        "batch_id": None,
        "error": None,
        "cancel_requested": False,
    })


def _save_state(batch_id: str, total_jobs: int) -> None:
    _STATE_FILE.parent.mkdir(exist_ok=True)
    _STATE_FILE.write_text(json.dumps({"batch_id": batch_id, "total_jobs": total_jobs}))


def _load_state() -> dict | None:
    if _STATE_FILE.exists():
        return json.loads(_STATE_FILE.read_text())
    return None


def _build_jsonl(jobs: list[Job], model: str) -> bytes:
    lines = []
    for job in jobs:
        desc = strip_html(job.description or "")
        lines.append(json.dumps({
            "custom_id": f"job-{job.id}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": model,
                "messages": [
                    {"role": "system", "content": _FILTER_SYSTEM},
                    {"role": "user", "content": f"Title: {job.title}\n\nDescription: {desc}"},
                ],
                "max_tokens": 100,
            },
        }))
    return "\n".join(lines).encode()


def _parse_json(content: str) -> dict:
    """Parse JSON from LLM response, stripping any markdown fences."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1]).strip()
    return json.loads(content)


def _apply_results(output_text: str) -> int:
    """Parse batch output and hide matched jobs. Returns count of jobs hidden."""
    hidden = 0
    with Session(engine) as session:
        for line in output_text.strip().split("\n"):
            if not line:
                continue
            row = json.loads(line)
            if row.get("error"):
                logger.warning("Request %s failed: %s", row.get("custom_id"), row["error"])
                continue
            job_id = int(row["custom_id"][4:])  # strip "job-" prefix
            try:
                content = row["response"]["body"]["choices"][0]["message"]["content"]
                result = FilterResult.model_validate(_parse_json(content))
            except Exception as exc:
                logger.warning("Could not parse result for job %s: %s", job_id, exc)
                continue
            if result.hide:
                db_job = session.get(Job, job_id)
                if db_job:
                    db_job.is_hidden = True
                    db_job.hide_reason = (result.reason or "AI filtered")[:60]
                    session.add(db_job)
                    hidden += 1
        session.commit()
    return hidden


async def _poll_and_apply(batch_id: str, total_jobs: int) -> None:
    """Poll an existing batch until completion, then apply results."""
    while True:
        if _state["cancel_requested"]:
            await _client.batches.cancel(batch_id)
            _state["status"] = "cancelled"
            return

        await asyncio.sleep(10)
        batch = await _client.batches.retrieve(batch_id)

        if batch.request_counts:
            _state["completed"] = batch.request_counts.completed

        if batch.status == "completed":
            break
        if batch.status in ("failed", "expired", "cancelled"):
            _state["status"] = "error"
            _state["error"] = f"Batch {batch.status}"
            return

    if batch.output_file_id:
        output = await _client.files.content(batch.output_file_id)
        _state["hidden"] = _apply_results(output.text)
    else:
        logger.warning("Batch completed with no output file — all requests may have failed")
    _state["completed"] = total_jobs
    _state["status"] = "done"


async def recover_if_needed() -> None:
    """On startup, check if a batch was in-flight and resume tracking it."""
    saved = _load_state()
    if not saved:
        return

    batch_id = saved["batch_id"]
    total_jobs = saved.get("total_jobs", 0)
    logger.info("Recovering in-flight batch %s", batch_id)

    try:
        batch = await _client.batches.retrieve(batch_id)
    except Exception as exc:
        logger.warning("Could not retrieve batch %s: %s", batch_id, exc)
        return

    if batch.status == "completed":
        logger.info("Batch %s already completed, applying results", batch_id)
        _state.update({
            "status": "submitted",
            "batch_id": batch_id,
            "total_jobs": total_jobs,
            "completed": total_jobs,
            "hidden": 0,
            "error": None,
            "cancel_requested": False,
        })
        if batch.output_file_id:
            output = await _client.files.content(batch.output_file_id)
            _state["hidden"] = _apply_results(output.text)
        else:
            logger.warning("Batch %s completed with no output file", batch_id)
        _state["status"] = "done"

    elif batch.status in ("validating", "in_progress", "finalizing"):
        logger.info("Batch %s still running, resuming polling", batch_id)
        _state.update({
            "status": "submitted",
            "batch_id": batch_id,
            "total_jobs": total_jobs,
            "completed": batch.request_counts.completed if batch.request_counts else 0,
            "hidden": 0,
            "error": None,
            "cancel_requested": False,
        })
        asyncio.create_task(_poll_and_apply(batch_id, total_jobs))

    else:
        logger.info("Batch %s is in terminal state: %s", batch_id, batch.status)
        _state.update({
            "status": "error",
            "error": f"Batch {batch.status}",
            "batch_id": batch_id,
        })


async def run_filter(model: str = DEFAULT_MODEL) -> None:
    _reset()
    try:
        with Session(engine) as session:
            jobs = list(session.exec(select(Job).where(Job.is_hidden == False)).all())  # noqa: E712

        if not jobs:
            _state["status"] = "done"
            return

        _state["total_jobs"] = len(jobs)

        file_obj = await _client.files.create(
            file=("filter.jsonl", io.BytesIO(_build_jsonl(jobs, model))),
            purpose="batch",
        )

        batch = await _client.batches.create(
            input_file_id=file_obj.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
        )
        _state["batch_id"] = batch.id
        _state["status"] = "submitted"
        _save_state(batch.id, len(jobs))

        await _poll_and_apply(batch.id, len(jobs))

    except Exception as exc:
        logger.exception("AI filter failed: %s", exc)
        _state["status"] = "error"
        _state["error"] = str(exc)
