from flask import Blueprint, render_template, session, request, redirect, url_for, jsonify
from collections import defaultdict
import json, re
from app.db import db_app
from app.editor.services import load_data_ask_trait_to_db

editor_bp = Blueprint('editor', __name__)


def is_admin():
    return session.get('user') and session['user']['email'] == 'admin@gmail.com'

from io import StringIO, BytesIO

@editor_bp.route('/admin')
def admin():
    if not is_admin():
        return "Доступ запрещён", 403

    users = db_app.fetch_all("SELECT * FROM user_profiles;")
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
    main_courses = [{"id": 0, "Title": " "}]
    users = db_app.fetch_all("SELECT * FROM user_profiles;")
    author_courses = db_app.fetch_all("SELECT * FROM author_courses ORDER BY id;")
    main_courses.extend(db_app.fetch_all("SELECT * FROM levels_course ORDER BY step_index;"))
    levels = db_app.fetch_all("SELECT * FROM levels_course ORDER BY level_index, step_index;")
    tests = [{"title": "", "id": ""}] + db_app.fetch_all("SELECT * FROM test ORDER BY id;")

    # Один запрос для всех уроков
    all_lessons = db_app.fetch_all(
        "SELECT * FROM lessons ORDER BY course_id, id;")
    all_content = db_app.fetch_all(
        "SELECT * FROM lesson_content ORDER BY lesson_id, id;"
    )

    content_by_lesson = defaultdict(list)
    for content in all_content:
        content_by_lesson[content["lesson_id"]].append(content)
    # Группировка уроков по course_id
    lessons_by_course = defaultdict(list)
    for lesson in all_lessons:
        lesson["content"] = content_by_lesson.get(lesson["id"], [])
        lessons_by_course[lesson["course_id"]].append(lesson)

    # Присваиваем уроки курсам
    for course in main_courses:
        course["lessons"] = lessons_by_course.get(course["id"], [])

    return render_template(
        "editor.html",
        users=users,
        courses=main_courses,
        author_courses=author_courses,
        levels=levels,
        tests=tests
    )

def upload_csv(input_name, file_name):
    import os
    file = request.files.get(input_name)
    if not file:
        return "Файл не загружен", 400

    filename = file.filename

    try:
        file.save(file_name)
        return f"Файл сохранён как: {file_name}", 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Ошибка сохранения: {e}", 500

@editor_bp.route("/upload_asks_csv", methods=["POST"])
def upload_asks_csv():
    return upload_csv("csv_asks", "asks.csv")

@editor_bp.route("/upload_traits_csv", methods=["POST"])
def upload_traits_csv():
    return upload_csv("csv_traits", "traits.csv")

@editor_bp.route("/upload_test_csv", methods=["POST"])
def upload_test_csv():
    from app.db import db_app

    title = request.form.get("title")
    is_main = request.form.get('is_public') == 'true'
    description = request.form.get("description")

    upload_csv("csv_asks", "asks.csv")
    upload_csv("csv_traits", "traits.csv")

    if not title:
        return "Не указано название теста", 400

    try:
        # 1. Создаём тест
        test_id = db_app.insert("test", {
            "title": title,
            "description": description,
            "is_main": is_main
        })
        load_data_ask_trait_to_db(test_id=test_id)

        return "Тест, вопросы и навыки успешно добавлены", 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Ошибка: {str(e)}", 500


@editor_bp.route("/upload_course", methods=["POST"])
def upload_course():
    from app.db import db_app

    title = request.form.get("title")
    description = request.form.get("description")
    level = request.form.get("level")
    course_type = request.form.get("type")

    if not title or not level or not course_type:
        return "Не все обязательные поля заполнены", 400

    try:
        # Логика вставки
        course_id = 1
        level_index = 1 if course_type == "main" else 2
        step_index = int(level)

        db_app.insert("levels_course", {
            "course_id": course_id,
            "level_index": level_index,
            "step_index": step_index,
            "title": title,
            "description": description,
        }, returning=False)

        return "Курс успешно добавлен", 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Ошибка при сохранении курса: {str(e)}", 500


@editor_bp.route("/upload_lesson", methods=["POST"])
def upload_lesson():

    from app.db import db_app

    title = request.form.get("title")
    description = request.form.get("description")
    course_title = request.form.get("course_title")
    course_id = db_app.fetch_one(f"SELECT id FROM levels_course WHERE title = '{course_title}';")["id"]
    if not title or not course_id:
        return "Название урока и курс обязательны", 400
    try:
        db_app.insert("lessons", {
            "course_id": int(course_id),
            "title": title,
            "description": description,
            "course_type": "Part 1",
            "type": "Part 1",
        }, returning=False)
        return "Урок успешно добавлен", 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Ошибка при добавлении урока: {str(e)}", 500

@editor_bp.route("/upload_lesson_content_csv", methods=["POST"])
def upload_lesson_content_csv():
    from app.db import db_app
    import pandas as pd

    upload_csv("csv_file", "content.csv")
    course_title = request.form.get("course_title")
    course_id = db_app.fetch_one(f"SELECT id FROM levels_course WHERE title = '{course_title}';")["id"]
    lesson_id = db_app.fetch_all(sql="SELECT id FROM lessons WHERE course_id = %s;", params=(course_id,))
    try:
        df = pd.read_csv("content.csv")
        df.columns = ["page_num", "type", "title", "content"]
        if df.empty:
            return "CSV-файл пустой", 400

        type_map = {
            "текст": "txt",
            "картинка": "image",
            "видео": "video"
        }

        df["type"] = df["type"].str.strip().str.lower().map(type_map).fillna(df["type"])
        # Очистка строк (удаление лишних пробелов)
        df["title"] = df["title"].astype(str).str.strip()
        df["content"] = df["content"].astype(str).str.strip()
        df['page_num'] = df['page_num'].fillna(1)
        df["page_num"] = df["page_num"].astype(int)

        lessons = db_app.fetch_all(f"SELECT * FROM lessons WHERE course_id = {course_id};")
        # Проверка нужных колонок
        required_columns = {"page_num", "type", "title", "content"}
        if not required_columns.issubset(df.columns):
            return f"В CSV-файле должны быть колонки: {required_columns}", 400
        # Вставка данных в БД
        for _, row in df.iterrows():
            title_value = " " if pd.isna(row["title"]) else row["title"]
            db_app.insert("lesson_content", {
                "lesson_id": lesson_id[int(row["page_num"]) - 1]["id"],
                "type": row["type"],
                "title": title_value,
                "content": row["content"],
                "page_num": row["page_num"]
            })
        return "Контент урока успешно загружен", 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Ошибка обработки файла: {str(e)}", 500


@editor_bp.route("/upload_lesson_images_zip", methods=["POST"])
def upload_lesson_images_zip():
    import zipfile, os, shutil
    from werkzeug.utils import secure_filename

    course_title = request.form.get("course_id")
    course_id = db_app.fetch_one(f"SELECT id FROM levels_course WHERE title = '{course_title}';")["id"]
    zip_file = request.files.get("zip_file")

    if not zip_file or not course_id:
        return "Не указан файл или курс", 400

    try:
        # Создаем папку назначения
        upload_folder = os.path.abspath(f"app/static/uploads/course_{course_id}")
        os.makedirs(upload_folder, exist_ok=True)

        # Сохраняем zip-файл временно
        zip_path = os.path.join(upload_folder, secure_filename(zip_file.filename))
        zip_file.save(zip_path)

        # Временная директория для распаковки
        tmp_folder = os.path.join(upload_folder, "_tmp_extract")
        os.makedirs(tmp_folder, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as archive:
            # Проверка безопасности путей
            for member in archive.namelist():
                member_path = os.path.abspath(os.path.join(tmp_folder, member))
                if not member_path.startswith(tmp_folder):
                    return "❌ Обнаружена попытка path traversal!", 400
            archive.extractall(tmp_folder)

        # Удаляем исходный zip
        os.remove(zip_path)

        # Если внутри только одна директория — переносим её содержимое
        extracted_items = os.listdir(tmp_folder)
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(tmp_folder, extracted_items[0])):
            only_folder = os.path.join(tmp_folder, extracted_items[0])
            for item in os.listdir(only_folder):
                s = os.path.join(only_folder, item)
                d = os.path.join(upload_folder, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
        else:
            # Если структура сложнее — переносим всё как есть
            for item in extracted_items:
                s = os.path.join(tmp_folder, item)
                d = os.path.join(upload_folder, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

        # Удаляем временную директорию
        shutil.rmtree(tmp_folder)

        return "Файлы успешно загружены и обработаны", 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Ошибка при обработке архива: {str(e)}", 500


@editor_bp.route("/delete_test", methods=["POST"])
def delete_test():
    from app.db import db_app
    test_id = request.form.get("test_id")

    if not test_id:
        return "Не выбран тест", 400

    try:
        # Удаляем зависимые записи (пример, адаптируй под свою структуру)
        db_app.execute("DELETE FROM user_test_answers WHERE test_id = %s", (test_id,), returning=False)
        db_app.execute("DELETE FROM ask WHERE test_id = %s", (test_id,), returning=False)
        db_app.execute("DELETE FROM test WHERE id = %s", (test_id,), returning=False)
        return "Тест удалён", 200
    except Exception as e:
        print(e)
        return "Ошибка удаления теста", 500


@editor_bp.route("/delete_course", methods=["POST"])
def delete_course():
    course_id = request.form.get("course_id")

    if not course_id:
        return "Не выбран курс", 400

    try:
        # Удаление курса — каскадно всё удалится через ON DELETE CASCADE
        db_app.execute("DELETE FROM levels_course WHERE id = %s;", (course_id,), returning=False)
        return "Курс удалён", 200
    except Exception as e:
        print(e)
        return "Ошибка удаления курса", 500


@editor_bp.route("/update_test", methods=["POST"])
def update_test():
    test_id = request.form.get("test_id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    is_main = request.form.get("is_main") == 'true'

    if not test_id or not title:
        return jsonify({"success": False, "error": "ID теста и название обязательны"}), 400

    try:
        db_app.execute(
            "UPDATE test SET title = %s, description = %s, is_main = %s WHERE id = %s",
            (title, description, is_main, test_id),
            returning=False
        )
        return jsonify({"success": True, "message": "Тест успешно обновлен"})
    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": "Ошибка при обновлении теста"}), 500


@editor_bp.route("/get_test_data", methods=["POST"])
def get_test_data():
    """Получение данных теста по ID"""
    data = request.get_json()
    test_id = data.get('test_id')

    if not test_id:
        return jsonify({"success": False, "error": "ID теста не указан"}), 400

    try:
        test = db_app.fetch_one(
            "SELECT id, title, description, is_main FROM test WHERE id = %s",
            (test_id,)
        )

        if test:
            return jsonify({
                "success": True,
                "test": {
                    "id": test["id"],
                    "title": test["title"],
                    "description": test["description"] or "",
                    "is_main": test["is_main"]
                }
            })
        else:
            return jsonify({"success": False, "error": "Тест не найден"}), 404

    except Exception as e:
        print(f"Ошибка при получении данных теста: {e}")
        return jsonify({"success": False, "error": "Ошибка при получении данных теста"}), 500


@editor_bp.route("/get_test_questions", methods=["POST"])
def get_test_questions():
    """Получение всех вопросов теста с ответами"""
    data = request.get_json()
    test_id = data.get('test_id')

    if not test_id:
        return jsonify({"success": False, "error": "ID теста не указан"}), 400

    try:
        # Получаем вопросы теста
        questions = db_app.fetch_all(
            "SELECT id, content FROM ask WHERE test_id = %s ORDER BY id",
            (test_id,)
        )

        # Для каждого вопроса получаем ответы
        for question in questions:
            answers = db_app.fetch_all(
                "SELECT id, content FROM answer WHERE ask_id = %s ORDER BY id",
                (question["id"],)
            )
            question["answers"] = answers

        return jsonify({
            "success": True,
            "questions": questions
        })

    except Exception as e:
        print(f"Ошибка при получении вопросов теста: {e}")
        return jsonify({"success": False, "error": "Ошибка при получении вопросов теста"}), 500


@editor_bp.route("/update_question", methods=["POST"])
def update_question():
    """Обновление вопроса теста"""
    question_id = request.form.get("question_id")
    content = request.form.get("content", "").strip()

    if not question_id or not content:
        return jsonify({"success": False, "error": "ID вопроса и содержание обязательны"}), 400

    try:
        db_app.execute(
            "UPDATE ask SET content = %s WHERE id = %s",
            (content, question_id),
            returning=False
        )
        return jsonify({"success": True, "message": "Вопрос успешно обновлен"})
    except Exception as e:
        print(f"Ошибка при обновлении вопроса: {e}")
        return jsonify({"success": False, "error": "Ошибка при обновлении вопроса"}), 500


@editor_bp.route("/update_answer", methods=["POST"])
def update_answer():
    """Обновление ответа на вопрос"""
    answer_id = request.form.get("answer_id")
    content = request.form.get("content", "").strip()

    if not answer_id or not content:
        return jsonify({"success": False, "error": "ID ответа и содержание обязательны"}), 400

    try:
        db_app.execute(
            "UPDATE answer SET content = %s WHERE id = %s",
            (content, answer_id),
            returning=False
        )
        return jsonify({"success": True, "message": "Ответ успешно обновлен"})
    except Exception as e:
        print(f"Ошибка при обновлении ответа: {e}")
        return jsonify({"success": False, "error": "Ошибка при обновлении ответа"}), 500


@editor_bp.route("/add_question", methods=["POST"])
def add_question():
    """Добавление нового вопроса к тесту"""
    test_id = request.form.get("test_id")
    content = request.form.get("content", "").strip()

    if not test_id or not content:
        return jsonify({"success": False, "error": "ID теста и содержание вопроса обязательны"}), 400

    try:
        question_id = db_app.insert("ask", {
            "test_id": test_id,
            "content": content,
        })

        return jsonify({
            "success": True,
            "message": "Вопрос успешно добавлен",
            "question_id": question_id
        })
    except Exception as e:
        print(f"Ошибка при добавлении вопроса: {e}")
        return jsonify({"success": False, "error": "Ошибка при добавлении вопроса"}), 500


@editor_bp.route("/add_answer", methods=["POST"])
def add_answer():
    """Добавление нового ответа к вопросу"""
    question_id = request.form.get("question_id")
    content = request.form.get("content", "").strip()

    if not question_id or not content:
        return jsonify({"success": False, "error": "ID вопроса и содержание ответа обязательны"}), 400

    try:
        answer_id = db_app.insert("answer", {
            "ask_id": question_id,
            "content": content,
        })

        return jsonify({
            "success": True,
            "message": "Ответ успешно добавлен",
            "answer_id": answer_id
        })
    except Exception as e:
        print(f"Ошибка при добавлении ответа: {e}")
        return jsonify({"success": False, "error": "Ошибка при добавлении ответа"}), 500


@editor_bp.route("/delete_question", methods=["POST"])
def delete_question():
    """Удаление вопроса и связанных ответов"""
    question_id = request.form.get("question_id")

    if not question_id:
        return jsonify({"success": False, "error": "ID вопроса не указан"}), 400

    try:
        # Ответы удалятся каскадно благодаря ON DELETE CASCADE
        db_app.execute(
            "DELETE FROM ask WHERE id = %s",
            (question_id,),
            returning=False
        )
        return jsonify({"success": True, "message": "Вопрос успешно удален"})
    except Exception as e:
        print(f"Ошибка при удалении вопроса: {e}")
        return jsonify({"success": False, "error": "Ошибка при удалении вопроса"}), 500


@editor_bp.route("/delete_answer", methods=["POST"])
def delete_answer():
    """Удаление ответа"""
    answer_id = request.form.get("answer_id")

    if not answer_id:
        return jsonify({"success": False, "error": "ID ответа не указан"}), 400

    try:
        db_app.execute(
            "DELETE FROM answer WHERE id = %s",
            (answer_id,),
            returning=False
        )
        return jsonify({"success": True, "message": "Ответ успешно удален"})
    except Exception as e:
        print(f"Ошибка при удалении ответа: {e}")
        return jsonify({"success": False, "error": "Ошибка при удалении ответа"}), 500


@editor_bp.route("/get_full_test_data", methods=["POST"])
def get_full_test_data():
    """Получение полных данных теста (тест + все вопросы + все ответы)"""
    data = request.get_json()
    test_id = data.get('test_id')

    if not test_id:
        return jsonify({"success": False, "error": "ID теста не указан"}), 400

    try:
        # Получаем данные теста
        test = db_app.fetch_one(
            "SELECT id, title, description, is_main FROM test WHERE id = %s",
            (test_id,)
        )

        if not test:
            return jsonify({"success": False, "error": "Тест не найден"}), 404

        # Получаем вопросы теста
        questions = db_app.fetch_all(
            "SELECT id, content FROM ask WHERE test_id = %s ORDER BY id",
            (test_id,)
        )

        # Для каждого вопроса получаем ответы
        for question in questions:
            answers = db_app.fetch_all(
                "SELECT id, content FROM answer WHERE ask_id = %s ORDER BY id",
                (question["id"],)
            )
            question["answers"] = answers

        return jsonify({
            "success": True,
            "test": test,
            "questions": questions
        })

    except Exception as e:
        print(f"Ошибка при получении полных данных теста: {e}")
        return jsonify({"success": False, "error": "Ошибка при получении данных теста"}), 500


@editor_bp.route("/update_course", methods=["POST"])
def update_course():
    course_id = request.form.get("course_id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not course_id or not title:
        return jsonify({"success": False, "error": "ID курса и название обязательны"}), 400

    try:
        db_app.execute(
            "UPDATE levels_course SET title = %s, description = %s WHERE id = %s",
            (title, description, course_id),
            returning=False
        )
        return jsonify({"success": True, "message": "Курс успешно обновлен"})
    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": "Ошибка при обновлении курса"}), 500


@editor_bp.route("/update_lesson", methods=["POST"])
def update_lesson():
    lesson_id = request.form.get("lesson_id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not lesson_id or not title:
        return jsonify({"success": False, "error": "ID урока и название обязательны"}), 400

    try:
        db_app.execute(
            "UPDATE lessons SET title = %s, description = %s WHERE id = %s",
            (title, description, lesson_id),
            returning=False
        )
        return jsonify({"success": True, "message": "Урок успешно обновлен"})
    except Exception as e:
        print(f"Ошибка при обновлении урока: {e}")
        return jsonify({"success": False, "error": "Ошибка при обновлении урока"}), 500


@editor_bp.route("/update_content", methods=["POST"])
def update_content():
    content_id = request.form.get("content_id")
    title = request.form.get("title", "").strip()
    content_text = request.form.get("content", "").strip()
    content_type = request.form.get("type", "txt")  # Добавлено поле type

    if not content_id or not title:
        return jsonify({"success": False, "error": "ID контента и заголовок обязательны"}), 400

    try:
        db_app.execute(
            "UPDATE lesson_content SET title = %s, content = %s, type = %s WHERE id = %s",
            (title, content_text, content_type, content_id),
            returning=False
        )
        return jsonify({"success": True, "message": "Контент успешно обновлен"})
    except Exception as e:
        print(f"Ошибка при обновлении контента: {e}")
        return jsonify({"success": False, "error": "Ошибка при обновлении контента"}), 500


@editor_bp.route("/get_lesson_data", methods=["POST"])
def get_lesson_data():
    """Функция для получения данных урока по ID (для AJAX запросов)"""
    data = request.get_json()
    lesson_id = data.get('lesson_id')

    if not lesson_id:
        return jsonify({"success": False, "error": "ID урока не указан"}), 400

    try:
        lesson = db_app.fetch_one(
            "SELECT id, title, description FROM lessons WHERE id = %s",
            (lesson_id,)
        )

        if lesson:
            return jsonify({
                "success": True,
                "lesson": {
                    "id": lesson["id"],
                    "title": lesson["title"],
                    "description": lesson["description"] or ""
                }
            })
        else:
            return jsonify({"success": False, "error": "Урок не найден"}), 404

    except Exception as e:
        print(f"Ошибка при получении данных урока: {e}")
        return jsonify({"success": False, "error": "Ошибка при получении данных урока"}), 500


@editor_bp.route("/get_content_data", methods=["POST"])
def get_content_data():
    """Функция для получения данных контента по ID (для AJAX запросов)"""
    data = request.get_json()
    content_id = data.get('content_id')

    if not content_id:
        return jsonify({"success": False, "error": "ID контента не указан"}), 400

    try:
        content = db_app.fetch_one(
            "SELECT id, title, content, page_num FROM lesson_content WHERE id = %s",
            (content_id,)
        )

        if content:
            return jsonify({
                "success": True,
                "content": {
                    "id": content["id"],
                    "title": content["title"] or "",
                    "content": content["content"] or "",
                    "page_num": content["page_num"]
                }
            })
        else:
            return jsonify({"success": False, "error": "Контент не найден"}), 404

    except Exception as e:
        print(f"Ошибка при получении данных контента: {e}")
        return jsonify({"success": False, "error": "Ошибка при получении данных контента"}), 500


@editor_bp.route('/check')
def check():
    main_courses = db_app.fetch_all(
        "SELECT * FROM levels_course ORDER BY step_index;")

    for course in main_courses:
        request = "SELECT * FROM lessons WHERE course_id = %s;"
        course["lessons"] = db_app.fetch_all(
            sql=request, params=(course["id"],))

    return render_template('check_function_1.html', courses_data=main_courses)