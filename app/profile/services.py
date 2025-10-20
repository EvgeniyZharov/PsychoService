from app.db import db_app

def get_full_user_profile(email):
    import os
    from app.auth.utils import get_or_create_user_experience
    user = db_app.fetch_one("SELECT * FROM user_profiles WHERE email = %s", (email,))
    if not user:
        return None

    file_path = os.path.join("/app/static/content", user["avatar"])
    if not os.path.isfile(file_path):
        user["avatar"] = ""

    test_count = db_app.fetch_one("""
        SELECT COUNT(*) FROM user_tests_completed WHERE user_email = %s
    """, (email,))['count']

    course_progress = db_app.fetch_all("""
        SELECT course_id, progress FROM user_courses_progress WHERE user_email = %s
    """, (email,))
    course_progress_map = {
        f"Курс {row['course_id']}": row['progress'] for row in course_progress
    }

    traits = db_app.fetch_all("""
        SELECT t.title, ut.percent 
        FROM user_traits ut
        JOIN skills t ON ut.trait_id = t.id
        WHERE ut.user_email = %s
    """, (email,))
    trait_map = {row['name']: row['percent'] for row in traits}

    goals = db_app.fetch_all("SELECT goal FROM user_goals WHERE user_email = %s", (email,))
    goal_list = [g['goal'] for g in goals]

    points_info = db_app.fetch_one(
        "SELECT today_points, day_streak FROM user_points WHERE user_email = %s", (email,)
    )

    # personality_info = db_app.fetch_one(
    #     "SELECT personality_type FROM user_info WHERE user_email = %s", (email,)
    # )

    personality_type = db_app.fetch_one("SELECT personality_type FROM user_profiles WHERE email = %s;", (email,))

    today_points = points_info["today_points"] if points_info else 0
    day_streak = points_info["day_streak"] if points_info else 0
    experience = get_or_create_user_experience(email)
    return {
        "name": user["name"],
        "personality_type": user["personality_type"],
        "tests_completed": test_count,
        "courses_progress": course_progress_map,
        "traits": trait_map,
        "goals": goal_list,
        "points": today_points,
        "streak_days": day_streak,
        "exp": experience["exp"],
        "level": experience["level"]
    }
