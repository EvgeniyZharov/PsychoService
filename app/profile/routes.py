from flask import Blueprint, render_template, redirect, session, request, url_for
from app.db import db_app
from app.profile.services import get_full_user_profile

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    email = session['user']['email']
    user_data = get_full_user_profile(email)
    user_characters = db_app.fetch_all(sql="""SELECT test_title, character_title from user_characters WHERE user_email = %s;""", params=(email,))

    if not user_data:
        return render_template("fail_user.html", message="Пользователь не найден")

    return render_template('profile.html', user=user_data, user_characters=user_characters)


@profile_bp.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    email = session['user']['email']
    user = db_app.fetch_one("SELECT * FROM user_profiles WHERE email = %s", (email,))

    if request.method == 'POST':
        name = request.form.get('name')
        new_password = request.form.get('new_password')
        personality_type = request.form.get('personality_type')
        goals_raw = request.form.get('goals')

        # Обновляем поля профиля
        update_fields = {
            'name': name,
            'personality_type': personality_type
        }
        if new_password:
            update_fields['password'] = new_password

        for field, value in update_fields.items():
            db_app.execute(f"UPDATE user_profiles SET {field} = %s WHERE email = %s", (value, email), returning=False)

        # Обновляем цели
        db_app.execute("DELETE FROM user_goals WHERE user_email = %s", (email,), returning=False)
        goals = [g.strip() for g in goals_raw.split(',') if g.strip()]
        for goal in goals:
            db_app.insert("user_goals", {"user_email": email, "goal": goal})

        session['user']['name'] = name
        user = db_app.fetch_one("SELECT * FROM user_profiles WHERE email = %s", (email,))
        return render_template('edit_profile.html', user=user, message="Профиль обновлён!")

    return render_template('edit_profile.html', user=user)

@profile_bp.route("/profile/<user_email>")
def view_user_profile(user_email):
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    from app.auth.utils import get_or_create_user_experience
    # Получение основной информации
    user = db_app.fetch_one(
        "SELECT name, email, avatar, personality_type FROM user_profiles WHERE email = %s",
        (user_email,)
    )
    exp = get_or_create_user_experience(user['email'])
    user["exp"] = exp["exp"]
    user["user_level"] = exp["level"]

    # Получение опыта и уровня
    stats = db_app.fetch_one("""
        SELECT exp, level FROM user_experience WHERE user_email = %s
    """, (user_email,))
    stats = stats or {"exp": 0, "level": 0}

    is_following = db_app.fetch_one("""
                SELECT 1 FROM user_subscriptions
                WHERE subscriber_email = %s AND subscribed_to_email = %s
            """, (session['user']['email'], user_email)) is not None

    return render_template("user_profile.html", user=user, stats=stats, is_following=is_following)


@profile_bp.route("/follow/<email>", methods=["POST"])
def toggle_follow(email):
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    user_email = session['user']['email']
    # Проверим, есть ли уже подписка
    existing = db_app.fetch_one("""
        SELECT 1 FROM user_subscriptions
        WHERE subscriber_email = %s AND subscribed_to_email = %s
    """, (user_email, email))

    if existing:
        # Отписка
        db_app.execute("""
            DELETE FROM user_subscriptions
            WHERE subscriber_email = %s AND subscribed_to_email = %s
        """, (user_email, email), returning=False)
    else:
        # Подписка
        db_app.execute("""
            INSERT INTO user_subscriptions (subscriber_email, subscribed_to_email)
            VALUES (%s, %s)
        """, (user_email, email), returning=False)

    return redirect(url_for('profile.foreign_profile', email=email))


@profile_bp.route("/profile/<email>")
def foreign_profile(email):
    import os
    print("FUCKK")
    profile = db_app.fetch_one("SELECT * FROM user_profiles WHERE email = %s", (email,))
    is_following = False

    if 'user' in session:
        file_path = os.path.join("/app/static/content", profile["avatar"])
        if not os.path.isfile(file_path):
            profile["avatar"] = ""
        is_following = db_app.fetch_one("""
            SELECT 1 FROM user_subscriptions
            WHERE subscriber_email = %s AND subscribed_to_email = %s
        """, (session['user']['email'], email)) is not None
        print(is_following)
    return render_template("foreign_profile.html", profile=profile, is_following=is_following)


@profile_bp.route('/following')
def following_profiles():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    import os
    user_email = session['user']['email']
    # Получить всех, на кого подписан пользователь
    profiles = db_app.fetch_all("""
        SELECT up.email, up.name, up.avatar, ux.exp, ux.level
        FROM user_subscriptions s
        JOIN user_profiles up ON s.subscribed_to_email = up.email
        LEFT JOIN user_experience ux ON up.email = ux.user_email
        WHERE s.subscriber_email = %s
        ORDER BY ux.exp DESC NULLS LAST;
    """, (user_email,))
    for profile in profiles:
        file_path = os.path.join("/app/static/content", profile["avatar"])
        if not os.path.isfile(file_path):
            profile["avatar"] = ""
    return render_template("following_profiles.html", profiles=profiles)

@profile_bp.route("/search", methods=["GET"])
def redirect_to_profile():
    email = request.args.get("email")
    if email:
        if db_app.fetch_all("""
        SELECT * FROM user_profiles WHERE email = %s;
    """, (email,)):
            return redirect(url_for("profile.foreign_profile", email=email))
    return redirect(url_for("profile.following_profiles"))  # если email не введён
