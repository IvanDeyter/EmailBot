#!/usr/bin/env python3
"""
Полный тест всей системы Email-Telegram бота
"""

import logging
import sys
import os
from dotenv import load_dotenv

# Добавляем путь к нашим модулям
sys.path.append(os.path.dirname(__file__))

try:
    from email_client import EmailClient
    from parser import EmailParser
    from telegram_bot import TelegramBotSync
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

def test_full_pipeline():
    """Тест полного процесса обработки письма"""
    
    print("🧪 Тестирование полного процесса обработки")
    print("=" * 60)
    
    # Загружаем настройки
    load_dotenv()
    
    # Проверяем настройки
    required_vars = [
        'EMAIL_LOGIN', 'EMAIL_PASSWORD', 'EMAIL_SENDER',
        'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Не заданы переменные: {missing_vars}")
        return False
    
    try:
        # Шаг 1: Инициализация компонентов
        print("🔧 Шаг 1: Инициализация компонентов...")
        
        email_client = EmailClient(
            server=os.getenv('EMAIL_SERVER', 'imap.yandex.ru'),
            port=int(os.getenv('EMAIL_PORT', 993)),
            login=os.getenv('EMAIL_LOGIN'),
            password=os.getenv('EMAIL_PASSWORD')
        )
        
        parser = EmailParser()
        
        telegram_bot = TelegramBotSync(
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            chat_id=os.getenv('TELEGRAM_CHAT_ID'),
            proxy_url=os.getenv('TELEGRAM_PROXY_URL')
        )
        
        print("✅ Компоненты инициализированы")
        
        # Шаг 2: Тест подключений
        print("\n🔗 Шаг 2: Тестирование подключений...")
        
        # Email подключение
        if not email_client.connect():
            print("❌ Ошибка подключения к почте")
            return False
        
        if not email_client.select_mailbox():
            print("❌ Ошибка выбора почтового ящика")
            return False
        
        print("✅ Подключение к почте успешно")
        
        # Telegram подключение
        if not telegram_bot.test_connection():
            print("❌ Ошибка подключения к Telegram")
            return False
        
        print("✅ Подключение к Telegram успешно")
        
        # Шаг 3: Тест на реальных письмах
        print(f"\n📧 Шаг 3: Поиск писем от {os.getenv('EMAIL_SENDER')}...")
        
        # Ищем новые письма (без обновления состояния)
        new_emails = email_client.get_new_emails_from_sender(
            os.getenv('EMAIL_SENDER'), 
            update_state=False
        )
        
        print(f"✅ Найдено {len(new_emails)} новых писем")
        
        if not new_emails:
            print("ℹ️ Новых писем нет, тестируем на примере...")
            
            # Используем тестовый пример
            test_email = {
                'subject': 'Уведомление о технических работах Внеплановые работы на стороне оператора Мотив',
                'body': '''Уважаемые клиенты!
Оператор Мотив сообщил о необходимости проведения технических работ.
Начало работ:** 19.06.2025 21:00 **(МСК/GMT+3)
Окончание работ:** 20.06.2025 02:00** (МСК/GMT+3)
В указанный промежуток времени могут наблюдаться затруднения в доставке сообщений абонентам данного оператора.''',
                'from': os.getenv('EMAIL_SENDER'),
                'date': '2025-06-19 18:30:00'
            }
            
            emails_to_process = [test_email]
        else:
            # Берем первое письмо для теста
            emails_to_process = [new_emails[0]]
        
        # Шаг 4: Обработка письма
        print(f"\n🔍 Шаг 4: Обработка письма...")
        
        test_email = emails_to_process[0]
        print(f"Тема: {test_email['subject'][:60]}...")
        
        # Проверяем тип письма
        is_maintenance = parser.is_maintenance_email(test_email)
        print(f"Тип письма: {'🚧 Уведомление о работах' if is_maintenance else '📄 Обычное письмо'}")
        
        if not is_maintenance:
            print("ℹ️ Письмо не является уведомлением о работах")
            print("✅ Процесс фильтрации работает корректно")
        else:
            # Парсим данные
            parsed_data = parser.parse_email(test_email)
            
            if not parsed_data:
                print("❌ Ошибка парсинга письма")
                return False
            
            print("✅ Данные успешно извлечены:")
            print(f"  • Оператор: {parsed_data.get('operator', 'Не найден')}")
            print(f"  • Начало: {parsed_data.get('start_time', 'Не найдено')}")
            print(f"  • Окончание: {parsed_data.get('end_time', 'Не найдено')}")
            print(f"  • Тип работ: {parsed_data.get('work_type', 'Не найден')}")
            
            # Шаг 5: Отправка уведомления
            print(f"\n📤 Шаг 5: Отправка уведомления в Telegram...")
            
            response = input("❓ Отправить уведомление в Telegram? (y/n): ")
            if response.lower() == 'y':
                if telegram_bot.send_maintenance_notification(parsed_data):
                    print("✅ Уведомление отправлено успешно")
                else:
                    print("❌ Ошибка отправки уведомления")
                    return False
            else:
                print("ℹ️ Отправка уведомления пропущена")
        
        # Шаг 6: Завершение
        print(f"\n🏁 Шаг 6: Завершение тестирования...")
        email_client.disconnect()
        print("✅ Отключение от почты")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {str(e)}")
        return False

def show_bot_status():
    """Показать статус готовности бота"""
    
    print("\n📊 Статус готовности бота:")
    print("-" * 40)
    
    load_dotenv()
    
    # Проверяем конфигурацию
    config_items = [
        ('EMAIL_LOGIN', 'Email логин'),
        ('EMAIL_PASSWORD', 'Email пароль'),
        ('EMAIL_SENDER', 'Email отправитель'),
        ('TELEGRAM_BOT_TOKEN', 'Telegram токен'),
        ('TELEGRAM_CHAT_ID', 'Telegram Chat ID'),
    ]
    
    all_configured = True
    
    for env_var, description in config_items:
        value = os.getenv(env_var)
        status = "✅" if value else "❌"
        print(f"{status} {description}")
        if not value:
            all_configured = False
    
    optional_items = [
        ('EMAIL_SERVER', 'Email сервер', 'imap.yandex.ru'),
        ('EMAIL_PORT', 'Email порт', '993'),
        ('CHECK_INTERVAL', 'Интервал проверки', '1800'),
        ('TELEGRAM_PROXY_URL', 'Telegram прокси', 'не задан'),
    ]
    
    print("\nДополнительные настройки:")
    for env_var, description, default in optional_items:
        value = os.getenv(env_var, default)
        print(f"ℹ️ {description}: {value}")
    
    print("\n" + "=" * 40)
    
    if all_configured:
        print("🎉 Бот полностью настроен и готов к запуску!")
        print("➡️ Запустите: python main.py")
    else:
        print("⚠️ Необходимо завершить настройку")
        print("📝 Заполните недостающие параметры в .env файле")

def main():
    """Главная функция теста"""
    
    print("🤖 Полное тестирование Email-Telegram бота")
    print("=" * 60)
    
    # Показываем статус конфигурации
    show_bot_status()
    
    # Запрашиваем тестирование
    if input("\n❓ Запустить полное тестирование? (y/n): ").lower() == 'y':
        if test_full_pipeline():
            print("\n🎉 Все тесты пройдены успешно!")
            print("🚀 Бот готов к работе в продакшене")
            print("\n📝 Для запуска бота используйте:")
            print("   python main.py")
        else:
            print("\n💡 Есть проблемы, которые нужно исправить")
    else:
        print("ℹ️ Тестирование пропущено")

if __name__ == "__main__":
    main()