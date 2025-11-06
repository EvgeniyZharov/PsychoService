from functools import wraps
from flask import session, redirect, url_for, request

def require_user_email(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def require_user_session(f):
    # Декоратор для проверки наличия полной пользовательской сессии.
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or 'user_email' not in session:
            # Сохраняем URL, на который пользователь пытался попасть
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

