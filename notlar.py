"""Hisse başına kullanıcı notları — JSON dosyasında saklanır."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

NOTLAR_FILE = Path(__file__).parent / "data" / "notlar.json"


def _load() -> Dict[str, dict]:
    if not NOTLAR_FILE.exists():
        return {}
    try:
        return json.loads(NOTLAR_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: Dict[str, dict]) -> None:
    NOTLAR_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTLAR_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_not(sembol: str) -> Optional[dict]:
    return _load().get(sembol.upper().strip())


def get_not_metin(sembol: str) -> str:
    row = get_not(sembol)
    return (row or {}).get("text", "") or ""


def tum_notlar() -> Dict[str, str]:
    return {k: (v.get("text") or "") for k, v in _load().items()}


def kaydet_not(sembol: str, text: str) -> dict:
    sembol = sembol.upper().strip()
    data = _load()
    text = (text or "").strip()
    if not text:
        data.pop(sembol, None)
        _save(data)
        return {"sembol": sembol, "text": "", "updated": None}
    row = {
        "text": text,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    }
    data[sembol] = row
    _save(data)
    return {"sembol": sembol, **row}
