from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import db_app

payment_bp = Blueprint("payment", __name__, url_prefix="/payment")

@payment_bp.route("/pay", methods=["GET", "POST"])
def process_payment():
    from datetime import date, timedelta
    user_email = session.get("user", {}).get("email")
    if request.method == "POST":
        plan = request.form.get("plan")
        card = request.form.get("card")
        expiry = request.form.get("expiry")
        cvv = request.form.get("cvv")

        # Пример простой валидации (в реальных условиях нужна безопасная обработка)
        if not all([plan, card, expiry, cvv]):
            flash("Пожалуйста, заполните все поля", "error")
            return redirect(url_for("payment.process_payment"))


        if not user_email:
            flash("Необходима авторизация", "error")
            return redirect(url_for("auth.login"))

        db_app.execute("""
        UPDATE user_profiles
        SET payment_plan = %s,
        subscription_status = 'active',
        subscription_expiry = %s
        WHERE email = %s
        """, (plan, date.today() + timedelta(days=30), user_email), returning=False)
        # plan = request.form.get("plan", "pro")
        # amount = request.form.get("amount")  # строка → число
        # card_last4 = request.form.get("card_last4")
        # transaction_id = request.form.get("transaction_id")
        # # Сохранение информации о подписке (псевдо-пример)
        # db_app.execute("""
        # INSERT INTO payments (user_email, plan_type, amount, card_last4, transaction_id)
        # VALUES (%s, %s, %s, %s, %s)
        # """, (user_email, plan, amount, card_last4, transaction_id))

        flash("Оплата успешно проведена! Подписка активирована ✅", "success")
        return redirect(url_for("profile.profile"))

    return render_template("payment.html", current_user={"email": user_email})

@payment_bp.route("/payment/success", methods=["POST"])
def payment_success():
    from datetime import date, timedelta
    user_email = request.form.get("email")
    plan = request.form.get("plan", "pro")  # по умолчанию 'pro'

    if not user_email:
        flash("Ошибка: не указан email пользователя", "error")
        return redirect(url_for("main.index"))

    # Обновление профиля
    db_app.execute("""
        UPDATE user_profiles
        SET payment_plan = %s,
            subscription_status = 'active',
            subscription_expiry = %s
        WHERE email = %s
    """, (plan, date.today() + timedelta(days=30), user_email))

    flash("Оплата прошла успешно. Подписка активирована!", "success")
    return redirect(url_for("profile.view_user_profile", user_email=user_email))