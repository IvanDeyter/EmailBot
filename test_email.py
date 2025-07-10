#!/usr/bin/env python3
"""
Тестовый скрипт для проверки подключения к почте
Запустите этот файл для проверки настроек
"""

import logging
import sys
import os
from dotenv import load_dotenv

# Добавляем путь к нашему модулю
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from email_client import EmailClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_email_connection():
    """Тестирование подключения к почте"""

    # Загружаем переменные окружения
    load_dotenv()

    # Получаем настройки из .env
    server = os.getenv('EMAIL_SERVER', 'imap.yandex.ru')
    port = int(os.getenv('EMAIL_PORT', 993))
    login = os.getenv('EMAIL_LOGIN')
    password = os.getenv('EMAIL_PASSWORD')
    sender = os.getenv('EMAIL_SENDER')

    # Проверяем, что все настройки заданы
    if not all([login, password, sender]):
        print("❌ Ошибка: Не все настройки заданы в .env файле")
        print("Нужно указать: EMAIL_LOGIN, EMAIL_PASSWORD, EMAIL_SENDER")
        return False

    print("🔧 Тестирование подключения к почте...")
    print(f"Сервер: {server}:{port}")
    print(f"Логин: {login}")
    print(f"Отправитель для поиска: {sender}")
    print("-" * 50)

    # Создаем клиент
    client = EmailClient(server, port, login, password)

    try:
        # Тест 1: Подключение
        print("📡 Тест 1: Подключение к серверу...")
        if not client.connect():
            print("❌ Не удалось подключиться к серверу")
            return False
        print("✅ Подключение успешно")

        # Тест 2: Выбор ящика
        print("\n📂 Тест 2: Выбор папки INBOX...")
        if not client.select_mailbox():
            print("❌ Не удалось выбрать папку INBOX")
            return False
        print("✅ Папка INBOX выбрана")

        # Тест 3: Поиск писем
        print(f"\n🔍 Тест 3: Поиск писем от {sender}...")
        all_emails = client.search_emails_from_sender(sender, days_back=7)
        print(f"✅ Найдено {len(all_emails)} писем за последние 7 дней")

        # Тест 4: Поиск новых писем (основная функция бота)
        print(f"\n📧 Тест 4: Поиск новых писем от {sender}...")
        new_emails = client.get_new_emails_from_sender(sender, update_state=False)  # Не обновляем состояние в тесте
        print(f"✅ Найдено {len(new_emails)} новых писем")

        # Тест 5: Поиск непрочитанных писем (старый метод)
        print(f"\n📧 Тест 5: Поиск непрочитанных писем от {sender}...")
        unread_emails = client.get_unread_emails_from_sender(sender)
        print(f"✅ Найдено {len(unread_emails)} непрочитанных писем")

        # Тест 6: Просмотр содержимого (если есть письма)
        emails_to_show = new_emails if new_emails else unread_emails
        if emails_to_show:
            print(f"\n📝 Тест 6: Просмотр содержимого первого письма...")
            first_email = emails_to_show[0]

            print(f"Тема: {first_email['subject']}")
            print(f"От: {first_email['from']}")
            print(f"Дата: {first_email['date']}")
            print(f"Начало текста: {first_email['body'][:200]}...")

            # Спрашиваем об обновлении состояния
            if new_emails:
                response = input("\n❓ Обновить время последней проверки? (y/n): ")
                if response.lower() == 'y':
                    client.save_last_check_time()
                    print("✅ Время последней проверки обновлено")
        else:
            print("ℹ️ Новых и непрочитанных писем нет, проверка содержимого пропущена")

        # Отключение
        client.disconnect()
        print("\n✅ Все тесты пройдены успешно!")
        return True

    except Exception as e:
        print(f"\n❌ Ошибка во время тестирования: {str(e)}")
        client.disconnect()
        return False

def create_sample_env():
    """Создание примера .env файла"""
    env_content = """# Email настройки
EMAIL_SERVER=imap.yandex.ru
EMAIL_PORT=993
EMAIL_LOGIN=ваш_email@компания.ru
EMAIL_PASSWORD=ваш_пароль_приложения
EMAIL_SENDER=отправитель@домен.ru

# Telegram настройки
TELEGRAM_BOT_TOKEN=ваш_токен_бота
TELEGRAM_CHAT_ID=ваш_chat_id

# Настройки бота
CHECK_INTERVAL=1800
LOG_LEVEL=INFO
"""

    if not os.path.exists('.env'):
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✅ Создан файл .env с примером настроек")
        print("📝 Отредактируйте его, указав ваши данные")
    else:
        print("ℹ️ Файл .env уже существует")

if __name__ == "__main__":
    print("🤖 Тестирование email клиента")
    print("=" * 50)

    # Проверяем существование .env
    if not os.path.exists('.env'):
        print("⚠️ Файл .env не найден")
        create_sample_env()
        print("\n❗ Заполните .env файл и запустите тест снова")
        sys.exit(1)

    # Запускаем тест
    success = test_email_connection()

    if success:
        print("\n🎉 Модуль работы с почтой готов к использованию!")
        print("➡️ Следующий шаг: настройка телеграм-бота")
    else:
        print("\n💡 Проверьте настройки в .env файле и попробуйте снова")
