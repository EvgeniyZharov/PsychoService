from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.db import db_app
from app.courses.services import add_user_points
from app.auth.decorators import require_user_email
from app.tests.logic import (
    save_test_results_for_user,
    check_question_condition,
    get_previous_step_by_condition,
    save_user_answer,
    get_top_n_traits
)

tests_bp = Blueprint('tests', __name__)


@tests_bp.route('/choose_theme')
# @require_user_email
def choose_theme():
    # Список доступных тем тестов.
    show_email_prompt = 'user_email' not in session and not session.get('email_collected')
    themes = db_app.fetch_all("SELECT * FROM test ORDER BY id")
    return render_template('choose_theme.html', themes=themes, show_email_prompt=show_email_prompt)


@tests_bp.route('/start_test/<int:theme_id>')
# @require_user_email
def start_test(theme_id):
    # Инициализация теста и переход к первому вопросу.
    questions = db_app.fetch_all(
        "SELECT id AS q_id, content, condition FROM ask WHERE test_id=%s ORDER BY id",
        (theme_id,)
    )

    if not questions:
        flash("Нет вопросов в выбранной теме.", "error")
        return redirect(url_for('tests.choose_theme'))

    session['current_theme_id'] = theme_id
    session['answers'] = []
    session['test_state'] = {
        'theme_id': theme_id,
        'current_step': 1,
        'answers': [],
        'total_questions': len(questions)
    }
    session.modified = True
    return redirect(url_for('tests.test_step_by_theme', theme_id=theme_id, step=1))


@tests_bp.route('/test_theme/<int:theme_id>/step/<int:step>', methods=['GET', 'POST'])
# @require_user_email
def test_step_by_theme(theme_id, step):
    """Основной маршрут прохождения теста с условным пропуском вопросов."""
    if 'test_state' not in session or session['test_state']['theme_id'] != theme_id:
        return redirect(url_for('tests.start_test', theme_id=theme_id))

    questions = db_app.fetch_all(
        "SELECT id AS q_id, content, condition FROM ask WHERE test_id=%s ORDER BY id",
        (theme_id,)
    )
    session['test_state']['total_questions'] = len(questions)
    session.modified = True

    if step > len(questions):
        return redirect(url_for('tests.test_result'))

    question_raw = questions[step - 1]
    user_answers = session['test_state']['answers']

    # Проверка условия вопроса
    if not check_question_condition(question_raw.get('condition'), user_answers, step):
        return redirect(url_for('tests.test_step_by_theme', theme_id=theme_id, step=step + 1))

    answers_data = db_app.fetch_all("SELECT id, content FROM answer WHERE ask_id=%s", (question_raw["q_id"],))
    question = {
        "id": question_raw["q_id"],
        "text": question_raw["content"],
        "condition": question_raw.get('condition'),
        "options": [{"id": ans["id"], "text": ans["content"]} for ans in answers_data]
    }

    if request.method == 'POST':
        answer_text = request.form.get("answer")
        if not answer_text:
            flash("Пожалуйста, выберите вариант ответа.", "warning")
            return redirect(url_for('tests.test_step_by_theme', theme_id=theme_id, step=step))

        # Сохраняем ответ в сессию
        current_index = step - 1
        if current_index >= len(user_answers):
            user_answers.append(answer_text)
        else:
            user_answers[current_index] = answer_text
        session['test_state']['answers'] = user_answers.copy()

        # Сохраняем в БД
        selected_answer = next((opt for opt in question["options"] if opt["text"] == answer_text), None)
        if selected_answer and "user_email" in session:
            save_user_answer(session["user_email"], theme_id, question["id"], selected_answer["id"])

        session['test_state']['current_step'] = step + 1
        session.modified = True
        return redirect(url_for('tests.test_step_by_theme', theme_id=theme_id, step=step + 1))

    # Предыдущий ответ для отображения
    previous_answer = None
    if step - 1 < len(user_answers):
        previous_answer = user_answers[step - 1]

    return render_template('test.html', question=question, step=step,
                           theme_id=theme_id, previous_answer=previous_answer)


@tests_bp.route('/test_theme/<int:theme_id>/step/<int:step>/back')
# @require_user_email
def test_step_back(theme_id, step):
    # Возврат на предыдущий шаг с учётом пропущенных вопросов.
    if 'test_state' not in session or session['test_state']['theme_id'] != theme_id:
        return redirect(url_for('tests.choose_theme'))

    if step <= 1:
        return redirect(url_for('tests.test_step_by_theme', theme_id=theme_id, step=1))

    prev_step = get_previous_step_by_condition(step, session['test_state']['answers'])
    session['test_state']['current_step'] = prev_step
    session.modified = True
    return redirect(url_for('tests.test_step_by_theme', theme_id=theme_id, step=prev_step))


@tests_bp.route('/test/result')
# @require_user_email
def test_result():
    # Отображение результатов теста и сохранение характеристик.
    answers = session.get('answers', [])
    theme_id = session.get('current_theme_id')
    user_email = session.get('user_email')

    if not theme_id or not user_email:
        flash("Тест не найден или сессия истекла.", "error")
        return redirect(url_for('tests.choose_theme'))

    # Начисление баллов
    completed_first_time = not db_app.fetch_one(
        "SELECT 1 FROM user_tests_completed WHERE user_email=%s AND test_id=%s",
        (user_email, theme_id)
    )
    add_user_points(user_email, 15 if completed_first_time else 5, 'test')
    save_test_results_for_user(user_email, theme_id)

    # Получаем топ характеристики
    test_info = db_app.fetch_one("SELECT is_main FROM test WHERE id=%s", (theme_id,))
    if test_info and test_info.get("is_main"):
        res = get_top_n_traits(user_email, theme_id, change_profile=True)
    else:
        res = get_top_n_traits(user_email, theme_id, top_trait=1)

    # Очистка сессии
    session.pop('answers', None)
    session.pop('current_theme_id', None)
    session.pop('test_state', None)
    session.modified = True

    return render_template("test_result.html", answers=answers, res=res, theme_id=theme_id)
