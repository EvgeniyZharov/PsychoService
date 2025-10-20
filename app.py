import psycopg2
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import random


app = Flask(__name__)

# Настройки приложения
app.config["SECRET_KEY"] = "supersecretkey"

# Подключение к PostgreSQL
DB_NAME = "psycho_db"
DB_USER = "psycho"
DB_PASSWORD = "patric123"
DB_HOST = "193.109.79.119"
DB_PORT = "5432"

courses_data = [
    {
        "id": 1,
        "title": "Психология общения",
        "description": "Узнайте, как лучше понимать людей и эффективно общаться.",
        "image": "content/image_1.png"
    },
    {
        "id": 2,
        "title": "Развитие эмоционального интеллекта",
        "description": "Развивайте способность понимать свои и чужие эмоции.",
        "image": "content/image_1.png"
    }
]

lessons_data = {
    1: [
        {
            "id": 101,
            "title": "Введение в психологию общения",
            "text": "Общение — это процесс обмена информацией между людьми...",
            "image": "content/image_1.png",
            "video": "https://www.youtube.com/embed/dQw4w9WgXcQ"
        },
        {
            "id": 102,
            "title": "Вербальные и невербальные сигналы",
            "text": "Научитесь понимать язык тела и жестов.",
            "image": "content/image_1.png",
            "video": "https://www.youtube.com/embed/dQw4w9WgXcQ"
        }
    ],
    2: [
        {
            "id": 201,
            "title": "Что такое эмоциональный интеллект?",
            "text": "Эмоциональный интеллект (EQ) — это способность распознавать эмоции...",
            "image": "content/image_1.png",
            "video": "https://www.youtube.com/embed/dQw4w9WgXcQ"
        }
    ]
}

# 📊 Данные для тестов и вопросов
tests_data = [
    {
        "id": 1,
        "title": "Тест на уровень стресса",
        "description": "Определите, насколько вы подвержены стрессу в повседневной жизни.",
        "questions": [
            {
                "id": 101,
                "text": "Как часто вы чувствуете себя уставшим?",
                "options": ["Редко", "Иногда", "Часто", "Постоянно"]
            },
            {
                "id": 102,
                "text": "Вы чувствуете раздражение без видимой причины?",
                "options": ["Никогда", "Редко", "Иногда", "Часто"]
            }
        ]
    },
    {
        "id": 2,
        "title": "Тест на эмоциональный интеллект",
        "description": "Проверьте, насколько вы хорошо понимаете свои эмоции и эмоции окружающих.",
        "questions": [
            {
                "id": 201,
                "text": "Вы легко распознаете свои чувства?",
                "options": ["Всегда", "Часто", "Иногда", "Редко"]
            },
            {
                "id": 202,
                "text": "Можете ли вы контролировать свои эмоции в стрессовых ситуациях?",
                "options": ["Да", "Скорее да", "Скорее нет", "Нет"]
            }
        ]
    }
]

dialog_data = [
    {
        "type": "fact",
        "text": "Факт 1: Люди запоминают негативные события на 60% лучше, чем позитивные."
    },
    {
        "type": "question",
        "text": "Как вы считаете, почему так происходит?",
        "choices": [
            "Мозг эволюционно настроен на выживание.",
            "Люди любят жаловаться.",
            "Негативные события просто более редкие."
        ]
    },
    {
        "type": "fact",
        "text": "Факт 2: Средний человек принимает около 35 000 решений каждый день."
    },
    {
        "type": "question",
        "text": "Что помогает вам делать более осознанные решения?",
        "choices": [
            "Регулярный сон и отдых.",
            "Выпить побольше кофе.",
            "Ничего, всё делаю наугад."
        ]
    }
]



def get_db_connection():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        client_encoding="UTF8"
    )
    conn.set_client_encoding('UTF8')
    return conn


bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


# --- Создание таблицы пользователей (если не существует) ---
def create_users_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            password VARCHAR(150) NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


create_users_table()


# --- Класс пользователя для Flask-Login ---
class User(UserMixin):
    def __init__(self, id, name, email, password):
        self.id = id
        self.name = name
        self.email = email
        self.password = password


# --- Загрузка пользователя ---
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password FROM users WHERE id = %s;", (user_id,))
    user_data = cur.fetchone()
    cur.close()
    conn.close()

    if user_data:
        return User(*user_data)
    return None


# --- Главная страница ---
@app.route("/")
def index():
    return render_template("index.html", user=current_user)


# --- Регистрация ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s;", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            flash("Этот email уже зарегистрирован!", "danger")
            return redirect(url_for("register"))

        cur.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s) RETURNING id;",
            (name, email, hashed_password)
        )
        conn.commit()
        cur.close()
        conn.close()

        flash("Регистрация успешна! Теперь войдите в систему.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# --- Авторизация ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, password FROM users WHERE email = %s;", (email,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()

        if user_data and bcrypt.check_password_hash(user_data[3], password):
            user = User(*user_data)
            login_user(user)
            flash("Вход выполнен успешно!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Неверный email или пароль.", "danger")

    return render_template("login.html")


# --- Страница профиля пользователя ---
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    # Пример данных для статистики (в реальном проекте данные нужно брать из базы)
    courses_progress = {"Курс 1": 80, "Курс 2": 60, "Курс 3": 40}
    tests_results = {"Тест 1": 90, "Тест 2": 75, "Тест 3": 50}
    user_progress_1 = {"Параметр 1": 90, "Параметр 2": 60, "Параметр 3": 75, }

    # Данные для радарной диаграммы
    characteristics = ["Лидерство", "Эмпатия", "Аналитика", "Креативность", "Стрессоустойчивость"]
    radar_data = [random.randint(50, 100) for _ in characteristics]

    # Обработка смены пароля
    if request.method == "POST":
        new_password = request.form.get("new_password")
        hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET password = %s WHERE id = %s;", (hashed_password, current_user.id))
        conn.commit()
        cur.close()
        conn.close()

        flash("Пароль успешно изменен!", "success")
        return redirect(url_for("profile"))

    man_type = "Normal man"
    return render_template("profile.html",
                           user=current_user,
                           courses_progress=courses_progress,
                           tests_results=tests_results,
                           characteristics=characteristics,
                           radar_data=radar_data,
                           user_progress_1=user_progress_1,
                           man_type=man_type)


# --- Главная страница после авторизации ---
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)


# --- Выход ---
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("login"))


# --- Курсы по развитию личности ---
@app.route("/courses_theme")
def courses_theme():
    return render_template("courses_theme.html")


# 📑 Страница со всеми курсами
@app.route("/courses")
def courses():
    return render_template("courses.html", courses=courses_data)


# 📖 Страница с уроками конкретного курса
@app.route("/course/<int:course_id>")
def course(course_id):
    course = next((c for c in courses_data if c["id"] == course_id), None)
    lessons = lessons_data.get(course_id, [])
    if not course:
        abort(404)
    return render_template("course_lesson.html", course=course, lessons=lessons)


# 📘 Страница отдельного урока с возможностью переключения между уроками
@app.route("/course/<int:course_id>/lesson/<int:lesson_id>")
def lesson(course_id, lesson_id):
    lessons = lessons_data.get(course_id, [])
    lesson = next((l for l in lessons if l["id"] == lesson_id), None)
    if not lesson:
        abort(404)

    # Поиск индекса текущего урока
    current_index = lessons.index(lesson)
    prev_lesson = lessons[current_index - 1] if current_index > 0 else None
    next_lesson = lessons[current_index + 1] if current_index < len(lessons) - 1 else None

    return render_template("lesson.html", lesson=lesson, prev_lesson=prev_lesson, next_lesson=next_lesson, course_id=course_id)


@app.route("/tests")
def tests():
    return render_template("tests.html", tests=tests_data)


# 📋 Страница прохождения теста
@app.route("/test/<int:test_id>", methods=["GET", "POST"])
def test(test_id):
    test = next((t for t in tests_data if t["id"] == test_id), None)
    if not test:
        flash("Тест не найден!", "error")
        return redirect(url_for("tests"))

    return render_template("test_page.html", test=test)


# 📊 Обработка отправки ответов на тест
@app.route("/submit_test/<int:test_id>", methods=["POST"])
def submit_test(test_id):
    test = next((t for t in tests_data if t["id"] == test_id), None)
    if not test:
        flash("Тест не найден!", "error")
        return redirect(url_for("tests"))

    answers = {}
    for question in test["questions"]:
        question_id = f"question_{question['id']}"
        answers[question["text"]] = request.form.get(question_id, "Ответ не выбран")

    # Логика обработки ответов (здесь можно добавить оценку результата)
    flash("Ваши ответы успешно отправлены!", "success")

    return render_template("test_result.html", test=test, answers=answers)


# Маршрут для карты прогресса
@app.route("/progress")
def show_progress():
    return render_template("story_map.html")


@app.route("/story", methods=["GET", "POST"])
def story():
    """
    Отображает текущий этап диалога.
    Если этап — вопрос, пользователь может отправить ответ (POST).
    Ответ сохраняется в session['answers'].
    """
    # Текущий шаг диалога
    if "step" not in session:
        session["step"] = 0  # Начинаем с 0
    step = session["step"]

    # Если пользователь уже прошёл всё
    if step >= len(dialog_data):
        return render_template("story.html", finished=True, answers=session.get("answers", {}))

    current_item = dialog_data[step]

    # Если POST-запрос (пользователь выбрал ответ на вопрос)
    if request.method == "POST":
        user_choice = request.form.get("choice")
        # Сохраним ответ пользователя
        if "answers" not in session:
            session["answers"] = []
        session["answers"].append({
            "question": current_item["text"],
            "answer": user_choice
        })
        session["step"] = step + 1
        return redirect(url_for("story"))

    # Иначе GET-запрос, показываем страницу
    return render_template("story.html",
                           finished=False,
                           step=step,
                           item=current_item,
                           total=len(dialog_data),
                           answers=session.get("answers", []))


# --- Запуск приложения ---
if __name__ == "__main__":
    app.run(debug=True)
