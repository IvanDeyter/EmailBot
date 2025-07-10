#!/usr/bin/env python3
"""
Тестовый скрипт для проверки Telegram бота
"""

import logging
import sys
import os
from dotenv import load_dotenv

# Добавляем путь к нашим модулям
sys.path.append(os.path.dirname(__file__))

try:
    from telegram_bot import TelegramBotSync
    from parser import EmailParser
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("📝 Убедитесь, что файлы telegram_bot.py и parser.py находятся в корне проекта")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_requirements():
    """Проверка установленных зависимостей"""
    try:
        import telegram
        print(f"✅ python-telegram-bot установлен (версия: {telegram.__version__})")
        return True
    except ImportError:
        print("❌ Не установлена библиотека python-telegram-bot")
        print("📦 Установите: pip install python-telegram-bot")
        return False

def get_chat_id_instructions():
    """Инструкции по получению Chat ID"""
    instructions = """
📝 Как получить Chat ID группы:

1️⃣ Создайте группу в Telegram
2️⃣ Добавьте вашего бота в группу (@SM_Email_parser_notify_bot)
3️⃣ Дайте боту права администратора (опционально)
4️⃣ Отправьте любое сообщение в группу
5️⃣ Перейдите по ссылке:
   https://api.telegram.org/bot<ВАШ_ТОКЕН>/getUpdates
6️⃣ Найдите в ответе "chat":{"id":-1001234567890}
7️⃣ Скопируйте ID (включая минус!)

💡 Или используйте бота @userinfobot - добавьте его в группу и он покажет ID
"""
    return instructions

def test_telegram_setup():
    """Проверка настроек Telegram"""

    print("🔧 Проверка настроек Telegram...")

    # Загружаем переменные окружения
    load_dotenv()

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    print(f"Bot Token: {'✅ Задан' if bot_token else '❌ Не задан'}")
    print(f"Chat ID: {'✅ Задан' if chat_id else '❌ Не задан'}")

    if not bot_token:
        print("\n📝 Как получить Bot Token:")
        print("1. Найдите @BotFather в Telegram")
        print("2. Отправьте /newbot")
        print("3. Следуйте инструкциям")
        print("4. Скопируйте токен в .env файл")
        return False, None, None

    if not chat_id:
        print(get_chat_id_instructions())
        return False, bot_token, None

    return True, bot_token, chat_id

def test_telegram_connection(bot_token: str, chat_id: str):
    """Тест подключения к Telegram"""

    print("\n📡 Тестирование подключения к Telegram...")
    print("-" * 50)

    try:
        # Проверяем настройку прокси
        load_dotenv()
        proxy_url = os.getenv('TELEGRAM_PROXY_URL')

        if proxy_url:
            print(f"🔧 Используется прокси: {proxy_url}")

        # Создаем бота
        bot = TelegramBotSync(bot_token, chat_id, proxy_url)

        # Тест 1: Подключение к API
        print("🔗 Тест 1: Подключение к Telegram API...")
        if bot.test_connection():
            print("✅ Подключение успешно")
        else:
            print("❌ Ошибка подключения")
            print("\n💡 Запустите диагностику: python test_telegram_connection.py")
            return False

        # Тест 2: Отправка тестового сообщения
        print("\n📤 Тест 2: Отправка тестового сообщения...")
        if bot.send_test_message():
            print("✅ Тестовое сообщение отправлено")
        else:
            print("❌ Ошибка отправки сообщения")
            return False

        return True

    except Exception as e:
        print(f"❌ Ошибка тестирования: {str(e)}")
        return False

def test_maintenance_notification():
    """Тест отправки уведомления о технических работах"""

    print("\n🚧 Тест 3: Отправка уведомления о технических работах...")

    # Загружаем настройки
    load_dotenv()
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("❌ Настройки Telegram не заданы")
        return False

    try:
        # Создаем бота и парсер
        bot = TelegramBotSync(bot_token, chat_id)
        parser = EmailParser()

        # Тестовые данные (ваш пример)
        sample_email = {
            'subject': 'Уведомление о технических работах Внеплановые работы на стороне оператора Мотив',
            'body': '''Уважаемые клиенты!
Оператор Мотив сообщил о необходимости проведения технических работ.
Начало работ:** 19.06.2025 21:00 **(МСК/GMT+3)
Окончание работ:** 20.06.2025 02:00** (МСК/GMT+3)
В указанный промежуток времени могут наблюдаться затруднения в доставке сообщений абонентам данного оператора.''',
            'from': 'no-reply@devinotele.com',
            'date': '2025-06-19 18:30:00'
        }

        # Парсим данные
        parsed_data = parser.parse_email(sample_email)

        if not parsed_data:
            print("❌ Не удалось распарсить тестовое письмо")
            return False

        print("📊 Парсинг данных:")
        print(f"  Оператор: {parsed_data.get('operator')}")
        print(f"  Начало: {parsed_data.get('start_time')}")
        print(f"  Окончание: {parsed_data.get('end_time')}")

        # Отправляем уведомление
        if bot.send_maintenance_notification(parsed_data):
            print("✅ Уведомление о технических работах отправлено")
            return True
        else:
            print("❌ Ошибка отправки уведомления")
            return False

    except Exception as e:
        print(f"❌ Ошибка теста уведомления: {str(e)}")
        return False

def main():
    """Главная функция теста"""

    print("🤖 Тестирование Telegram бота")
    print("=" * 60)

    # Проверяем зависимости
    if not check_requirements():
        return

    # Проверяем настройки
    settings_ok, bot_token, chat_id = test_telegram_setup()

    if not settings_ok:
        print("\n💡 Настройте токен бота и Chat ID в .env файле и запустите тест снова")
        return

    # Тестируем подключение
    if test_telegram_connection(bot_token, chat_id):
        print("\n🎉 Базовые тесты пройдены!")

        # Тестируем уведомления
        response = input("\n❓ Отправить тестовое уведомление о технических работах? (y/n): ")
        if response.lower() == 'y':
            if test_maintenance_notification():
                print("\n🎉 Все тесты Telegram бота пройдены успешно!")
                print("➡️ Telegram бот готов к работе")
                print("📝 Следующий шаг: создание основного цикла бота")
            else:
                print("\n💡 Есть проблемы с отправкой уведомлений")
        else:
            print("\n✅ Базовое тестирование завершено")
    else:
        print("\n💡 Проверьте настройки Telegram и попробуйте снова")

if __name__ == "__main__":
    main()
