# Экземпляр базы данных, будет использоваться во всём проекте
def init_app():
    from db_client import PostgresDB
    from .config import db_params
    """
    Инициализирует подключение к базе данных.

    :param app: Flask-приложение
    :param db_params: параметры подключения к базе данных (dict)
    """
    db = PostgresDB(**db_params)
    return db

db_app = init_app()
