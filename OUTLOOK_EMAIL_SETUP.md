# Настройка отправки писем через Outlook SMTP

## Шаги для настройки:

### 1. Получите пароль приложения для Outlook

Для безопасности Outlook требует использовать пароль приложения вместо обычного пароля:

1. Перейдите на https://account.microsoft.com/security
2. Войдите в свой аккаунт Outlook/Microsoft
3. Перейдите в раздел "Безопасность" → "Дополнительные параметры безопасности"
4. Найдите "Пароли приложений" и создайте новый пароль приложения
5. Скопируйте созданный пароль (он будет показан только один раз!)

### 2. Настройте переменные окружения

#### Для Windows (PowerShell):
```powershell
$env:EMAIL_HOST_USER="your-email@outlook.com"
$env:EMAIL_HOST_PASSWORD="your-app-password"
```

#### Для Windows (CMD):
```cmd
set EMAIL_HOST_USER=your-email@outlook.com
set EMAIL_HOST_PASSWORD=your-app-password
```

#### Для Linux/Mac:
```bash
export EMAIL_HOST_USER="your-email@outlook.com"
export EMAIL_HOST_PASSWORD="your-app-password"
```

### 3. Альтернатива: прямое редактирование settings.py

Если не хотите использовать переменные окружения, можете напрямую указать данные в `tendersite/settings.py`:

```python
EMAIL_HOST_USER = 'your-email@outlook.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

** ВНИМАНИЕ:** Не коммитьте файл settings.py с паролями в Git!

### 4. Проверка настроек

Настройки уже настроены в `settings.py`:
- **EMAIL_HOST**: `smtp-mail.outlook.com` (или `smtp.office365.com`)
- **EMAIL_PORT**: `587`
- **EMAIL_USE_TLS**: `True`

### 5. Тестирование

После настройки перезапустите сервер Django и попробуйте закрыть тендер - письма должны отправляться через Outlook.

## Важные замечания:

- Используйте **пароль приложения**, а не обычный пароль аккаунта
- Если у вас двухфакторная аутентификация, пароль приложения обязателен
- Пароль приложения можно создать несколько раз, если потеряете текущий
- Для корпоративных аккаунтов Office 365 может потребоваться другой SMTP сервер

