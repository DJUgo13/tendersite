"""
Инициализация Django-проекта.

Важно: Celery может быть не установлен в окружении (например, до `pip install -r requirements.txt`).
Чтобы `runserver`/`manage.py` не падали, импорт Celery делаем безопасным.
"""

try:
    # На Windows проще использовать PyMySQL вместо mysqlclient (не требует сборки).
    import pymysql

    pymysql.install_as_MySQLdb()
except ModuleNotFoundError:
    pass

try:
    from .celery import app as celery_app

    __all__ = ("celery_app",)
except ModuleNotFoundError:
    # Celery не установлен — Django должен продолжить запускаться.
    celery_app = None
    __all__ = ()

