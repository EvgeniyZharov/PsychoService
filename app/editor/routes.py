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
    # save_path = os.path.join(os.getcwd(), filename)  # сохраняем в текущую папку

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
    # lesson_id = request.form.get("course_title")
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
            # lesson_id = lessons[int(row["lesson_id"]) - 1]["id"]
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
    if not test_id or not title:
        return "ID теста и название обязательны", 400
    try:
        db_app.execute(
            "UPDATE test SET title = %s, description = %s WHERE id = %s",
            (title, description, test_id),
            returning=False
        )
        return redirect(url_for("editor.editor"))
    except Exception as e:
        print(e)
        return "Ошибка при обновлении теста", 500


@editor_bp.route("/update_course", methods=["POST"])
def update_course():
    course_id = request.form.get("course_id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    if not course_id or not title:
        return "ID курса и название обязательны", 400
    try:
        db_app.execute(
            "UPDATE levels_course SET title = %s, description = %s WHERE id = %s",
            (title, description, course_id),
            returning=False
        )
        return redirect(url_for("editor.editor"))
    except Exception as e:
        print(e)
        return "Ошибка при обновлении курса", 500

