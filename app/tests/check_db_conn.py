import psycopg2
from psycopg2.extras import RealDictCursor

# Данные подключения к удалённому серверу PostgreSQL
conn = psycopg2.connect(
    host="193.162.143.84",        # IP-адрес или доменное имя
    port="5432",                    # Порт PostgreSQL (по умолчанию 5432)
    dbname="psycho_db",
    user="psycho_user",
    password="pass123"
)
def make_note():
    cur = conn.cursor()

    # Добавим тест
    cur.execute("""
        INSERT INTO test (title, description) 
        VALUES (%s, %s) 
        RETURNING id;
    """, ("Тест уверенности", "Оценивает уровень уверенности в себе."))

    test_id = cur.fetchone()[0]

    # Добавим вопросы
    asks = [
        ("Мне легко говорить «нет» другим людям.",),
        ("Я часто отказываюсь от своих желаний в пользу других.",)
    ]

    ask_ids = []
    for content in asks:
        cur.execute("""
            INSERT INTO ask (test_id, content)
            VALUES (%s, %s)
            RETURNING id;
        """, (test_id, content[0]))
        ask_ids.append(cur.fetchone()[0])

    # Добавим ответы
    for ask_id in ask_ids:
        cur.execute("""
            INSERT INTO answer (ask_id, score)
            VALUES (%s, %s), (%s, %s);
        """, (ask_id, 1, ask_id, 5))  # Пример: ответ с низким и высоким баллом

    # Добавим навыки
    cur.execute("""
        INSERT INTO skills (ask_id, title, description, base_score)
        VALUES (%s, %s, %s, %s)
    """, (
        ask_ids[0],
        "Уверенность",
        "Способность отстаивать свои границы и интересы.",
        50
    ))

    # Сохраняем изменения и закрываем соединение
    conn.commit()
    cur.close()


def read_db():
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM skills;")
    results = cur.fetchall()

    print(results)
    conn.close()


def list_tables_and_columns():
    cur = conn.cursor()

    # Получаем список всех таблиц в public-схеме
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """)
    tables = cur.fetchall()

    for (table,) in tables:
        cur.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s
        """, (table,))
        columns = [row[0] for row in cur.fetchall()]
        print(f"{table} ({', '.join(columns)})")

    cur.close()
    conn.close()

if __name__ == "__main__":
    list_tables_and_columns()

