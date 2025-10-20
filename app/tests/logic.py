from app.db import db_app


def save_test_results_for_user(email, theme_id):
    """
    Сохраняет результат прохождения теста пользователем в БД.
    """
    db_app.insert('user_tests_completed', {
        "user_email": email,
        "test_id": theme_id
    }, returning=False)


def save_user_answer(user_email, test_id, ask_id, answer_id):
    """
    Сохраняет выбранный ответ пользователя на вопрос теста.
    Если запись уже существует — обновляет answer_id.
    """
    existing = db_app.fetch_one("""
        SELECT id FROM user_test_answers
        WHERE user_email = %s AND test_id = %s AND ask_id = %s
    """, (user_email, test_id, ask_id))

    if existing:
        db_app.execute("""
            UPDATE user_test_answers
            SET answer_id = %s
            WHERE id = %s
        """, (answer_id, existing["id"]), returning=False)
    else:
        db_app.insert("user_test_answers", {
            "user_email": user_email,
            "test_id": test_id,
            "ask_id": ask_id,
            "answer_id": answer_id
        }, returning=False)


def calculate_and_save_user_traits(user_email, test_id):
    # Получаем все ответы пользователя с информацией о очках и признаках
    query = """
        SELECT a.trait_id, s.base_score, SUM(a.score) as total_score
        FROM user_test_answers uta
        JOIN answer a ON uta.answer_id = a.id
        JOIN skills s ON a.trait_id = s.id
        WHERE uta.user_email = %s AND uta.test_id = %s
        GROUP BY a.trait_id, s.base_score
    """
    results = db_app.fetch_all(query, (user_email, test_id))

    # Для каждого признака сохраняем процент
    for row in results:
        trait_id = row['trait_id']
        base_score = row['base_score']
        total_score = row['total_score']
        percent = round((total_score / base_score) * 100, 2) if base_score else 0

        # Вставляем или обновляем запись в user_traits
        db_app.execute("""
            INSERT INTO user_traits (user_email, trait_id, percent, test_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_email, trait_id, test_id)
            DO UPDATE SET percent = EXCLUDED.percent
        """, (user_email, trait_id, percent, test_id))


def calculate_and_save_user_traits2(user_email, test_id):
    # Получаем все ответы пользователя с информацией об очках и признаках
    query = """
    SELECT 
        sal.skill_id AS trait_id,
        ROUND(SUM(a.score)::numeric / s.base_score * 100, 2) AS percent
    FROM 
        skill_ask_link sal
    JOIN 
        user_test_answers uta ON sal.ask_id = uta.ask_id
    JOIN 
        answer a ON uta.answer_id = a.id AND uta.ask_id = a.ask_id
    JOIN 
        skills s ON sal.skill_id = s.id
    WHERE 
        uta.user_email = %s AND uta.test_id = %s
    GROUP BY 
        sal.skill_id, s.base_score;"""
    result = db_app.fetch_all(query, (user_email, test_id,))

    return result


def get_top_n_traits(user_email, test_id, top_trait: int = 3, change_profile: bool = False):
    """
    Принимает список словарей с полями:
        - trait_id: ID характеристики
        - percent: процент выраженности
    Возвращает 3 характеристики с наибольшим значением percent.
    """

    traits_results = calculate_and_save_user_traits2(user_email, test_id)
    if not traits_results:
        return []

    # Сортируем по убыванию процента
    sorted_traits = sorted(traits_results, key=lambda x: x['percent'], reverse=True)

    # Берем топ-3
    traits = sorted_traits[:top_trait]

    trait_ids = [trait['trait_id'] for trait in traits]
    # Получаем данные из таблицы skills
    query = "SELECT id, title, description FROM skills WHERE id = ANY(%s);"
    rows = db_app.fetch_all(query, (trait_ids,))
    # Преобразуем в словарь для быстрого доступа
    skills = {row['id']: row for row in rows}

    # Находим основную характеристику
    primary = skills[traits[0]['trait_id']]['title']
    if change_profile:
    # Остальные — описания
        descriptions = [
            skills[traits[1]['trait_id']]['description'],
            skills[traits[2]['trait_id']]['description']
        ]

        # Формируем итоговую строку
        summary = f"{descriptions[0].lower()} {descriptions[1].lower()} {primary}"

        query = """
                UPDATE user_profiles
                SET personality_type = %s
                WHERE email = %s
            """
        db_app.execute(query, (summary, user_email), returning=False)

        return summary
    else:
        test_title = db_app.fetch_one("""
        SELECT title FROM test
        WHERE id = %s
    """, (test_id,))["title"]
        # Добавление записи в таблицу user_characters
        db_app.insert('user_characters', {
            "user_email": user_email,
            "test_id": test_id,
            "test_title": test_title,
            "character_title": primary
        }, returning=False)
        return primary




if __name__ == "__main__":
    print(get_top_n_traits("admin@gmail.com", 8))
