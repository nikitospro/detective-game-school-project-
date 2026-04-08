from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass
from typing import Any

from cases import CaseFile, Clue, Contradiction, Suspect
from utils import stable_seed


DEFAULT_HOST = os.getenv("OLLAMA_HOST")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
DEFAULT_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "20"))


@dataclass(frozen=True)
class LLMResponse:
    text: str
    ok: bool
    source: str
    model: str
    error: str | None = None


class OllamaClient:
    def __init__(
        self,
        host: str | None = DEFAULT_HOST,
        default_model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host.strip() if isinstance(host, str) and host.strip() else None
        self.default_model = default_model
        self.timeout = timeout
        self._client: Any = None

    def _post_generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        seed: int,
        model_name: str | None,
        max_tokens: int,
        max_chars: int | None,
        fallback_text: str,
    ) -> LLMResponse:
        model = (model_name or self.default_model).strip() or self.default_model
        think_setting = self._thinking_mode(model)
        options = {
            "temperature": 0.2,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "num_predict": max_tokens,
            "seed": seed,
        }
        generate_payload = {
            "model": model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": options,
            "think": think_setting,
        }
        chat_payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": options,
            "think": think_setting,
        }

        try:
            chat_report = "не вызывался"
            generate_report = "не вызывался"
            chat_data: Any = None
            generate_data: Any = None

            try:
                chat_data = self._request_json("/api/chat", chat_payload)
                chat_text = self._clean_text(self._extract_text(chat_data), max_chars=max_chars)
                if chat_text:
                    return LLMResponse(text=chat_text, ok=True, source="ollama", model=model)
                if self._needs_nonthinking_retry(chat_data):
                    retry_chat_payload = dict(chat_payload)
                    retry_chat_payload["think"] = False
                    chat_data = self._request_json("/api/chat", retry_chat_payload)
                    chat_text = self._clean_text(self._extract_text(chat_data), max_chars=max_chars)
                    if chat_text:
                        return LLMResponse(text=chat_text, ok=True, source="ollama", model=model)
                chat_report = f"пусто ({self._diagnostics(chat_data)})"
            except Exception as exc:
                chat_report = f"ошибка ({exc})"

            try:
                generate_data = self._request_json("/api/generate", generate_payload)
                generate_text = self._clean_text(self._extract_text(generate_data), max_chars=max_chars)
                if generate_text:
                    return LLMResponse(text=generate_text, ok=True, source="ollama", model=model)
                if self._needs_nonthinking_retry(generate_data):
                    retry_generate_payload = dict(generate_payload)
                    retry_generate_payload["think"] = False
                    generate_data = self._request_json("/api/generate", retry_generate_payload)
                    generate_text = self._clean_text(self._extract_text(generate_data), max_chars=max_chars)
                    if generate_text:
                        return LLMResponse(text=generate_text, ok=True, source="ollama", model=model)
                generate_report = f"пусто ({self._diagnostics(generate_data)})"
            except Exception as exc:
                generate_report = f"ошибка ({exc})"

            rescue_text = self._rescue_visible_text(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                max_chars=max_chars,
                seed=seed,
                chat_data=chat_data,
                generate_data=generate_data,
            )
            if rescue_text:
                return LLMResponse(text=rescue_text, ok=True, source="ollama", model=model)

            raise ValueError(
                "Пустой ответ модели. "
                f"/api/chat: {chat_report}; "
                f"/api/generate: {generate_report}"
            )
        except Exception as exc:
            return LLMResponse(
                text=fallback_text,
                ok=False,
                source="fallback",
                model=model,
                error=str(exc),
            )

    @classmethod
    def _clean_text(cls, text: str, max_chars: int | None = None) -> str:
        cleaned = "\n".join(line.strip() for line in str(text).splitlines() if line.strip())
        if not max_chars or len(cleaned) <= max_chars:
            return cleaned
        return cls._soft_truncate(cleaned, max_chars)

    @staticmethod
    def _soft_truncate(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text

        cutoff = text[:max_chars]
        sentence_break = max(cutoff.rfind(". "), cutoff.rfind("! "), cutoff.rfind("? "), cutoff.rfind("\n"))
        if sentence_break >= int(max_chars * 0.65):
            return cutoff[: sentence_break + 1].rstrip() + "..."

        word_break = cutoff.rfind(" ")
        if word_break >= int(max_chars * 0.8):
            return cutoff[:word_break].rstrip() + "..."

        return cutoff.rstrip() + "..."

    def _request_json(self, endpoint: str, payload: dict[str, Any]) -> Any:
        client = self._get_client()
        if endpoint == "/api/chat":
            response = client.chat(
                model=payload["model"],
                messages=payload["messages"],
                stream=False,
                options=payload.get("options"),
                think=payload.get("think"),
            )
            return self._normalize_response(response)

        if endpoint == "/api/generate":
            response = client.generate(
                model=payload["model"],
                prompt=payload["prompt"],
                system=payload.get("system"),
                stream=False,
                options=payload.get("options"),
                think=payload.get("think"),
            )
            return self._normalize_response(response)

        raise ValueError(f"Неподдерживаемый endpoint: {endpoint}")

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from ollama import Client
        except ImportError as exc:
            raise RuntimeError(
                "Python-пакет 'ollama' не установлен. Установите зависимости из requirements.txt."
            ) from exc

        client_kwargs: dict[str, Any] = {"timeout": self.timeout}
        if self.host:
            client_kwargs["host"] = self.host
        self._client = Client(**client_kwargs)
        return self._client

    @staticmethod
    def _normalize_response(response: Any) -> Any:
        if isinstance(response, dict):
            return response

        if hasattr(response, "model_dump"):
            return response.model_dump(exclude_none=True)

        if hasattr(response, "dict"):
            return response.dict(exclude_none=True)

        try:
            return dict(response)
        except Exception:
            return response

    def _rescue_visible_text(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        max_chars: int | None,
        seed: int,
        chat_data: Any,
        generate_data: Any,
    ) -> str:
        if not any(self._has_generation_activity(payload) for payload in (chat_data, generate_data)):
            return ""

        rescue_system = (
            "Отвечай только по-русски. "
            "Выведи только финальный видимый ответ для пользователя. "
            "Запрещено скрытое рассуждение, пустой вывод, только пробелы, служебные токены и молчание. "
            "Начни сразу с содержательного текста."
        )
        rescue_user = (
            "Сохрани факты и ограничения исходной задачи.\n\n"
            f"Исходные правила:\n{system_prompt}\n\n"
            f"Исходный запрос:\n{user_prompt}\n\n"
            "Верни только итоговый ответ без объяснения внутренних шагов."
        )
        rescue_payload = {
            "model": model,
            "stream": False,
            "think": False,
            "system": rescue_system,
            "prompt": rescue_user,
            "options": {
                "temperature": 0,
                "top_p": 0.9,
                "repeat_penalty": 1.05,
                "num_predict": max_tokens,
                "seed": seed,
            },
        }

        try:
            rescue_data = self._request_json("/api/generate", rescue_payload)
            return self._clean_text(self._extract_text(rescue_data), max_chars=max_chars)
        except Exception:
            return ""

    @classmethod
    def _extract_text(cls, payload: Any) -> str:
        if isinstance(payload, list):
            parts = [cls._extract_text(item) for item in payload]
            return "\n".join(part for part in parts if part)

        if not isinstance(payload, dict):
            return str(payload or "")

        response_text = payload.get("response")
        if isinstance(response_text, str) and response_text.strip():
            return response_text

        message = payload.get("message")
        if isinstance(message, dict):
            message_text = message.get("content")
            if isinstance(message_text, str) and message_text.strip():
                return message_text

        content_text = payload.get("content")
        if isinstance(content_text, str) and content_text.strip():
            return content_text

        messages = payload.get("messages")
        if isinstance(messages, list):
            parts = []
            for item in messages:
                if isinstance(item, dict):
                    content = item.get("content")
                    if isinstance(content, str) and content.strip():
                        parts.append(content)
            if parts:
                return "\n".join(parts)

        return ""

    @staticmethod
    def _thinking_mode(model_name: str) -> bool | str:
        normalized = model_name.lower()
        if "gpt-oss" in normalized:
            return "low"
        return False

    @classmethod
    def _needs_nonthinking_retry(cls, payload: Any) -> bool:
        if isinstance(payload, list):
            if not payload:
                return False
            return any(cls._needs_nonthinking_retry(item) for item in payload)

        if not isinstance(payload, dict):
            return False

        done_reason = str(payload.get("done_reason", "")).lower()
        if done_reason != "length":
            return False

        has_final_text = bool(cls._extract_text(payload).strip())
        if has_final_text:
            return False

        thinking_text = payload.get("thinking")
        if isinstance(thinking_text, str) and thinking_text.strip():
            return True

        message = payload.get("message")
        if isinstance(message, dict):
            message_thinking = message.get("thinking")
            if isinstance(message_thinking, str) and message_thinking.strip():
                return True

        return False

    @classmethod
    def _has_generation_activity(cls, payload: Any) -> bool:
        if isinstance(payload, list):
            return any(cls._has_generation_activity(item) for item in payload)

        if not isinstance(payload, dict):
            return False

        eval_count = payload.get("eval_count")
        if isinstance(eval_count, int) and eval_count > 0:
            return True

        done_reason = str(payload.get("done_reason", "")).lower()
        return done_reason in {"stop", "length"}

    @classmethod
    def _diagnostics(cls, payload: Any) -> str:
        if isinstance(payload, list):
            if not payload:
                return "пустой список чанков"
            last_item = payload[-1] if isinstance(payload[-1], dict) else {}
            chunk_count = len(payload)
            return (
                f"chunks={chunk_count}, "
                f"done_reason={last_item.get('done_reason', 'n/a')}, "
                f"eval_count={last_item.get('eval_count', 'n/a')}"
            )

        if isinstance(payload, dict):
            return (
                f"done_reason={payload.get('done_reason', 'n/a')}, "
                f"eval_count={payload.get('eval_count', 'n/a')}, "
                f"keys={','.join(sorted(payload.keys()))}"
            )

        return f"payload_type={type(payload).__name__}"

    @staticmethod
    def _unsafe_dialogue(text: str) -> bool:
        lowered = text.lower()
        banned_fragments = [
            "я убил",
            "я убила",
            "это сделал я",
            "это сделала я",
            "я виновен",
            "я виновна",
            "я подменил",
            "я подменила",
            "я отключил камеру",
            "я отключила камеру",
        ]
        return any(fragment in lowered for fragment in banned_fragments)

    def generate_dialogue(
        self,
        *,
        case_file: CaseFile,
        suspect: Suspect,
        question: str,
        history: list[dict[str, str]],
        visible_clues: list[Clue],
        contradictions: list[Contradiction],
        model_name: str | None = None,
    ) -> LLMResponse:
        fallback_text = self._fallback_dialogue(
            case_file=case_file,
            suspect=suspect,
            question=question,
            visible_clues=visible_clues,
        )
        system_prompt = textwrap.dedent(
            f"""
            Ты играешь роль подозреваемого в детективной учебной игре.
            Отвечай только по-русски.
            Факты дела фиксированы и менять их нельзя.
            Нельзя придумывать новые улики, новых людей, новые комнаты, новые события или новые мотивы.
            Ты знаешь только собственные действия, собственные секреты, публичные факты и то, что мог увидеть лично.
            Не раскрывай убийцу и не признавайся в убийстве напрямую, даже если ты виновен.
            Разрешены уклончивость, раздражение, неполные ответы и небольшие несостыковки.
            Не переходи на роль рассказчика или следователя.
            Держи ответ в пределах 2-5 предложений.
            Манера речи: {suspect.speaking_style}
            Личная стратегия: {suspect.private_strategy}
            Уровень стресса: {suspect.stress_level}/100
            """
        ).strip()
        user_prompt = textwrap.dedent(
            f"""
            Дело: {case_file.title}
            Локация: {case_file.location}
            Жертва: {case_file.victim_name}

            Персонаж:
            - Имя: {suspect.name}
            - Роль: {suspect.role}
            - Краткая биография: {suspect.short_backstory}
            - Черты: {", ".join(suspect.personality_traits)}
            - Отношение к жертве: {suspect.relationship_to_victim}
            - Мотив: {suspect.motive}
            - Алиби: {suspect.alibi}
            - Известные факты: {"; ".join(suspect.known_facts)}
            - Тайные факты: {"; ".join(suspect.hidden_secrets)}
            - Болевые точки: {", ".join(suspect.pressure_points)}

            Уже вскрытые следователем улики:
            {"; ".join(f"{clue.title}: {clue.interpretation}" for clue in visible_clues) or "Следователь пока не озвучил конкретные улики."}

            Уже заметные противоречия:
            {"; ".join(item.title for item in contradictions) or "Явных противоречий пока нет."}

            Недавний контекст допроса:
            {"; ".join(f"{entry['role']}: {entry['text']}" for entry in history) or "Это начало разговора."}

            Вопрос детектива:
            {question}

            Ответь в образе {suspect.name}. Не цитируй правила.
            """
        ).strip()

        result = self._post_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            seed=stable_seed(case_file.case_id, suspect.suspect_id, question, len(history)),
            model_name=model_name,
            max_tokens=220,
            max_chars=1000,
            fallback_text=fallback_text,
        )

        if self._unsafe_dialogue(result.text):
            return LLMResponse(
                text=fallback_text,
                ok=False,
                source="fallback",
                model=result.model,
                error="Ответ модели нарушил сюжетные ограничения и был заменён резервным.",
            )
        return result

    def describe_clue(
        self,
        *,
        case_file: CaseFile,
        clue: Clue,
        model_name: str | None = None,
    ) -> LLMResponse:
        fallback_text = self._fallback_clue(clue)
        system_prompt = textwrap.dedent(
            """
            Ты эксперт-помощник следователя.
            Отвечай только по-русски.
            Нельзя добавлять новые улики, новых свидетелей или выводы, которых нет во входных данных.
            Нужно кратко и атмосферно объяснить, что означает улика и насколько она надёжна.
            Формат: 2 коротких абзаца, максимум 5 предложений всего.
            """
        ).strip()
        user_prompt = textwrap.dedent(
            f"""
            Дело: {case_file.title}
            Улика: {clue.title}
            Найдена: {clue.found_at}
            Описание: {clue.description}
            Значение: {clue.interpretation}
            Связанные подозреваемые: {", ".join(clue.related_suspects) or "нет прямой привязки"}
            Ложный след: {"да" if clue.misleading else "нет"}
            Критическая: {"да" if clue.critical else "нет"}
            """
        ).strip()
        return self._post_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            seed=stable_seed(case_file.case_id, clue.clue_id, "clue"),
            model_name=model_name,
            max_tokens=190,
            max_chars=1400,
            fallback_text=fallback_text,
        )

    def narrative_text(
        self,
        *,
        title: str,
        facts: list[str],
        model_name: str | None = None,
    ) -> LLMResponse:
        fallback_text = self._fallback_narrative(title, facts)
        fact_lines = "\n".join(f"- {fact}" for fact in facts)
        system_prompt = textwrap.dedent(
            """
            Ты пишешь короткие атмосферные заметки для детективного интерфейса.
            Отвечай только по-русски.
            Используй только переданные факты, ничего не добавляй от себя.
            Тон: сдержанный, кинематографичный, учебный.
            Длина: 1-2 абзаца, максимум 120 слов.
            """
        ).strip()
        user_prompt = textwrap.dedent(
            f"""
            Заголовок: {title}
            Факты:
            {fact_lines}
            """
        ).strip()
        return self._post_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            seed=stable_seed(title, *facts),
            model_name=model_name,
            max_tokens=180,
            max_chars=1200,
            fallback_text=fallback_text,
        )

    def final_report(
        self,
        *,
        case_file: CaseFile,
        evaluation: dict[str, Any],
        model_name: str | None = None,
    ) -> LLMResponse:
        fallback_text = self._fallback_final_report(case_file, evaluation)
        system_prompt = textwrap.dedent(
            """
            Ты оформляешь итоговый рапорт следователя.
            Отвечай только по-русски.
            Нельзя менять виновного, мотив, улики или оценку расследования.
            Используй только входные факты.
            Напиши 3 коротких абзаца: итог, логика дела, педагогический вывод.
            """
        ).strip()
        user_prompt = textwrap.dedent(
            f"""
            Дело: {case_file.title}
            Обвинённый: {evaluation.get('accused_name')}
            Правильный виновный: {case_file.solution.culprit_name}
            Обвинение верно: {"да" if evaluation.get('correct') else "нет"}
            Счёт: {evaluation.get('score')}
            Качество рассуждения: {evaluation.get('reasoning_quality')}
            Ранг: {evaluation.get('rank')}
            Мотив по делу: {case_file.solution.motive}
            Ключевые улики: {"; ".join(case_file.solution.key_evidence)}
            Противоречия: {"; ".join(case_file.solution.contradictions)}
            Пропущенные улики: {"; ".join(evaluation.get('missed_clues', [])) or "нет"}
            """
        ).strip()
        return self._post_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            seed=stable_seed(case_file.case_id, evaluation.get("score"), evaluation.get("correct")),
            model_name=model_name,
            max_tokens=420,
            max_chars=3200,
            fallback_text=fallback_text,
        )

    def _fallback_dialogue(
        self,
        *,
        case_file: CaseFile,
        suspect: Suspect,
        question: str,
        visible_clues: list[Clue],
    ) -> str:
        lower_question = question.lower()
        stress_line = self._stress_line(suspect.stress_level)
        clue_titles = ", ".join(clue.title.lower() for clue in visible_clues)

        if any(word in lower_question for word in ["где", "когда", "алиби", "находил", "были"]):
            core = f"Я уже говорил(а): {suspect.alibi}"
        elif any(word in lower_question for word in ["мотив", "выгода", "зачем", "почему уб"]):
            core = (
                f"Конфликт с {case_file.victim_name.split()[0]} у меня был, но это не делает меня убийцей. "
                f"Причина напряжения проста: {suspect.motive}"
            )
        elif any(word in lower_question for word in ["отношен", "роман", "лев", "жерт", "виктим"]):
            core = f"Мои отношения с {case_file.victim_name.split()[0]} были такими: {suspect.relationship_to_victim}"
        elif any(point in lower_question for point in suspect.pressure_points) or any(
            keyword in clue_titles for keyword in suspect.pressure_points
        ):
            core = (
                "Вы цепляетесь за неудобную деталь. Я не обязан(а) выворачивать всю свою жизнь "
                "только потому, что вам нужен быстрый виновный."
            )
        else:
            core = (
                f"Я отвечу прямо настолько, насколько могу: {suspect.known_facts[0]}. "
                "Но вы делаете слишком широкие выводы."
            )

        return f"{core} {stress_line}"

    @staticmethod
    def _fallback_clue(clue: Clue) -> str:
        reliability = "Это ключевая улика." if clue.critical else "Это вспомогательная улика."
        caution = "Похоже на ложный след, поэтому её нужно сверять с другими фактами." if clue.misleading else (
            "Она хорошо ложится в логическую цепочку дела и усиливает общую картину."
        )
        return f"{clue.description}\n\n{clue.interpretation} {reliability} {caution}"

    @staticmethod
    def _fallback_narrative(title: str, facts: list[str]) -> str:
        opening = f"{title} выглядит как сцена, где каждая мелочь работает против спешки."
        facts_line = " ".join(facts[:3])
        return f"{opening}\n\n{facts_line}"

    @staticmethod
    def _fallback_final_report(case_file: CaseFile, evaluation: dict[str, Any]) -> str:
        verdict_line = (
            f"Обвинение против {evaluation.get('accused_name')} {'подтверждено' if evaluation.get('correct') else 'не подтвердилось'}."
        )
        logic_line = (
            f"Настоящий виновный — {case_file.solution.culprit_name}. "
            f"Ключевая логика дела: {case_file.solution.logical_explanation}"
        )
        study_line = (
            f"Итоговый счёт: {evaluation.get('score')}. "
            f"Ранг: {evaluation.get('rank')}. "
            f"Пропущенные улики: {', '.join(evaluation.get('missed_clues', [])) or 'нет'}."
        )
        return f"{verdict_line}\n\n{logic_line}\n\n{study_line}"

    @staticmethod
    def _stress_line(stress_level: int) -> str:
        if stress_level >= 75:
            return "И если вы продолжите давить, разговор станет гораздо короче."
        if stress_level >= 60:
            return "Мне уже начинает надоедать повторять одно и то же."
        return "Пока что я готов(а) отвечать спокойно, если вопросы будут по делу."


_DEFAULT_CLIENT = OllamaClient()


def generate_dialogue(**kwargs: Any) -> LLMResponse:
    return _DEFAULT_CLIENT.generate_dialogue(**kwargs)


def describe_clue(**kwargs: Any) -> LLMResponse:
    return _DEFAULT_CLIENT.describe_clue(**kwargs)


def narrative_text(**kwargs: Any) -> LLMResponse:
    return _DEFAULT_CLIENT.narrative_text(**kwargs)


def final_report(**kwargs: Any) -> LLMResponse:
    return _DEFAULT_CLIENT.final_report(**kwargs)
