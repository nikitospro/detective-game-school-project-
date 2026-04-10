from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cases import (
    CaseFile,
    Clue,
    Contradiction,
    Suspect,
    build_generated_case,
    get_case_map,
    get_default_case_id,
    get_generation_themes,
    make_generated_case_id,
    parse_generated_case_id,
)
from ollama_client import OllamaClient
from utils import (
    clamp,
    detective_rank,
    excerpt_history,
    keyword_hits,
    normalize_text,
    reasoning_quality,
    safe_text,
    stable_seed,
    suspicion_label,
)


@dataclass(frozen=True)
class DifficultyProfile:
    key: str
    label: str
    summary_hint_enabled: bool
    contradiction_requires_all_suspects: bool
    contradiction_question_count: int
    suspicion_mode: str


DIFFICULTIES: dict[str, DifficultyProfile] = {
    "cadet": DifficultyProfile(
        key="cadet",
        label="Кадет",
        summary_hint_enabled=True,
        contradiction_requires_all_suspects=False,
        contradiction_question_count=1,
        suspicion_mode="numeric",
    ),
    "detective": DifficultyProfile(
        key="detective",
        label="Следователь",
        summary_hint_enabled=False,
        contradiction_requires_all_suspects=True,
        contradiction_question_count=1,
        suspicion_mode="numeric",
    ),
    "expert": DifficultyProfile(
        key="expert",
        label="Эксперт",
        summary_hint_enabled=False,
        contradiction_requires_all_suspects=True,
        contradiction_question_count=2,
        suspicion_mode="label",
    ),
}


class GameEngine:
    def __init__(
        self,
        llm_client: OllamaClient | None = None,
        case_map: dict[str, CaseFile] | None = None,
    ) -> None:
        self.llm_client = llm_client or OllamaClient()
        self.case_map = case_map or get_case_map()
        self.default_case_id = get_default_case_id()
        self.generation_themes = {theme.key: theme for theme in get_generation_themes()}
        self.generated_case_cache: dict[str, CaseFile] = {}

    def ensure_state(self, state: dict[str, Any] | None) -> dict[str, Any]:
        if not state:
            return self.new_state()

        case_file = self._resolve_case(state.get("case_id"))
        if case_file is None:
            return self.new_state()

        state.setdefault("difficulty", "detective")
        state.setdefault("model_name", self.llm_client.default_model)
        state.setdefault("notes", "")
        state.setdefault("viewed_clues", [])
        state.setdefault("clue_analysis", {})
        state.setdefault("summary", {"text": "", "source": "system", "error": None})
        state.setdefault("result", None)
        state.setdefault("last_llm", {"source": "system", "error": None})

        state["case_id"] = case_file.case_id
        state.setdefault("active_suspect_id", case_file.suspects[0].suspect_id)
        state.setdefault("active_clue_id", case_file.clues[0].clue_id)
        state.setdefault("intro_text", case_file.introduction)
        state.setdefault("intro_source", "system")
        state.setdefault(
            "question_counts",
            {suspect.suspect_id: 0 for suspect in case_file.suspects},
        )
        state.setdefault(
            "chat_history",
            {
                suspect.suspect_id: [
                    {
                        "role": "suspect",
                        "text": self._opening_line(suspect),
                        "source": "system",
                    }
                ]
                for suspect in case_file.suspects
            },
        )

        for suspect in case_file.suspects:
            state["question_counts"].setdefault(suspect.suspect_id, 0)
            state["chat_history"].setdefault(
                suspect.suspect_id,
                [
                    {
                        "role": "suspect",
                        "text": self._opening_line(suspect),
                        "source": "system",
                    }
                ],
            )

        if not any(suspect.suspect_id == state["active_suspect_id"] for suspect in case_file.suspects):
            state["active_suspect_id"] = case_file.suspects[0].suspect_id
        if not any(clue.clue_id == state["active_clue_id"] for clue in case_file.clues):
            state["active_clue_id"] = case_file.clues[0].clue_id

        return state

    def new_state(
        self,
        *,
        case_id: str | None = None,
        difficulty: str = "detective",
        model_name: str | None = None,
    ) -> dict[str, Any]:
        difficulty_key = difficulty if difficulty in DIFFICULTIES else "detective"
        case_file = self.get_case(case_id or self.default_case_id)
        intro = self.llm_client.narrative_text(
            title=f"Вводная: {case_file.title}",
            facts=[
                case_file.introduction,
                f"Локация: {case_file.location}",
                *case_file.timeline[:3],
            ],
            model_name=model_name,
        )
        return {
            "case_id": case_file.case_id,
            "difficulty": difficulty_key,
            "model_name": (model_name or self.llm_client.default_model).strip() or self.llm_client.default_model,
            "active_suspect_id": case_file.suspects[0].suspect_id,
            "active_clue_id": case_file.clues[0].clue_id,
            "notes": "",
            "viewed_clues": [],
            "clue_analysis": {},
            "summary": {"text": "", "source": "system", "error": None},
            "result": None,
            "question_counts": {suspect.suspect_id: 0 for suspect in case_file.suspects},
            "chat_history": {
                suspect.suspect_id: [
                    {
                        "role": "suspect",
                        "text": self._opening_line(suspect),
                        "source": "system",
                    }
                ]
                for suspect in case_file.suspects
            },
            "intro_text": intro.text,
            "intro_source": intro.source,
            "case_started_at": datetime.now(timezone.utc).isoformat(),
            "last_llm": {"source": intro.source, "error": intro.error},
        }

    def change_case(
        self,
        state: dict[str, Any],
        *,
        case_id: str,
        difficulty: str | None = None,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        return self.new_state(
            case_id=case_id,
            difficulty=difficulty or state.get("difficulty", "detective"),
            model_name=model_name or state.get("model_name"),
        )

    def update_settings(
        self,
        state: dict[str, Any],
        *,
        difficulty: str | None = None,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        updated = deepcopy(self.ensure_state(state))
        if difficulty in DIFFICULTIES:
            updated["difficulty"] = difficulty
        if model_name is not None:
            cleaned_model = safe_text(model_name, self.llm_client.default_model)
            updated["model_name"] = cleaned_model
        return updated

    def get_case(self, case_id: str) -> CaseFile:
        return self._resolve_case(case_id) or self.case_map[self.default_case_id]

    def start_generated_case(
        self,
        state: dict[str, Any],
        *,
        theme_key: str,
        seed_text: str,
        difficulty: str | None = None,
        model_name: str | None = None,
    ) -> tuple[dict[str, Any], str | None]:
        cleaned_theme = safe_text(theme_key)
        if cleaned_theme not in self.generation_themes:
            return deepcopy(self.ensure_state(state)), "Выберите тему для процедурного дела."

        if safe_text(seed_text):
            try:
                seed = abs(int(seed_text))
            except ValueError:
                return deepcopy(self.ensure_state(state)), "Seed должен быть целым числом."
        else:
            seed = stable_seed(
                cleaned_theme,
                datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            )

        if seed == 0:
            seed = 1

        return (
            self.new_state(
                case_id=make_generated_case_id(cleaned_theme, seed),
                difficulty=difficulty or state.get("difficulty", "detective"),
                model_name=model_name or state.get("model_name"),
            ),
            None,
        )

    def get_case_options(self, state: dict[str, Any]) -> list[CaseFile]:
        options = list(self.case_map.values())
        current_case = self._resolve_case(state.get("case_id"))
        if current_case and current_case.case_id not in self.case_map:
            options.append(current_case)
        return options

    def get_difficulty(self, state: dict[str, Any]) -> DifficultyProfile:
        return DIFFICULTIES.get(state.get("difficulty", "detective"), DIFFICULTIES["detective"])

    def select_suspect(self, state: dict[str, Any], suspect_id: str) -> dict[str, Any]:
        updated = deepcopy(self.ensure_state(state))
        case_file = self.get_case(updated["case_id"])
        if any(suspect.suspect_id == suspect_id for suspect in case_file.suspects):
            updated["active_suspect_id"] = suspect_id
        return updated

    def select_clue(self, state: dict[str, Any], clue_id: str) -> dict[str, Any]:
        updated = deepcopy(self.ensure_state(state))
        case_file = self.get_case(updated["case_id"])
        if any(clue.clue_id == clue_id for clue in case_file.clues):
            updated["active_clue_id"] = clue_id
        return updated

    def save_notes(self, state: dict[str, Any], notes: str) -> dict[str, Any]:
        updated = deepcopy(self.ensure_state(state))
        updated["notes"] = safe_text(notes)[:5000]
        return updated

    def interrogate(
        self,
        state: dict[str, Any],
        *,
        suspect_id: str,
        question: str,
    ) -> tuple[dict[str, Any], str | None]:
        updated = deepcopy(self.ensure_state(state))
        cleaned_question = safe_text(question)
        if not cleaned_question:
            return updated, "Введите вопрос перед допросом."

        case_file = self.get_case(updated["case_id"])
        if not any(item.suspect_id == suspect_id for item in case_file.suspects):
            return updated, "Не удалось найти выбранного подозреваемого."
        suspect = case_file.suspect_by_id(suspect_id)
        updated["active_suspect_id"] = suspect_id
        history = updated["chat_history"][suspect_id]
        history.append({"role": "detective", "text": cleaned_question, "source": "user"})

        visible_clues = [
            case_file.clue_by_id(clue_id)
            for clue_id in updated["viewed_clues"]
            if clue_id in {clue.clue_id for clue in case_file.clues}
        ]
        contradictions = self.get_available_contradictions(case_file, updated)
        response = self.llm_client.generate_dialogue(
            case_file=case_file,
            suspect=suspect,
            question=cleaned_question,
            history=excerpt_history(history),
            visible_clues=visible_clues,
            contradictions=contradictions,
            model_name=updated["model_name"],
        )
        history.append(
            {
                "role": "suspect",
                "text": response.text,
                "source": response.source,
            }
        )
        updated["question_counts"][suspect_id] += 1
        updated["result"] = None
        updated["last_llm"] = {"source": response.source, "error": response.error}
        return updated, None

    def analyze_clue(self, state: dict[str, Any], *, clue_id: str) -> tuple[dict[str, Any], str | None]:
        updated = deepcopy(self.ensure_state(state))
        case_file = self.get_case(updated["case_id"])
        if not any(item.clue_id == clue_id for item in case_file.clues):
            return updated, "Не удалось найти выбранную улику."
        clue = case_file.clue_by_id(clue_id)
        updated["active_clue_id"] = clue_id
        if clue_id not in updated["viewed_clues"]:
            updated["viewed_clues"].append(clue_id)

        if clue_id not in updated["clue_analysis"]:
            response = self.llm_client.describe_clue(
                case_file=case_file,
                clue=clue,
                model_name=updated["model_name"],
            )
            updated["clue_analysis"][clue_id] = {
                "text": response.text,
                "source": response.source,
                "error": response.error,
            }
            updated["last_llm"] = {"source": response.source, "error": response.error}

        updated["result"] = None
        return updated, None

    def generate_summary(self, state: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
        updated = deepcopy(self.ensure_state(state))
        case_file = self.get_case(updated["case_id"])
        difficulty = self.get_difficulty(updated)
        questioned = [
            case_file.suspect_by_id(suspect_id).name
            for suspect_id, count in updated["question_counts"].items()
            if count > 0
        ]
        analyzed_clues = [
            case_file.clue_by_id(clue_id).title
            for clue_id in updated["viewed_clues"]
        ]
        contradictions = [item.title for item in self.get_available_contradictions(case_file, updated)]
        facts = [
            case_file.introduction,
            f"Опрошены: {', '.join(questioned) or 'пока никто'}",
            f"Изученные улики: {', '.join(analyzed_clues) or 'пока нет'}",
            f"Выявленные противоречия: {', '.join(contradictions) or 'пока нет'}",
        ]
        if difficulty.summary_hint_enabled:
            facts.append(f"Подсказка наставника: {case_file.summary_hint}")

        summary = self.llm_client.narrative_text(
            title=f"Сводка расследования: {case_file.title}",
            facts=facts,
            model_name=updated["model_name"],
        )
        updated["summary"] = {
            "text": summary.text,
            "source": summary.source,
            "error": summary.error,
        }
        updated["last_llm"] = {"source": summary.source, "error": summary.error}
        return updated, None

    def evaluate_accusation(
        self,
        state: dict[str, Any],
        *,
        accused_id: str,
        motive_text: str,
        evidence_text: str,
    ) -> tuple[dict[str, Any], str | None]:
        updated = deepcopy(self.ensure_state(state))
        case_file = self.get_case(updated["case_id"])
        if not any(item.suspect_id == accused_id for item in case_file.suspects):
            return updated, "Выберите подозреваемого для обвинения."
        accused = case_file.suspect_by_id(accused_id)
        normalized_motive = normalize_text(motive_text)
        normalized_evidence = normalize_text(evidence_text)

        if not normalized_motive or not normalized_evidence:
            return updated, "Для обвинения нужно указать и мотив, и доказательства."

        correct = accused_id == case_file.solution.culprit_id
        motive_hits = keyword_hits(normalized_motive, case_file.solution.motive_keywords)
        evidence_matches = {
            clue_id: keyword_hits(normalized_evidence, keywords)
            for clue_id, keywords in case_file.solution.evidence_keywords.items()
        }
        matched_evidence_ids = [clue_id for clue_id, hits in evidence_matches.items() if hits]
        critical_clues = [clue for clue in case_file.clues if clue.critical]
        questioned_count = sum(1 for count in updated["question_counts"].values() if count > 0)
        contradictions = self.get_available_contradictions(case_file, updated)

        suspect_score = 45 if correct else 0
        motive_score = min(20, len(motive_hits) * 4 + (4 if len(motive_hits) >= 2 else 0))
        evidence_score = min(25, len(matched_evidence_ids) * 5)
        investigation_score = min(
            10,
            len([clue for clue in critical_clues if clue.clue_id in updated["viewed_clues"]]) * 2
            + questioned_count
            + min(3, len(contradictions)),
        )
        difficulty_bonus = 5 if correct and updated.get("difficulty") == "expert" else 0

        score = suspect_score + motive_score + evidence_score + investigation_score + difficulty_bonus
        if not correct:
            score = min(score, 55)
        score = int(clamp(score, 0, 100))

        missed_clues = [
            clue.title
            for clue in critical_clues
            if clue.clue_id not in matched_evidence_ids
        ]
        rank, rank_description = detective_rank(score)
        result = {
            "accused_id": accused_id,
            "accused_name": accused.name,
            "correct": correct,
            "score": score,
            "reasoning_quality": reasoning_quality(score),
            "rank": rank,
            "rank_description": rank_description,
            "motive_hits": motive_hits,
            "matched_evidence_titles": [
                case_file.clue_by_id(clue_id).title for clue_id in matched_evidence_ids
            ],
            "missed_clues": missed_clues,
            "culprit_name": case_file.solution.culprit_name,
            "solution_motive": case_file.solution.motive,
            "solution_explanation": case_file.solution.logical_explanation,
            "submitted_motive": safe_text(motive_text),
            "submitted_evidence": safe_text(evidence_text),
            "questioned_count": questioned_count,
            "analyzed_clues_count": len(updated["viewed_clues"]),
            "contradictions_count": len(contradictions),
        }
        final_report = self.llm_client.final_report(
            case_file=case_file,
            evaluation=result,
            model_name=updated["model_name"],
        )
        result["report_text"] = final_report.text
        result["report_source"] = final_report.source
        result["report_error"] = final_report.error
        updated["result"] = result
        updated["last_llm"] = {"source": final_report.source, "error": final_report.error}
        return updated, None

    def get_available_contradictions(
        self,
        case_file: CaseFile,
        state: dict[str, Any],
    ) -> list[Contradiction]:
        difficulty = self.get_difficulty(state)
        available: list[Contradiction] = []
        viewed_clues = set(state.get("viewed_clues", []))
        question_counts = state.get("question_counts", {})

        for contradiction in case_file.contradictions:
            clues_ready = all(clue_id in viewed_clues for clue_id in contradiction.clue_ids)
            if not clues_ready:
                continue

            required_questions = max(
                contradiction.unlock_after_questions,
                difficulty.contradiction_question_count,
            )
            if difficulty.contradiction_requires_all_suspects:
                suspects_ready = all(
                    question_counts.get(suspect_id, 0) >= required_questions
                    for suspect_id in contradiction.suspect_ids
                )
            else:
                suspects_ready = any(
                    question_counts.get(suspect_id, 0) >= required_questions
                    for suspect_id in contradiction.suspect_ids
                )

            if suspects_ready:
                available.append(contradiction)

        return available

    def get_suspicion_levels(self, case_file: CaseFile, state: dict[str, Any]) -> dict[str, dict[str, Any]]:
        viewed_clues = {clue_id for clue_id in state.get("viewed_clues", [])}
        contradictions = self.get_available_contradictions(case_file, state)
        suspicion: dict[str, dict[str, Any]] = {}

        for suspect in case_file.suspects:
            score = 12 + state["question_counts"].get(suspect.suspect_id, 0) * 3
            for clue in case_file.clues:
                if suspect.suspect_id in clue.related_suspects and clue.clue_id in viewed_clues:
                    if clue.critical:
                        score += 18
                    elif clue.misleading:
                        score += 7
                    else:
                        score += 4
            for contradiction in contradictions:
                if suspect.suspect_id in contradiction.suspect_ids:
                    score += 8 + contradiction.severity * 2

            numeric = int(clamp(score, 5, 95))
            suspicion[suspect.suspect_id] = {
                "score": numeric,
                "label": suspicion_label(numeric),
            }
        return suspicion

    def build_view_model(self, state: dict[str, Any]) -> dict[str, Any]:
        current_state = self.ensure_state(deepcopy(state))
        case_file = self.get_case(current_state["case_id"])
        difficulty = self.get_difficulty(current_state)
        active_suspect = case_file.suspect_by_id(current_state["active_suspect_id"])
        active_clue = case_file.clue_by_id(current_state["active_clue_id"])
        suspect_name_map = {suspect.suspect_id: suspect.name for suspect in case_file.suspects}
        suspicion = self.get_suspicion_levels(case_file, current_state)
        contradictions = self.get_available_contradictions(case_file, current_state)

        suspect_cards = []
        for suspect in case_file.suspects:
            suspect_cards.append(
                {
                    "suspect": suspect,
                    "questions": current_state["question_counts"].get(suspect.suspect_id, 0),
                    "suspicion": suspicion[suspect.suspect_id],
                    "active": suspect.suspect_id == current_state["active_suspect_id"],
                }
            )

        clue_cards = []
        for clue in case_file.clues:
            analysis = current_state["clue_analysis"].get(clue.clue_id)
            clue_cards.append(
                {
                    "clue": clue,
                    "analysis": analysis,
                    "viewed": clue.clue_id in current_state["viewed_clues"],
                    "active": clue.clue_id == current_state["active_clue_id"],
                }
            )

        return {
            "case_file": case_file,
            "case_options": self.get_case_options(current_state),
            "generation_themes": list(self.generation_themes.values()),
            "difficulty": difficulty,
            "difficulty_options": list(DIFFICULTIES.values()),
            "state": current_state,
            "is_generated_case": case_file.origin == "generated",
            "active_suspect": active_suspect,
            "active_history": current_state["chat_history"][active_suspect.suspect_id],
            "active_clue": active_clue,
            "active_clue_related_names": [
                suspect_name_map.get(suspect_id, suspect_id)
                for suspect_id in active_clue.related_suspects
            ],
            "active_clue_analysis": current_state["clue_analysis"].get(active_clue.clue_id),
            "suspect_cards": suspect_cards,
            "clue_cards": clue_cards,
            "contradictions": contradictions,
            "suspicion": suspicion,
            "suspect_name_map": suspect_name_map,
            "last_llm": current_state.get("last_llm", {"source": "system", "error": None}),
            "progress": {
                "questioned_suspects": sum(
                    1 for count in current_state["question_counts"].values() if count > 0
                ),
                "analyzed_clues": len(current_state["viewed_clues"]),
                "available_contradictions": len(contradictions),
            },
        }

    def _resolve_case(self, case_id: str | None) -> CaseFile | None:
        cleaned_case_id = safe_text(case_id)
        if not cleaned_case_id:
            return None
        if cleaned_case_id in self.case_map:
            return self.case_map[cleaned_case_id]

        parsed = parse_generated_case_id(cleaned_case_id)
        if parsed is None:
            return None

        theme_key, seed = parsed
        generated_case_id = make_generated_case_id(theme_key, seed)
        if generated_case_id not in self.generated_case_cache:
            self.generated_case_cache[generated_case_id] = build_generated_case(theme_key, seed)
        return self.generated_case_cache[generated_case_id]

    @staticmethod
    def _opening_line(suspect: Suspect) -> str:
        return (
            f"{suspect.name}: я готов(а) отвечать, но не собираюсь терпеть пустые обвинения."
        )
