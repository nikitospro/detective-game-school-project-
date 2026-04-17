from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

from game_logic import GameEngine
from utils import JsonSessionStore, ensure_session_id, safe_text


BASE_DIR = Path(__file__).resolve().parent
STORE = JsonSessionStore(BASE_DIR / "data" / "sessions")
ENGINE = GameEngine()
CUSTOM_THEME_FIELDS = [
    "theme_label",
    "pitch",
    "case_title",
    "venue_name",
    "location",
    "event_name",
    "victim_role",
    "restricted_area",
    "public_area",
    "side_area",
    "document_name",
    "trace_material",
    "crime_object",
    "suspect_roles",
]


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "detective-demo-secret-key")
app.config["TEMPLATES_AUTO_RELOAD"] = True


def load_state() -> tuple[str, dict]:
    session_id = ensure_session_id(session)
    state = STORE.load(session_id)
    state = ENGINE.ensure_state(state)
    STORE.save(session_id, state)
    return session_id, state


def save_state(session_id: str, state: dict) -> None:
    STORE.save(session_id, state)


@app.route("/", methods=["GET"])
def index() -> str:
    _, state = load_state()
    view_model = ENGINE.build_view_model(state)
    return render_template("index.html", **view_model)


@app.route("/case/select", methods=["POST"])
def select_case() -> str:
    session_id, state = load_state()
    requested_case = safe_text(request.form.get("case_id"), state["case_id"])
    difficulty = safe_text(request.form.get("difficulty"), state.get("difficulty", "detective"))
    model_name = safe_text(request.form.get("model_name"), state.get("model_name"))

    if requested_case != state["case_id"]:
        updated_state = ENGINE.change_case(
            state,
            case_id=requested_case,
            difficulty=difficulty,
            model_name=model_name,
        )
        flash("Новое дело загружено. Расследование началось заново.", "success")
    else:
        updated_state = ENGINE.update_settings(
            state,
            difficulty=difficulty,
            model_name=model_name,
        )
        flash("Настройки обновлены.", "success")

    save_state(session_id, updated_state)
    return redirect(url_for("index"))


@app.route("/case/generate", methods=["POST"])
def generate_case() -> str:
    session_id, state = load_state()
    theme_key = safe_text(request.form.get("theme_key"))
    seed_text = request.form.get("case_seed", "")
    difficulty = safe_text(request.form.get("difficulty"), state.get("difficulty", "detective"))
    model_name = safe_text(request.form.get("model_name"), state.get("model_name"))

    updated_state, error = ENGINE.start_generated_case(
        state,
        theme_key=theme_key,
        seed_text=seed_text,
        difficulty=difficulty,
        model_name=model_name,
    )
    save_state(session_id, updated_state)
    if error:
        flash(error, "error")
    else:
        flash("Процедурное дело сгенерировано. Можно начинать новое расследование.", "success")
    return redirect(url_for("index"))


@app.route("/case/generate/custom", methods=["POST"])
def generate_custom_case() -> str:
    session_id, state = load_state()
    custom_payload = {
        field: request.form.get(field, "")
        for field in CUSTOM_THEME_FIELDS
    }
    seed_text = request.form.get("custom_case_seed", "")
    difficulty = safe_text(request.form.get("difficulty"), state.get("difficulty", "detective"))
    model_name = safe_text(request.form.get("model_name"), state.get("model_name"))

    updated_state, error = ENGINE.start_custom_case(
        state,
        custom_payload=custom_payload,
        seed_text=seed_text,
        difficulty=difficulty,
        model_name=model_name,
    )
    save_state(session_id, updated_state)
    if error:
        flash(error, "error")
    else:
        flash("Кастомное дело собрано из ваших параметров. Расследование началось.", "success")
    return redirect(url_for("index"))


@app.route("/case/reset", methods=["POST"])
def reset_case() -> str:
    session_id, state = load_state()
    updated_state = ENGINE.change_case(
        state,
        case_id=state["case_id"],
        difficulty=state.get("difficulty", "detective"),
        model_name=state.get("model_name"),
    )
    save_state(session_id, updated_state)
    flash("Текущее дело перезапущено.", "success")
    return redirect(url_for("index"))


@app.route("/suspect/select", methods=["POST"])
def select_suspect() -> str:
    session_id, state = load_state()
    suspect_id = safe_text(request.form.get("suspect_id"))
    updated_state = ENGINE.select_suspect(state, suspect_id)
    save_state(session_id, updated_state)
    return redirect(url_for("index"))


@app.route("/clue/select", methods=["POST"])
def select_clue() -> str:
    session_id, state = load_state()
    clue_id = safe_text(request.form.get("clue_id"))
    updated_state = ENGINE.select_clue(state, clue_id)
    save_state(session_id, updated_state)
    return redirect(url_for("index"))


@app.route("/clue/analyze", methods=["POST"])
def analyze_clue() -> str:
    session_id, state = load_state()
    clue_id = safe_text(request.form.get("clue_id"))
    updated_state, error = ENGINE.analyze_clue(state, clue_id=clue_id)
    save_state(session_id, updated_state)
    if error:
        flash(error, "error")
    else:
        flash("Улика добавлена в рабочее досье и разобрана.", "success")
    return redirect(url_for("index"))


@app.route("/interrogate", methods=["POST"])
def interrogate() -> str:
    session_id, state = load_state()
    suspect_id = safe_text(request.form.get("suspect_id"), state.get("active_suspect_id"))
    question = request.form.get("question", "")
    updated_state, error = ENGINE.interrogate(state, suspect_id=suspect_id, question=question)
    save_state(session_id, updated_state)
    if error:
        flash(error, "error")
    else:
        flash("Ответ получен и добавлен в протокол допроса.", "success")
    return redirect(url_for("index"))


@app.route("/notes", methods=["POST"])
def save_notes() -> str:
    session_id, state = load_state()
    notes = request.form.get("notes", "")
    updated_state = ENGINE.save_notes(state, notes)
    save_state(session_id, updated_state)
    flash("Заметки сохранены.", "success")
    return redirect(url_for("index"))


@app.route("/summary", methods=["POST"])
def generate_summary() -> str:
    session_id, state = load_state()
    updated_state, error = ENGINE.generate_summary(state)
    save_state(session_id, updated_state)
    if error:
        flash(error, "error")
    else:
        flash("Сводка расследования обновлена.", "success")
    return redirect(url_for("index"))


@app.route("/accuse", methods=["POST"])
def accuse() -> str:
    session_id, state = load_state()
    accused_id = safe_text(request.form.get("accused_id"))
    motive = request.form.get("motive", "")
    evidence = request.form.get("evidence", "")
    updated_state, error = ENGINE.evaluate_accusation(
        state,
        accused_id=accused_id,
        motive_text=motive,
        evidence_text=evidence,
    )
    save_state(session_id, updated_state)
    if error:
        flash(error, "error")
    else:
        flash("Итоговое обвинение проверено.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
