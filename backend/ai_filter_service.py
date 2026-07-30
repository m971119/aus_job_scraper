import json
import logging
import litellm
from sqlmodel import Session, select

from ai_config import strip_html
from database import engine
from models import Job

logger = logging.getLogger(__name__)

BATCH_SIZE = 20
DEFAULT_MODEL = "gpt-4o-mini"

_state: dict = {
    "status": "idle",
    "current_batch": 0,
    "total_batches": 0,
    "evaluated": 0,
    "hidden": 0,
    "error": None,
    "cancel_requested": False,
}

_FILTER_SYSTEM = """\
You are filtering job listings for a software engineer seeking backend, frontend, or full-stack roles.

For each job, decide if it should be hidden because it clearly does not match.

Hide a job if ANY of these rules apply:
- Leadership-only role: Principal Engineer, Engineering Lead/Manager, VP/Director of Engineering
- Non-software PM: Project Manager or Product Manager for construction, infrastructure, civil, or non-tech domains
- Non-software engineering discipline: Electrical, Civil, Mechanical, or Structural Engineer
- Requires ASP.NET as a core or mandatory skill
- Clearly outside software/web/data/cloud engineering

If there is reasonable doubt, do NOT hide — only filter obvious mismatches.

Return ONLY a JSON array, no markdown, no other text. Each element must have exactly these keys:
{"id": <int>, "hide": <bool>, "reason": "<max 60 chars, empty string if hide is false>"}
"""


def get_status() -> dict:
    return {k: v for k, v in _state.items() if k != "cancel_requested"}


def _reset() -> None:
    _state.update({
        "status": "running",
        "current_batch": 0,
        "total_batches": 0,
        "evaluated": 0,
        "hidden": 0,
        "error": None,
        "cancel_requested": False,
    })


def _build_batch_payload(jobs: list[Job]) -> list[dict]:
    return [
        {"id": job.id, "title": job.title, "description": strip_html(job.description or "")[:500]}
        for job in jobs
    ]


def _parse_response(content: str) -> list[dict]:
    """Extract JSON array from LLM response, stripping any markdown fences."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1]).strip()
    return json.loads(content)


async def run_filter(model: str = DEFAULT_MODEL) -> None:
    _reset()
    try:
        with Session(engine) as session:
            jobs = list(session.exec(select(Job).where(Job.is_hidden == False)).all())  # noqa: E712

        if not jobs:
            _state["status"] = "done"
            return

        batches = [jobs[i:i + BATCH_SIZE] for i in range(0, len(jobs), BATCH_SIZE)]
        _state["total_batches"] = len(batches)

        for batch_idx, batch in enumerate(batches):
            if _state["cancel_requested"]:
                _state["status"] = "cancelled"
                return

            _state["current_batch"] = batch_idx + 1
            payload = _build_batch_payload(batch)

            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=[
                        {"role": "system", "content": _FILTER_SYSTEM},
                        {"role": "user", "content": json.dumps(payload)},
                    ],
                )
                content = response.choices[0].message.content
            except Exception as exc:
                logger.error("Batch %d LLM call failed: %s", batch_idx + 1, exc)
                _state["status"] = "error"
                _state["error"] = str(exc)
                return

            try:
                decisions = _parse_response(content)
            except Exception as exc:
                logger.error("Batch %d JSON parse failed: %s", batch_idx + 1, exc)
                _state["evaluated"] += len(batch)
                continue

            hide_map = {d["id"]: d for d in decisions if d.get("hide")}

            with Session(engine) as session:
                for job in batch:
                    if job.id in hide_map:
                        db_job = session.get(Job, job.id)
                        if db_job:
                            db_job.is_hidden = True
                            db_job.hide_reason = hide_map[job.id].get("reason", "AI filtered")[:60]
                            session.add(db_job)
                            _state["hidden"] += 1
                session.commit()

            _state["evaluated"] += len(batch)

        _state["status"] = "done"

    except Exception as exc:
        logger.exception("AI filter failed: %s", exc)
        _state["status"] = "error"
        _state["error"] = str(exc)
