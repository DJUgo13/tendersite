# Инструкция по деплою на Reg.ru (VPS Ubuntu)

Эта инструкция поможет вам развернуть проект `tendersite` на сервере Reg.ru.

## 1. Подготовка сервера
Зайдите на сервер по SSH:
```bash
ssh root@ваш_ip_адрес
```

Обновите систему и установите зависимости:
```bash
sudo apt update
sudo apt install python3-pip python3-venv git nginx curl -y
```

## 2. Клонирование проекта
```bash
cd /var/www
git clone <ссылка_на_ваш_репозиторий> tendersite
cd tendersite
```

## 3. Настройка окружения
Создайте виртуальное окружение и установите зависимости:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Создайте файл `.env`:
```bash
cp .env.example .env
nano .env
```
> [!IMPORTANT]
> Обязательно установите `DEBUG=False`, сгенерируйте новый `SECRET_KEY` и укажите данные почты Mail.ru.

## 4. Сбор статических файлов
```bash
python manage.py collectstatic --noinput
python manage.py migrate
```

## 5. Настройка Gunicorn (Systemd)
Создайте файл сервиса:
```bash
sudo nano /etc/systemd/system/tendersite.service
```
Вставьте содержимое:
```ini
[Unit]
Description=Gunicorn instance to serve tendersite
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/tendersite
Environment="PATH=/var/www/tendersite/venv/bin"
ExecStart=/var/www/tendersite/venv/bin/gunicorn --workers 3 --bind unix:tendersite.sock tendersite.wsgi:application

[Install]
WantedBy=multi-user.target
```

Запустите сервис:
```bash
sudo systemctl start tendersite
sudo systemctl enable tendersite
```

## 6. Настройка Nginx
Создайте конфиг Nginx:
```bash
sudo nano /etc/nginx/sites-available/tendersite
```
Вставьте содержимое:
```nginx
server {
    listen 80;
    server_name tende.space www.tende.space;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root /var/www/tendersite;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/tendersite/tendersite.sock;
    }
}
```

Активируйте конфиг:
```bash
sudo ln -s /etc/nginx/sites-available/tendersite /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

## 7. Настройка SSL (HTTPS)
Рекомендуется использовать Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d tende.space -d www.tende.space
```
