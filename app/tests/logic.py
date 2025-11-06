from app.db import db_app


def check_question_condition(condition_text, user_answers, current_question_number):
    # Проверяет условие для вопроса на основе предыдущих ответов пользователя.
    if not condition_text or not condition_text.strip():
        return True  # Если условие не задано, вопрос показывается всегда

    try:
        context = {f'answer_{i+1}': ans for i, ans in enumerate(user_answers)}
        context['current_question'] = current_question_number
        return bool(eval(condition_text, {"__builtins__": {}}, context))
    except Exception as e:
        print(f"Ошибка при проверке условия '{condition_text}': {e}")
        return True


def get_previous_step_by_condition(current_step, user_answers):
    # Определяет шаг назад с учётом условного пропуска.
    # Пример 1: если текущий шаг 5 — вернуться на 2
    if current_step == 5:
        return 2

    # Пример 2: если на шаге 3 выбран "Нет", вернуться на 1
    if len(user_answers) >= 3 and user_answers[2] == "Нет":
        return 1

    return max(1, current_step - 1)


def save_test_results_for_user(email, theme_id):
    db_app.insert('user_tests_completed', {
        "user_email": email,
        "test_id": theme_id
    }, returning=False)


def save_user_answer(user_email, test_id, ask_id, answer_id):
    existing = db_app.fetch_one("""
        SELECT id FROM user_test_answers
        WHERE user_email=%s AND test_id=%s AND ask_id=%s
    """, (user_email, test_id, ask_id))

    if existing:
        db_app.execute("""
            UPDATE user_test_answers
            SET answer_id=%s
            WHERE id=%s
        """, (answer_id, existing["id"]), returning=False)
    else:
        db_app.insert("user_test_answers", {
            "user_email": user_email,
            "test_id": test_id,
            "ask_id": ask_id,
            "answer_id": answer_id
        }, returning=False)


def calculate_and_save_user_traits2(user_email, test_id):
    query = """
    SELECT 
        sal.skill_id AS trait_id,
        ROUND(SUM(a.score)::numeric / s.base_score * 100, 2) AS percent
    FROM skill_ask_link sal
    JOIN user_test_answers uta ON sal.ask_id = uta.ask_id
    JOIN answer a ON uta.answer_id = a.id AND uta.ask_id = a.ask_id
    JOIN skills s ON sal.skill_id = s.id
    WHERE uta.user_email=%s AND uta.test_id=%s
    GROUP BY sal.skill_id, s.base_score
    """
    return db_app.fetch_all(query, (user_email, test_id))


def get_top_n_traits(user_email, test_id, top_trait=3, change_profile=False):
    traits_results = calculate_and_save_user_traits2(user_email, test_id)
    if not traits_results:
        return []

    sorted_traits = sorted(traits_results, key=lambda x: x['percent'], reverse=True)
    traits = sorted_traits[:top_trait]

    trait_ids = [t['trait_id'] for t in traits]
    skills_data = db_app.fetch_all("SELECT id, title, description FROM skills WHERE id = ANY(%s);", (trait_ids,))
    skills = {s['id']: s for s in skills_data}

    primary = skills[traits[0]['trait_id']]['title']

    if change_profile and len(traits) > 2:
        descriptions = [skills[traits[1]['trait_id']]['description'],
                        skills[traits[2]['trait_id']]['description']]
        summary = f"{descriptions[0].lower()} {descriptions[1].lower()} {primary}"
        db_app.execute("UPDATE user_profiles SET personality_type=%s WHERE email=%s",
                       (summary, user_email), returning=False)
        return summary

    test_title = db_app.fetch_one("SELECT title FROM test WHERE id=%s", (test_id,))["title"]
    db_app.insert('user_characters', {
        "user_email": user_email,
        "test_id": test_id,
        "test_title": test_title,
        "character_title": primary
    }, returning=False)
    return primary
