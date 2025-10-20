from flask import Blueprint, render_template, session, request, redirect, url_for, jsonify
from collections import defaultdict
import json, re
from app.db import db_app

editor_bp = Blueprint('editor', __name__)


def is_admin():
    return session.get('user') and session['user']['email'] == 'admin@gmail.com'


@editor_bp.route('/admin')
def admin():
    if not is_admin():
        return "Доступ запрещён", 403

    users = db_app.fetch_all("SELECT * FROM user_profiles")
    guest_emails = db_app.fetch_all("SELECT * FROM guest_emails ORDER BY collected_at DESC")
    courses = db_app.fetch_all("SELECT * FROM main_courses ORDER BY id")

    return render_template(
        'admin.html',
        users=users,
        guest_emails=guest_emails,
        courses=courses
    )


@editor_bp.route('/editor')
def editor():
    if not is_admin():
        return "Доступ запрещён", 403

    users = db_app.fetch_all("SELECT * FROM user_profiles")
    author_courses = db_app.fetch_all("SELECT * FROM author_courses ORDER BY id")
    main_courses = db_app.fetch_all("SELECT * FROM levels_course ORDER BY step_index")
    levels = db_app.fetch_all("SELECT * FROM levels_course ORDER BY level_index, step_index")

    return render_template(
        "editor.html",
        users=users,
        main_courses=main_courses,
        author_courses=author_courses,
        levels=levels
    )


@editor_bp.route("/add_trait", methods=["POST"])
def add_trait():
    name = request.form.get("name")
    if name:
        db_app.insert("traits", {"name": name})
        return "OK", 200
    return "Ошибка", 400


@editor_bp.route("/add_author_course", methods=["POST"])
def add_author_course():
    data = {
        "id": int(request.form.get("id")),
        "title": request.form.get("title"),
        "description": request.form.get("description"),
        "author": request.form.get("author"),
        "traits": [t.strip() for t in request.form.get("traits", "").split(",")],
        "first_lesson_id": request.form.get("first_lesson_id"),
        "available": True,
        "condition": "1"
    }
    db_app.insert("author_courses", data)
    return redirect(url_for("editor.editor"))


@editor_bp.route("/add_level", methods=["POST"])
def add_level():
    level = int(request.form.get("level"))
    step = int(request.form.get("step"))
    title = request.form.get("title")
    description = request.form.get("description")

    result = db_app.insert("levels_course", {
        "chapter_id": 1,
        "title": title,
        "description": description,
        "step": step,
        "level": level,
    })

    return ("OK", 200) if result else (jsonify({"error": "Ошибка при добавлении"}), 400)


@editor_bp.route("/add_lesson", methods=["POST"])
def add_lesson():
    try:
        level_title = request.form.get("level_id")
        level_id = db_app.fetch_one(
            "SELECT id FROM levels_course WHERE title = %s", (level_title,)
        )["id"]

        page_number = len(db_app.fetch_all("SELECT * FROM lessons WHERE course_id = %s", (level_id,))) + 1

        lesson_id = db_app.insert("lessons", {
            "course_id": level_id,
            "page": page_number,
            "count_pages": page_number
        })

        items = defaultdict(dict)
        for key, value in request.form.items():
            match = re.match(r'items\[(\d+)\]\[(\w+)\]', key)
            if match:
                idx, subkey = match.groups()
                items[int(idx)][subkey] = value

        for item in items.values():
            lesson_page = len(db_app.fetch_all("SELECT id FROM content WHERE lesson_id = %s", (lesson_id,))) + 1
            if item.get("mode") == "content":
                db_app.insert("content", {
                    "lesson_id": lesson_id,
                    "lesson_page": lesson_page,
                    "type": item.get("type"),
                    "content": item.get("content")
                })
            elif item.get("mode") == "question":
                qa = {
                    "question": item.get("question"),
                    "answer1": item.get("answer1"),
                    "price1": int(item.get("price1", 0)),
                }
                db_app.insert("questions", {
                    "lesson_id": lesson_id,
                    "lesson_page": lesson_page,
                    "qa": json.dumps(qa)
                })

        return redirect(url_for("editor.editor"))

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@editor_bp.route("/update_author_course", methods=["POST"])
def update_author_course():
    db_app.execute("""
        UPDATE author_courses
        SET title = %s, author = %s, description = %s
        WHERE id = %s
    """, (
        request.form.get("title"),
        request.form.get("author"),
        request.form.get("description"),
        request.form.get("id")
    ))
    return "OK", 200


@editor_bp.route("/delete_author_course", methods=["POST"])
def delete_author_course():
    db_app.execute("DELETE FROM author_courses WHERE id = %s", (request.form.get("id"),))
    return "OK", 200


@editor_bp.route("/add_test", methods=["POST"])
def add_test():
    db_app.insert("tests", {
        "title": request.form.get("title"),
        "description": request.form.get("description"),
        "available": request.form.get("available") == "on",
        "condition": [c.strip() for c in request.form.get("condition", "").split(",") if c.strip()]
    })
    return "OK", 200


@editor_bp.route("/add_test_question", methods=["POST"])
def add_test_question():
    options = [o.strip() for o in request.form.get("options", "").split(",")]
    db_app.insert("test_questions", {
        "test_id": int(request.form.get("test_id")),
        "question_index": int(request.form.get("question_index")),
        "text": request.form.get("text"),
        "options": options
    })
    return "OK", 200


@editor_bp.route("/save_test_full", methods=["POST"])
def save_test_full():
    data = request.form
    theme_id = db_app.insert("test_themes", {
        "title": data.get("title"),
        "description": data.get("description", "")
    })

    question_map = {}
    for key in data:
        if key.startswith("question_"):
            idx = key.split("_")[1]
            question_map[idx] = {"ask": data[key], "answers": []}

    for key in data:
        if key.startswith("answer_"):
            _, qid, aid = key.split("_")
            score_key = f"score_{qid}_{aid}"
            question_map[qid]["answers"].append({
                "text": data[key],
                "score": int(data.get(score_key, 0))
            })

    ask_id_map = {}
    for idx, q in question_map.items():
        ask_id = db_app.insert("asks", {"theme_id": theme_id, "ask": q["ask"]})
        ask_id_map[idx] = ask_id
        for a in q["answers"]:
            db_app.insert("answers", {"ask_id": ask_id, "text": a["text"], "score": a["score"]})

    for key in data:
        if key.startswith("skill_") and key.endswith("_name"):
            skill_idx = key.split("_")[1]
            skill_name = data[key]
            asks_raw = data.get(f"skill_{skill_idx}_questions", "")
            qnums = [a.strip() for a in asks_raw.split(",") if a.strip().isdigit()]
            ask_ids = [str(ask_id_map[q]) for q in qnums if q in ask_id_map]
            db_app.insert("test_skills", {
                "theme_id": theme_id,
                "asks": ",".join(ask_ids),
                "total": len(ask_ids),
                "title": skill_name
            })

    return "OK", 200
