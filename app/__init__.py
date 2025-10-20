from flask import Flask, session
from .db import db_app
import os

# Импорт blueprint-ов из разных модулей
from .auth.routes import auth_bp
from .courses.routes import courses_bp
from .profile.routes import profile_bp
from .tests.routes import tests_bp
from .editor.routes import editor_bp
from .main.routes import main_bp
from app.payment.routes import payment_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = 'your-very-secret-key'

    # Регистрация blueprint-ов
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(tests_bp)
    app.register_blueprint(editor_bp)
    app.register_blueprint(payment_bp)

    # Глобальный context processor для user_profile
    @app.context_processor
    def inject_user_profile():
        from app.auth.utils import get_or_create_user_experience

        user = session.get('user')

        if not user:
            return {'user_profile': None}

        try:
            # Получаем опыт пользователя
            exp = get_or_create_user_experience(user['email'])

            # Получаем профиль пользователя
            profile = db_app.fetch_one("SELECT * FROM user_profiles WHERE email = %s", (user['email'],))

            # Если профиль не найден, возвращаем None
            if not profile:
                return {'user_profile': None}

            # Добавляем опыт и уровень в профиль
            profile["exp"] = exp["exp"]
            profile["user_level"] = exp["level"]

            # Проверяем существование аватара
            if profile.get("avatar"):
                file_path = os.path.join("/app/static/content", profile["avatar"])
                if not os.path.isfile(file_path):
                    profile["avatar"] = ""
            else:
                profile["avatar"] = ""

            return {'user_profile': profile}

        except Exception as e:
            # Логируем ошибку, но не ломаем приложение
            app.logger.error(f"Error loading user profile: {e}")
            return {'user_profile': None}

    return app