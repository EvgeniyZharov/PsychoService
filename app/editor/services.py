import pandas as pd
from app.db import db_app


def extract_questions_answers_from_csv(file_path):
    """
    Считывает CSV-файл и возвращает список словарей с вопросами и их ответами с баллами.
    """
    df = pd.read_csv(file_path)
    questions_data = []

    for i, row in df.iterrows():
        row_values = row.tolist()
        question_text = str(row_values[0]).strip()

        answers = []
        # Обрабатываем пары: ответ — балл
        for j in range(1, len(row_values) - 1, 2):
            answer_text = row_values[j]
            score = row_values[j + 1]

            if pd.notna(answer_text) and pd.notna(score):
                try:
                    score = int(score)
                except ValueError:
                    continue  # Пропустить если балл не число

                answers.append({
                    "text": str(answer_text).strip(),
                    "score": score
                })

        questions_data.append({
            "question": question_text,
            "answers": answers
        })

    return questions_data


def insert_questions_and_answers(db_app, test_id, questions_data):
    """
    Добавляет вопросы и ответы в базу данных:
    - db_app: объект для работы с БД
    - test_id: ID теста
    - questions_data: список вопросов с ответами (из extract_questions_answers_from_csv)
    """
    ask_keys = list()
    for item in questions_data:
        question = item["question"]
        answers = item["answers"]

        # Вставка вопроса
        ask_id = db_app.insert("ask", {
            "test_id": test_id,
            "content": question
        })
        ask_keys.append(ask_id)

        # Вставка ответов
        for answer in answers:
            answer_id = db_app.insert("answer", {
                "ask_id": ask_id,
                "content": answer["text"],
                "score": answer["score"]
            })

    return ask_keys

def extract_traits_from_csv(file_path):
    """
    Считывает traits.csv с русскими заголовками и возвращает список черт характера.
    """
    df = pd.read_csv(file_path)
    traits_data = []

    for _, row in df.iterrows():
        title = str(row.get("Тип акцентуации", "")).strip()
        description = str(row.get("Описание", "")).strip()
        raw_numbers = row.get("Номера утверждений", "")
        numbers = [int(n.strip()) for n in str(raw_numbers).split(",") if n.strip().isdigit()]

        traits_data.append({
            "title": title,
            "description": description,
            "question_numbers": numbers
        })

    return traits_data

def insert_traits_and_links(db_app, test_id, traits_data, ask_ids_ordered, base_score=10):
    """
    1. Добавляет каждую черту (skill) в таблицу `skills`.
    2. Для каждой черты добавляет связи в `skill_ask_link`.

    - db_app: объект для работы с базой
    - test_id: ID теста
    - traits_data: данные из extract_traits_from_csv()
    - ask_ids_ordered: список ask_id в том же порядке, что вопросы в файле
    """
    for trait in traits_data:
        title = trait["title"]
        description = trait["description"]
        question_numbers = trait["question_numbers"]

        # Преобразуем номера утверждений в ask_id
        linked_ask_ids = [
            ask_ids_ordered[n - 1]
            for n in question_numbers
            if 0 < n <= len(ask_ids_ordered)
        ]

        # 1. Добавляем навык в таблицу skills
        skill_id = db_app.insert("skills", {
            "test_id": test_id,
            "title": title,
            "description": description,
            "base_score": base_score
        })

        # 2. Добавляем связи skill <-> ask
        for ask_id in linked_ask_ids:
            db_app.insert("skill_ask_link", {
                "skill_id": skill_id,
                "ask_id": ask_id
            }, returning=False)


def load_data_ask_trait_to_db(test_id):
    result = extract_questions_answers_from_csv("asks.csv")
    ask_ids = insert_questions_and_answers(db_app, test_id=test_id, questions_data=result)
    result = extract_traits_from_csv("traits.csv")
    insert_traits_and_links(db_app, test_id=test_id, traits_data=result, ask_ids_ordered=ask_ids)

if __name__ == "__main__":
    load_data_ask_trait_to_db(test_id=1)