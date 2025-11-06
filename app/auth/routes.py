from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response
from app.db import db_app
from app.auth.utils import generate_reset_token, validate_reset_token, validate_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember_me')

        if not validate_email(email):
            return render_template('login.html', error='Неверный формат email адреса')

        user = db_app.fetch_one("SELECT * FROM user_profiles WHERE email = %s", (email,))
        if user and user['password'] == password:
            session['user'] = {"email": email, "name": user["name"], "nickname": user.get("nickname", "")}
            session['user_email'] = email
            next_url = session.pop('next_url', None)
            if next_url:
                resp = redirect(next_url)
            else:
                resp = redirect(url_for('courses.courses', course_id=1))
            # resp = redirect(url_for('courses.courses', course_id=1))
            if remember:
                resp.set_cookie('remember_email', email, max_age=60*60*24*30)
            return resp
        else:
            return render_template('login.html', error='Неверный логин или пароль')

    saved_email = request.cookies.get('remember_email', '')
    return render_template('login.html', saved_email=saved_email)


@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_email', None)  # Очищаем email из сессии
    session.pop('email_collected', None)  # Очищаем флаг сбора email
    session.pop('guest_email', None)  # Очищаем гостевой email
    return redirect(url_for('courses.courses', course_id=1))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        # nickname = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        agree_terms = request.form.get('agree_terms')

        # Валидация email
        if not validate_email(email):
            return render_template('register.html', error="Неверный формат email адреса")

        # Проверяем уникальность email
        existing_email = db_app.fetch_one("SELECT * FROM user_profiles WHERE email = %s", (email,))
        if existing_email:
            return render_template('register.html', error="Пользователь с таким email уже существует")

        # Проверяем уникальность никнейма
        existing_nickname = db_app.fetch_one("SELECT * FROM user_profiles WHERE nickname = %s", (name,))
        if existing_nickname:
            return render_template('register.html', error="Пользователь с таким никнеймом уже существует")

        if not agree_terms:
            return render_template('register.html', error="Необходимо согласиться с условиями")

        db_app.insert("user_profiles", {
            "email": email,
            "name": name,
            "password": password,
            "status": "free"
        }, returning=False)

        session['user'] = {"email": email, "name": name}
        session['user_email'] = email

        next_url = session.pop('next_url', None)
        if next_url:
            return redirect(next_url)
        else:
            return redirect(url_for('courses.courses', course_id=1))

        # return redirect(url_for('courses.course', course_id=1))
    if 'guest_email' in session:
        email = session["guest_email"]
    else:
        email = ""

    return render_template('register.html', email=email)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')

        # Валидация email
        if not validate_email(email):
            return render_template('forgot_password.html', error="Неверный формат email адреса")

        user = db_app.fetch_one("SELECT * FROM user_profiles WHERE email = %s", (email,))
        if user:
            token = generate_reset_token(email)
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            return render_template('forgot_password.html', message=f"Ссылка для сброса: {reset_link}")
        else:
            return render_template('forgot_password.html', error="Пользователь с таким email не найден.")

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = validate_reset_token(token)
    if not email:
        return "Недействительная или устаревшая ссылка", 400

    if request.method == 'POST':
        new_password = request.form.get('password')
        db_app.execute("UPDATE user_profiles SET password = %s WHERE email = %s", (new_password, email))
        db_app.execute("DELETE FROM reset_tokens WHERE token = %s", (token,))
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', email=email, token=token)
