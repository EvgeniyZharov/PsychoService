# app/main/routes.py
from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/api/documents/terms')
def terms():
    return render_template('terms_content.html')


@main_bp.route('/api/documents/rules')
def rules():
    return render_template('rules_content.html')


@main_bp.route('/checking')
def check_work():
    from app.db import db_app
    from collections import defaultdict
    main_courses = [{"id": 0, "Title": " "}]
    main_courses.extend(db_app.fetch_all("SELECT * FROM levels_course ORDER BY step_index;"))
    all_lessons = db_app.fetch_all(
        "SELECT * FROM lessons ORDER BY course_id, id;")
    all_content = db_app.fetch_all(
        "SELECT * FROM lesson_content ORDER BY lesson_id, id;"
    )
    content_by_lesson = defaultdict(list)
    for content in all_content:
        content_by_lesson[content["lesson_id"]].append(content)

    lessons_by_course = defaultdict(list)
    for lesson in all_lessons:
        lesson["content"] = content_by_lesson.get(lesson["id"], [])
        lessons_by_course[lesson["course_id"]].append(lesson)

    # Присваиваем уроки курсам
    for course in main_courses:
        course["lessons"] = lessons_by_course.get(course["id"], [])

    return render_template('check_function_2.html', courses_data=main_courses)
