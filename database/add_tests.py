import csv
import psycopg2
from config import db_params_2

# Подключение к базе данных
conn = psycopg2.connect(
    **db_params_2
)
conn.set_client_encoding('UTF8')
cur = conn.cursor()

# Заменить на путь к твоему CSV-файлу
csv_file_path = 'questions.csv'

# Предположим, что каждая строка CSV содержит только текст вопроса
with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        content = row[0].strip()
        if content:  # Пропуск пустых строк
            cur.execute(
                "INSERT INTO ask (test_id, content) VALUES (%s, %s)",
                (1, content)  # test_id = 1
            )

conn.commit()
cur.close()
conn.close()
