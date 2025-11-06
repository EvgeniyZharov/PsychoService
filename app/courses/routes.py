from flask import Blueprint, render_template, request, redirect, url_for, session
from collections import defaultdict
from app.db import db_app
from app.courses.services import (
    get_lesson_by_id,
    get_next_lesson,
    get_previous_lesson,
    add_user_points
)

courses_bp = Blueprint('courses', __name__)


@courses_bp.route('/basic_courses')
def basic_courses():
    show_email_prompt = 'user' not in session and not session.get('email_collected')
    courses = db_app.fetch_all("SELECT * FROM author_courses ORDER BY id")
    return render_template("basic_courses.html", courses=courses, show_email_prompt=show_email_prompt)


@courses_bp.route('/submit_email', methods=['POST'])
def submit_email():
    email = request.form.get('email')
    if email:
        session['email_collected'] = True
        session['guest_email'] = email
        existing = db_app.fetch_one("SELECT * FROM guest_emails WHERE email = %s", (email,))
        if not existing:
            db_app.insert("guest_emails", {"email": email}, returning=False)
    return redirect(request.referrer or url_for('courses.courses'))


@courses_bp.route('/course/<int:course_id>')
def courses(course_id):
    show_email_prompt = 'user' not in session and not session.get('email_collected')

    lessons = db_app.fetch_all("SELECT * FROM levels_course WHERE course_id = %s", (course_id,))


    available_level = 0
    result = None
    if 'user' in session:
    # Проверяем, пройден ли текущий урок
        result = db_app.fetch_one(
            """
            SELECT COALESCE(lc.step_index, 0) as result
            FROM (SELECT %s as user_email) params
            LEFT JOIN user_lesson_completed ulc ON ulc.user_email = params.user_email
            LEFT JOIN levels_course lc ON lc.id = ulc.lesson_id
            ORDER BY ulc.last_time DESC 
            LIMIT 1;
            """,
            (session['user']['email'],)
        )["result"]
    available_level = result if result else 0
    available_level += 1

    steps = defaultdict(lambda: defaultdict(list))
    for lesson in lessons:
        lesson_row = db_app.fetch_one(
            "SELECT id FROM lessons WHERE course_id = %s ORDER BY id ASC LIMIT 1",
            (lesson["id"],)
        )

        lesson_id = lesson_row["id"] if lesson_row else None
        lesson["lesson_id"] = lesson_id
        steps[lesson["step_index"]][lesson["level_index"]].append(lesson)

        if lesson["step_index"] <= available_level:
            lesson["color"] = 'bg-green-500'
            lesson["open"] = "true"
        else:
            lesson["color"] = 'bg-gray-400'
            lesson["open"] = "false"

    steps = dict(steps)
    return render_template("course.html",
                           course_id=course_id,
                           steps=steps,
                           show_email_prompt=show_email_prompt)


@courses_bp.route('/lesson/<course_id>/<lesson_id>', methods=['GET', 'POST'])
def lesson(course_id, lesson_id):
    if lesson_id == '-1':
        lesson_id = db_app.fetch_one("""
            SELECT id FROM lessons WHERE course_id = %s limit 1;""", (course_id, ))["id"]
        session["course_id"] = course_id
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        return render_template('fail_course.html'), 404
    # course_id = db_app.fetch_one("SELECT course_id FROM lessons WHERE id = %s;", (lesson_id,))["course_id"]
    prev_lesson = get_previous_lesson(lesson)
    next_lesson = get_next_lesson(lesson)

    course_id = int(course_id)
    content_items = db_app.fetch_all(
        "SELECT * FROM lesson_content WHERE lesson_id = %s ORDER BY id;", (lesson_id, )
        # "SELECT * FROM lesson_content WHERE page_num = %s and course_id = %s ORDER BY id;", (lesson_id, course_id)
    )
    for elem in content_items:

        if elem["title"] == "nan":
            elem["title"] = " "
    return render_template(
        "lesson.html",
        lesson_id=lesson_id,
        lesson=lesson,
        lesson_pages=content_items,
        prev_lesson=prev_lesson,
        next_lesson=next_lesson,
        course_id=course_id,
        size=30
    )


@courses_bp.route('/end_lesson/<int:course_id>', methods=['GET', 'POST'])
def end_lesson(course_id):
    """
    Обрабатывает нажатие ссылки для начала курса
    Выполняет необходимые действия и перенаправляет на страницу курса
    """

    if 'user' in session:
        lesson_id = session["course_id"]
        if db_app.fetch_one("""
            SELECT 1 FROM user_lesson_completed WHERE user_email = %s AND lesson_id = %s
        """, (session['user']['email'], course_id)):
            add_user_points(session['user']['email'], 10, 'course')
        else:
            db_app.insert('user_lesson_completed', {
                "user_email": session['user']['email'],
                "lesson_id": course_id
            }, returning=False)
            add_user_points(session['user']['email'], 30, 'course')

    return redirect(url_for('courses.courses', course_id=1))
