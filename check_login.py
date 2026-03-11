import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tendersite.settings')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import connection

print("--- ПРОВЕРКА ПОДКЛЮЧЕНИЯ ---")
print(f"База данных: {connection.settings_dict['ENGINE']}")
print(f"Хост: {connection.settings_dict['HOST']}")
print(f"БД Имя: {connection.settings_dict['NAME']}")

print("\n--- ПРОВЕРКА ПОЛЬЗОВАТЕЛЯ ---")
username = 'admin'
password = 'admin12345'

try:
    user_obj = User.objects.get(username=username)
    print(f"Пользователь '{username}' найден.")
    print(f"is_staff: {user_obj.is_staff}")
    print(f"is_superuser: {user_obj.is_superuser}")
    print(f"is_active: {user_obj.is_active}")
    
    # Проверка пароля напрямую
    auth_user = authenticate(username=username, password=password)
    if auth_user:
        print(f"\n✅ УСПЕХ: Пароль '{password}' ВЕРНЫЙ.")
    else:
        print(f"\n❌ ОШИБКА: Пароль '{password}' НЕ подходит для '{username}'.")
        
except User.DoesNotExist:
    print(f"❌ ОШИБКА: Пользователь '{username}' НЕ найден в этой базе!")

print("\n--- ВСЕ ПОЛЬЗОВАТЕЛИ В БАЗЕ ---")
for u in User.objects.all():
    print(f"- {u.username} (staff: {u.is_staff})")
