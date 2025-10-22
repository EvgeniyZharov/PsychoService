import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from typing import List, Tuple, Dict, Any
from config import db_params


class PostgresDB:
    _pool = None

    def __init__(self, host: str, database: str, user: str, password: str, port: int = 5432,
                 minconn: int = 1, maxconn: int = 10):
        if not PostgresDB._pool:
            PostgresDB._pool = psycopg2.pool.SimpleConnectionPool(
                minconn,
                maxconn,
                host=host,
                database=database,
                user=user,
                password=password,
                port=port
            )

    def _get_conn(self):
        return PostgresDB._pool.getconn()

    def _release_conn(self, conn):
        PostgresDB._pool.putconn(conn)

    def execute(self, sql: str, params: Tuple = (), returning: bool = True) -> None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchone()[0] if returning else False
                conn.commit()
                return result
        finally:
            self._release_conn(conn)

    def create_table(self, create_sql: str):
        self.execute(create_sql, returning=False)

    def insert(self, table: str, data: Dict[str, Any], returning: bool = True):
        try:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            context = " RETURNING id" if returning else ""
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}){context};"
            print(sql, tuple(data.values()))
            new_id = self.execute(sql, tuple(data.values()), returning=returning)
            return new_id
        except Exception as ex:
            print(ex)
            return False

    def upsert(self, table: str, data: Dict[str, Any], conflict_field: str):
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        updates = ', '.join([f"{col}=EXCLUDED.{col}" for col in data.keys() if col != conflict_field])
        sql = f"""
            INSERT INTO {table} ({columns}) 
            VALUES ({placeholders}) 
            ON CONFLICT ({conflict_field}) DO UPDATE SET {updates}
        """
        self.execute(sql, tuple(data.values()))
        return True

    def fetch_all(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        finally:
            self._release_conn(conn)

    def fetch_one(self, sql: str, params: Tuple = ()) -> Dict[str, Any]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()
        finally:
            self._release_conn(conn)

    def close_all_connections(self):
        if PostgresDB._pool:
            PostgresDB._pool.closeall()


def main():
    db = PostgresDB(
        **db_params
    )

    # 1. USER_PROFILES
    # 1. Пользователи
    db.create_table("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            email VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            password VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'free'
        );
        """)

    # 2. Черты
    db.create_table("""
        CREATE TABLE IF NOT EXISTS traits (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL UNIQUE
        );
        """)

    # 3. Черты пользователя
    db.create_table("""
        CREATE TABLE IF NOT EXISTS user_traits (
            user_email VARCHAR REFERENCES user_profiles(email) ON DELETE CASCADE,
            trait_id INTEGER REFERENCES traits(id) ON DELETE CASCADE,
            value INTEGER,
            PRIMARY KEY (user_email, trait_id)
        );
        """)

    # 4. Цели пользователя
    db.create_table("""
        CREATE TABLE IF NOT EXISTS user_goals (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR REFERENCES user_profiles(email) ON DELETE CASCADE,
            goal TEXT NOT NULL
        );
        """)

    # 5. Прогресс по курсам
    db.create_table("""
        CREATE TABLE IF NOT EXISTS user_courses_progress (
            user_email VARCHAR REFERENCES user_profiles(email) ON DELETE CASCADE,
            course_id INTEGER NOT NULL,
            progress TEXT,
            PRIMARY KEY (user_email, course_id)
        );
        """)

    # 6. Пройденные тесты
    db.create_table("""
        CREATE TABLE IF NOT EXISTS user_tests_completed (
            user_email VARCHAR REFERENCES user_profiles(email) ON DELETE CASCADE,
            test_id INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_email, test_id)
        );
        """)

    # 2. MAIN_COURSES
    db.create_table("""
    CREATE TABLE IF NOT EXISTS main_courses (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        author TEXT,
        traits TEXT[],
        first_lesson_id VARCHAR,
        available BOOLEAN DEFAULT FALSE,
        condition TEXT
    );
    """)

    # 3. AUTHOR_COURSES
    db.create_table("""
    CREATE TABLE IF NOT EXISTS author_courses (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        author TEXT,
        traits TEXT[],
        first_lesson_id VARCHAR,
        available BOOLEAN DEFAULT FALSE,
        condition TEXT
    );
    """)

    # 4. LESSONS
    db.create_table("""
    CREATE TABLE IF NOT EXISTS lessons (
        id VARCHAR PRIMARY KEY,
        course_type VARCHAR,
        course_id INTEGER,
        title TEXT,
        type VARCHAR,
        content JSONB,
        question JSONB
    );
    """)

    # 5. TESTS
    db.create_table("""
    CREATE TABLE IF NOT EXISTS tests (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        available BOOLEAN DEFAULT FALSE,
        condition TEXT[]
    );
    """)

    # 6. TEST_QUESTIONS
    db.create_table("""
    CREATE TABLE IF NOT EXISTS test_questions (
        test_id INTEGER REFERENCES tests(id),
        question_index SERIAL,
        text TEXT,
        options TEXT[],
        PRIMARY KEY (test_id, question_index)
    );
    """)

    # 7. ROLE_TEST_QUESTIONS
    db.create_table("""
    CREATE TABLE IF NOT EXISTS role_test_questions (
        id SERIAL PRIMARY KEY,
        text TEXT NOT NULL,
        options TEXT[]
    );
    """)

    # 8. LEVELS_COURSE
    db.create_table("""
    CREATE TABLE IF NOT EXISTS levels_course (
        course_id INTEGER,
        level_index INTEGER,
        step_index INTEGER,
        lesson_id VARCHAR,
        title TEXT,
        description TEXT,
        color TEXT,
        size TEXT,
        PRIMARY KEY (course_id, level_index, step_index)
    );
    """)

    # 9. GUEST_EMAILS
    db.create_table("""
    CREATE TABLE IF NOT EXISTS guest_emails (
        email VARCHAR PRIMARY KEY,
        collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 10. RESET_TOKENS
    db.create_table("""
    CREATE TABLE IF NOT EXISTS reset_tokens (
        token UUID PRIMARY KEY,
        email VARCHAR REFERENCES user_profiles(email),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 1. Таблица answers
    db.create_table("""
    CREATE TABLE IF NOT EXISTS answers (
        id SERIAL PRIMARY KEY,
        ask_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        score INTEGER NOT NULL
    );
    """)

    # 2. Таблица asks
    db.create_table("""
    CREATE TABLE IF NOT EXISTS asks (
        id SERIAL PRIMARY KEY,
        theme_id INTEGER NOT NULL,
        ask TEXT NOT NULL
    );
    """)

    # 3. Таблица content
    db.create_table("""
    CREATE TABLE IF NOT EXISTS content (
        id SERIAL PRIMARY KEY,
        lesson_id VARCHAR NOT NULL,
        lesson_page INTEGER NOT NULL,
        type VARCHAR NOT NULL,
        content TEXT NOT NULL
    );
    """)

    # 4. Таблица questions
    db.create_table("""
    CREATE TABLE IF NOT EXISTS questions (
        id SERIAL PRIMARY KEY,
        lesson_id VARCHAR NOT NULL,
        lesson_page INTEGER NOT NULL,
        qa JSONB NOT NULL
    );
    """)

    # 5. Таблица test_skills
    db.create_table("""
    CREATE TABLE IF NOT EXISTS test_skills (
        id SERIAL PRIMARY KEY,
        theme_id INTEGER NOT NULL,
        asks INTEGER NOT NULL,
        total INTEGER NOT NULL,
        title TEXT NOT NULL
    );
    """)

    # 6. Таблица test_themes
    db.create_table("""
    CREATE TABLE IF NOT EXISTS test_themes (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT
    );
    """)

    # 7. Таблица users_tests
    db.create_table("""
    CREATE TABLE IF NOT EXISTS users_tests (
        user_id VARCHAR NOT NULL REFERENCES user_profiles(email) ON DELETE CASCADE,
        test_id INTEGER NOT NULL,
        PRIMARY KEY (user_id, test_id)
    );
    """)

    # 8. Таблица users_tests_results
    db.create_table("""
    CREATE TABLE IF NOT EXISTS users_tests_results (
        user_id VARCHAR NOT NULL REFERENCES user_profiles(email) ON DELETE CASCADE,
        skill_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        PRIMARY KEY (user_id, skill_id)
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS test (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS ask (
        id SERIAL PRIMARY KEY,
        test_id INTEGER REFERENCES test(id) ON DELETE CASCADE,
        content TEXT NOT NULL
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS answer (
        id SERIAL PRIMARY KEY,
        ask_id INTEGER REFERENCES ask(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        score INTEGER NOT NULL
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS skills (
        id SERIAL PRIMARY KEY,
        ask_id INTEGER REFERENCES ask(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        description TEXT,
        base_score INTEGER NOT NULL
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS user_test_answers (
        id SERIAL PRIMARY KEY,
        user_email VARCHAR REFERENCES user_profiles(email) ON DELETE CASCADE,
        test_id INTEGER NOT NULL,
        ask_id INTEGER NOT NULL,
        answer_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS skill_ask_link (
        id SERIAL PRIMARY KEY,
        skill_id INTEGER REFERENCES skills(id) ON DELETE CASCADE,
        ask_id INTEGER REFERENCES ask(id) ON DELETE CASCADE
    );
    """)

    db.execute("""
    ALTER TABLE user_profiles 
    ADD COLUMN IF NOT EXISTS personality_type VARCHAR;
    """, returning=False)

    db.execute("""
    ALTER TABLE user_traits 
    DROP COLUMN IF EXISTS value,
    ADD COLUMN IF NOT EXISTS percent DECIMAL(5,2),
    ADD COLUMN IF NOT EXISTS test_id INTEGER;
    """, returning=False)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS user_tests_completed (
        user_email VARCHAR REFERENCES user_profiles(email) ON DELETE CASCADE,
        test_id INTEGER NOT NULL,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_email, test_id)
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS lesson_content (
        id SERIAL PRIMARY KEY,
        lesson_id VARCHAR NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
        type VARCHAR NOT NULL,
        title TEXT,
        content TEXT NOT NULL
    );
    """)

    db.execute("""
    ALTER TABLE skills 
    ADD COLUMN IF NOT EXISTS test_id INTEGER REFERENCES test(id) ON DELETE CASCADE;
    """, returning=False)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS skill_ask_link (
        id SERIAL PRIMARY KEY,
        skill_id INTEGER REFERENCES skills(id) ON DELETE CASCADE,
        ask_id INTEGER REFERENCES ask(id) ON DELETE CASCADE
    );
    """)

    db.execute("""
    ALTER TABLE skills 
    ADD COLUMN IF NOT EXISTS test_id INTEGER REFERENCES test(id) ON DELETE CASCADE;
    """, returning=False)

    db.execute("""
    ALTER TABLE lessons 
    ADD COLUMN IF NOT EXISTS title TEXT,
    ADD COLUMN IF NOT EXISTS description TEXT;
    """, returning=False)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS test (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS ask (
        id SERIAL PRIMARY KEY,
        test_id INTEGER REFERENCES test(id) ON DELETE CASCADE,
        content TEXT NOT NULL
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS answer (
        id SERIAL PRIMARY KEY,
        ask_id INTEGER REFERENCES ask(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        score INTEGER NOT NULL
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS user_test_answers (
        id SERIAL PRIMARY KEY,
        user_email VARCHAR REFERENCES user_profiles(email) ON DELETE CASCADE,
        test_id INTEGER NOT NULL,
        ask_id INTEGER NOT NULL,
        answer_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS user_experience (
        user_email VARCHAR PRIMARY KEY REFERENCES user_profiles(email) ON DELETE CASCADE,
        exp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS user_points (
        user_email VARCHAR PRIMARY KEY REFERENCES user_profiles(email) ON DELETE CASCADE,
        today_points INTEGER DEFAULT 0,
        last_day DATE DEFAULT CURRENT_DATE,
        day_streak INTEGER DEFAULT 0
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS user_activity_log (
        id SERIAL PRIMARY KEY,
        email VARCHAR REFERENCES user_profiles(email) ON DELETE CASCADE,
        activity_date DATE DEFAULT CURRENT_DATE,
        points INTEGER NOT NULL,
        activity_type VARCHAR NOT NULL
    );
    """)

    db.create_table("""
    CREATE TABLE IF NOT EXISTS user_subscriptions (
        id SERIAL PRIMARY KEY,
        subscriber_email VARCHAR REFERENCES user_profiles(email) ON DELETE CASCADE,
        subscribed_to_email VARCHAR REFERENCES user_profiles(email) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(subscriber_email, subscribed_to_email)
    );
    """)

    db.execute("""
    ALTER TABLE user_profiles 
    ADD COLUMN IF NOT EXISTS avatar VARCHAR DEFAULT '';
    """, returning=False)

    db.execute("""
    ALTER TABLE user_traits 
    ADD COLUMN IF NOT EXISTS percent DECIMAL(5,2);
    """, returning=False)

    print("✅ Все таблицы успешно созданы.")
    db.close_all_connections()


if __name__ == "__main__":
    db = PostgresDB(
        **db_params
    )
    main()
    # db.insert('users_tests', {
    #         "user_id": 'admin@gmail.com',
    #         "test_id": 6
    #     }, returning=False)
    # db.execute("INSERT INTO users_tests (user_id, test_id) VALUES (%s, %s)", ('admin@gmail.com', 6), returning=False)
