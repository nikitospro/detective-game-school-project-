from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from threading import Lock
from typing import Any


_NON_WORD_RE = re.compile(r"[^a-zA-Zа-яА-Я0-9\s]+")
_MULTISPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    cleaned = _NON_WORD_RE.sub(" ", (text or "").lower())
    return _MULTISPACE_RE.sub(" ", cleaned).strip()


def stable_seed(*parts: object) -> int:
    joined = "||".join(str(part) for part in parts)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def clamp(value: int | float, lower: int | float, upper: int | float) -> int | float:
    return max(lower, min(upper, value))


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    normalized = normalize_text(text)
    return [keyword for keyword in keywords if normalize_text(keyword) in normalized]


def excerpt_history(history: list[dict[str, str]], limit: int = 8) -> list[dict[str, str]]:
    return history[-limit:]


def ensure_session_id(session_obj: Any, key: str = "detective_session_id") -> str:
    session_id = session_obj.get(key)
    if not session_id:
        session_id = uuid.uuid4().hex
        session_obj[key] = session_id
    return session_id


class JsonSessionStore:
    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _path(self, session_id: str) -> Path:
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)
        return self.base_path / f"{safe_id}.json"

    def load(self, session_id: str) -> dict[str, Any] | None:
        file_path = self._path(session_id)
        if not file_path.exists():
            return None

        try:
            with self._lock:
                return json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, session_id: str, data: dict[str, Any]) -> None:
        file_path = self._path(session_id)
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        with self._lock:
            file_path.write_text(payload, encoding="utf-8")


def detective_rank(score: int) -> tuple[str, str]:
    if score >= 90:
        return "Легенда отдела", "Вы раскрываете дело почти без потерь и видите структуру преступления целиком."
    if score >= 75:
        return "Старший следователь", "Уверенное расследование: логика крепкая, улики использованы по делу."
    if score >= 60:
        return "Оперуполномоченный", "Дело раскрыто, но часть связей и деталей осталась на поверхности."
    if score >= 40:
        return "Стажёр отдела", "Есть верные догадки, однако аргументации пока не хватает точности."
    return "Случайный свидетель", "Вы уловили атмосферу дела, но логическая цепочка ещё не собрана."


def reasoning_quality(score: int) -> str:
    if score >= 85:
        return "Отличное"
    if score >= 70:
        return "Сильное"
    if score >= 55:
        return "Уверенное"
    if score >= 40:
        return "Слабое"
    return "Недостаточное"


def suspicion_label(score: int) -> str:
    if score >= 75:
        return "Критическое"
    if score >= 55:
        return "Высокое"
    if score >= 35:
        return "Среднее"
    return "Низкое"


def safe_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip() or fallback
