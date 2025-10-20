from flask import Blueprint, render_template, request, redirect, url_for, session
from app.db import db_app
from app.courses.services import add_user_points
from app.tests.logic import save_test_results_for_user

tests_bp = Blueprint('tests', __name__)


@tests_bp.route('/choose_theme')
def choose_theme():
    show_email_prompt = 'user' not in session and not session.get('email_collected')
    themes = db_app.fetch_all("SELECT * FROM test ORDER BY id")
    return render_template('choose_theme.html',
                           themes=themes,
                           show_email_prompt=show_email_prompt)


@tests_bp.route('/start_test/<int:theme_id>')
def start_test(theme_id):
    questions = db_app.fetch_all("""
        SELECT id as q_id, ask as text 
        FROM ask
        WHERE test_id = %s
        ORDER BY id
    """, (theme_id,))

    if not questions:
        return "Нет вопросов в выбранной теме", 404

    session['current_theme_id'] = theme_id
    session['answers'] = []

    return redirect(url_for('tests.test_step_by_theme', theme_id=theme_id, step=1))


@tests_bp.route('/test_theme/<int:theme_id>/step/<int:step>', methods=['GET', 'POST'])
def test_step_by_theme(theme_id, step):
    questions = db_app.fetch_all("""
        SELECT id as q_id, content
        FROM ask
        WHERE test_id = %s
        ORDER BY id
    """, (theme_id,))

    if step > len(questions):
        return redirect(url_for('tests.test_result'))

    question = questions[step - 1]
    answers = db_app.fetch_all("SELECT id, content FROM answer WHERE ask_id = %s", (question["q_id"],))
    question = {"id": question["q_id"],
                "text": question["content"],
                "options": []}
    for elem in answers:
        question["options"].append({"id": elem["id"], "text": elem["content"]})
    # options = [a["content"] for a in answers]

    if request.method == 'POST':
        answer = request.form.get("answer")
        session["answers"].append(answer)
        # Найти выбранный объект ответа
        selected_answer = next((opt for opt in question["options"] if opt["text"] == answer), None)
        if selected_answer and "user" in session:
            from app.tests.logic import save_user_answer
            save_user_answer(
                user_email=session["user"]["email"],
                test_id=theme_id,
                ask_id=question["id"],
                answer_id=selected_answer["id"]
            )
        session.modified = True
        return redirect(url_for('tests.test_step_by_theme', theme_id=theme_id, step=step + 1))

    return render_template('test.html', question=question, step=step, theme_id=theme_id)


# @tests_bp.route('/test/<int:test_id>', methods=['GET', 'POST'])
# def test(test_id):
#     completed = session.get("completed_tests", [])
#     if str(test_id) not in completed:
#         completed.append(str(test_id))
#         session["completed_tests"] = completed
#
#     questions = db_app.fetch_all("""
#         SELECT text, options
#         FROM test_questions
#         WHERE test_id = %s
#         ORDER BY question_index
#     """, (test_id,))
#
#     return render_template('test.html', questions=questions)


@tests_bp.route('/test/result')
def test_result():
    from app.tests.logic import get_top_n_traits
    answers = session.get('answers', [])
    theme_id = session.get('current_theme_id')
    if 'user' in session and theme_id:
        if db_app.fetch_one("""
        SELECT 1 FROM user_tests_completed WHERE user_email = %s AND test_id = %s
    """, (session['user']['email'], theme_id)):
            add_user_points(session['user']['email'], 5, 'test')
        else:
            add_user_points(session['user']['email'], 15, 'test')
        save_test_results_for_user(session['user']['email'], theme_id)
        if db_app.fetch_one("""
                SELECT is_main FROM test WHERE id = %s
            """, (theme_id,))["is_main"]:
            res = get_top_n_traits(session['user']['email'], theme_id, change_profile=True)
        else:
            res = get_top_n_traits(session['user']['email'], theme_id, top_trait=1)


        return render_template("test_result.html", answers=answers, res=res)


@tests_bp.route('/submit_test', methods=['POST'])
def submit_test():
    return render_template('test_result.html')
