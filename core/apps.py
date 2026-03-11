from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Улучшение конкурентного доступа SQLite (актуально на Windows при Django+Celery).
        # WAL снижает вероятность "database is locked", busy_timeout даёт подождать освобождения блокировки.
        try:
            from django.db import connection
            from django.db.backends.signals import connection_created

            def _set_sqlite_pragmas(sender, connection, **kwargs):  # noqa: ANN001
                if connection.vendor != "sqlite":
                    return
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("PRAGMA journal_mode=WAL;")
                        cursor.execute("PRAGMA synchronous=NORMAL;")
                        cursor.execute("PRAGMA busy_timeout=60000;")
                except Exception:
                    # Не падаем на старте, даже если PRAGMA не применилась
                    return

            # Подключаем обработчик один раз на процесс
            connection_created.connect(_set_sqlite_pragmas, dispatch_uid="core.sqlite_pragmas")

            # Применяем сразу к текущему соединению (на случай, если уже создано)
            if getattr(connection, "vendor", None) == "sqlite":
                _set_sqlite_pragmas(None, connection)
        except Exception:
            return
