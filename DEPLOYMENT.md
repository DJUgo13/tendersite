# Инструкция по деплою в продакшн

## ⚠️ КРИТИЧЕСКИЕ настройки перед запуском

### 1. Переменные окружения (создайте `.env` файл или установите в системе)

```bash
# Django Core
SECRET_KEY=<сгенерируйте новый секретный ключ>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# База данных
USE_MYSQL=True
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=tendersite
MYSQL_USER=tendersite
MYSQL_PASSWORD=<сильный пароль>
MYSQL_ROOT_PASSWORD=<сильный пароль root>

# Celery / Redis
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

# Сайт
SITE_URL=https://yourdomain.com/

# Email
EMAIL_MODE=production
EMAIL_HOST=smtp.mail.ru
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your-email@mail.ru
EMAIL_HOST_PASSWORD=<пароль приложения>
DEFAULT_FROM_EMAIL=your-email@mail.ru

# Безопасность (если используете HTTPS)
SECURE_SSL_REDIRECT=True
```

### 2. Генерация SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Миграции базы данных

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 5. Создание директории для логов

```bash
mkdir logs
```

### 6. Запуск сервисов

#### Вариант A: Gunicorn + Nginx (рекомендуется)

```bash
# Запуск Gunicorn
gunicorn tendersite.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120

# В отдельном терминале - Celery worker
celery -A tendersite worker -l info

# В отдельном терминале - Celery beat (если нужны периодические задачи)
celery -A tendersite beat -l info
```

#### Вариант B: Docker Compose (если используете)

```bash
docker compose up -d db redis
# Затем запустите Django и Celery на хосте или в контейнерах
```

### 7. Настройка Nginx (пример)

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /path/to/tendersite/staticfiles/;
    }
}
```

### 8. SSL сертификат (Let's Encrypt)

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```


