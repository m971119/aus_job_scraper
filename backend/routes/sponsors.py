from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

_DATA_FILE = Path(__file__).parent.parent / "data" / "sponsors.txt"
_sponsors: list[str] = [
    line.strip()
    for line in _DATA_FILE.read_text(encoding="utf-8").splitlines()
    if line.strip()
]


@router.get("/sponsors")
def list_sponsors():
    return {"sponsors": _sponsors}
