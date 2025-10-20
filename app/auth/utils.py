import uuid
from app.db import db_app

def generate_reset_token(email):
    token = str(uuid.uuid4())
    db_app.insert("reset_tokens", {"token": token, "email": email})
    return token

def validate_reset_token(token):
    record = db_app.fetch_one("SELECT * FROM reset_tokens WHERE token = %s", (token,))
    if record:
        return record['email']
    return None

def get_or_create_user_experience(user_email):
    # Пытаемся получить текущие значения
    experience = db_app.fetch_one(
        "SELECT exp, level FROM user_experience WHERE user_email = %s",
        (user_email,)
    )
    # Если не нашли — создаём новую запись с нулями
    if not experience:
        db_app.execute(
            "INSERT INTO user_experience (user_email, exp) VALUES (%s, 0)",
            (user_email,),
            returning=False
        )
        return {"exp": 0, "level": 0}

    return {"exp": experience["exp"], "level": experience["level"]}
