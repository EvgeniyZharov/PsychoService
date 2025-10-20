import psycopg2
from config import db_params

# Параметры подключения
# DB_HOST = "localhost"
# DB_PORT = "5432"
# DB_NAME = "your_database"
# DB_USER = "your_username"
# DB_PASSWORD = "your_password"

# Таблицы, которые нужно обработать
tables = [
    "answers", "asks", "author_courses", "content", "guest_emails", "lessons",
    "levels_course", "main_courses", "questions", "reset_tokens", "role_test_questions",
    "test_skills", "test_themes", "traits", "user_courses_progress", "user_goals",
    "user_profiles", "user_tests_completed", "user_traits", "users_tests", "users_tests_results"
]

# Подключение к базе данных
conn = psycopg2.connect(
    **db_params
)

cursor = conn.cursor()

output_lines = []

# Обработка каждой таблицы
for table in tables:
    cursor.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position;
    """, (table,))

    columns = cursor.fetchall()

    output_lines.append("+++++")
    output_lines.append(f"Таблица: {table}")
    for column in columns:
        output_lines.append(column[0])
    output_lines.append("+++++")

cursor.close()
conn.close()

# Сохраняем в файл
with open("tables_structure_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("Структура таблиц сохранена в 'tables_structure_output.txt'")
