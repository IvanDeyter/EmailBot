#!/usr/bin/env python3
"""
Тестовый скрипт для проверки парсера писем
"""

import logging
import sys
import os
from dotenv import load_dotenv

# Добавляем путь к нашим модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from email_client import EmailClient
from parser import EmailParser

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_parser_with_sample():
    """Тест парсера на примере письма"""
    
    # Ваш пример письма
    sample_email = {
        'subject': 'Уведомление о технических работах Внеплановые работы на стороне оператора Мотив',
        'body': '''Уважаемые клиенты!
Оператор Мотив сообщил о необходимости проведения технических работ.
Начало работ:** 19.06.2025 21:00 **(МСК/GMT+3)
Окончание работ:** 20.06.2025 02:00** (МСК/GMT+3)
В указанный промежуток времени могут наблюдаться затруднения в доставке сообщений абонентам данного оператора.''',
        'from': 'no-reply@devinotele.com',
        'date': '2025-06-19 18:30:00',
        'id': 12345
    }
    
    print("🧪 Тестирование парсера на примере письма")
    print("=" * 60)
    
    parser = EmailParser()
    
    print("📧 Исходное письмо:")
    print(f"Тема: {sample_email['subject']}")
    print(f"Текст: {sample_email['body'][:100]}...")
    print("-" * 40)
    
    # Тест 1: Проверка типа письма
    print("\n🔍 Тест 1: Определение типа письма...")
    is_maintenance = parser.is_maintenance_email(sample_email)
    print(f"Результат: {'✅ Уведомление о работах' if is_maintenance else '❌ Обычное письмо'}")
    
    if not is_maintenance:
        print("❌ Парсер не распознал письмо как уведомление о работах")
        return False
    
    # Тест 2: Парсинг данных
    print("\n📊 Тест 2: Извлечение данных...")
    parsed_data = parser.parse_email(sample_email)
    
    if not parsed_data:
        print("❌ Не удалось извлечь данные из письма")
        return False
    
    print("✅ Данные успешно извлечены:")
    for key, value in parsed_data.items():
        if key not in ['original_body', 'description', 'parsed_at']:
            print(f"  📝 {key}: {value}")
    
    # Тест 3: Форматирование для Telegram
    print("\n📱 Тест 3: Форматирование для Telegram...")
    telegram_message = parser.format_for_telegram(parsed_data)
    
    print("✅ Сообщение для Telegram:")
    print("-" * 40)
    print(telegram_message)
    print("-" * 40)
    
    return True

def test_parser_with_real_emails():
    """Тест парсера на реальных письмах из почты"""
    
    # Загружаем настройки
    load_dotenv()
    
    server = os.getenv('EMAIL_SERVER', 'imap.yandex.ru')
    port = int(os.getenv('EMAIL_PORT', 993))
    login = os.getenv('EMAIL_LOGIN')
    password = os.getenv('EMAIL_PASSWORD')
    sender = os.getenv('EMAIL_SENDER')
    
    if not all([login, password, sender]):
        print("❌ Настройки почты не заданы в .env файле")
        return False
    
    print("\n🌐 Тестирование парсера на реальных письмах")
    print("=" * 60)
    
    # Подключаемся к почте
    client = EmailClient(server, port, login, password)
    parser = EmailParser()
    
    try:
        if not client.connect():
            print("❌ Не удалось подключиться к почте")
            return False
        
        if not client.select_mailbox():
            print("❌ Не удалось выбрать папку INBOX")
            return False
        
        # Ищем письма от отправителя за последние 7 дней
        print(f"🔍 Поиск писем от {sender}...")
        email_ids = client.search_emails_from_sender(sender, days_back=7)
        
        if not email_ids:
            print("❌ Письма не найдены")
            return False
        
        print(f"✅ Найдено {len(email_ids)} писем")
        
        # Берем последние 3 письма для теста
        test_ids = email_ids[-3:] if len(email_ids) >= 3 else email_ids
        
        for i, email_id in enumerate(test_ids, 1):
            print(f"\n📧 Тест письма {i}/{len(test_ids)} (ID: {email_id})")
            print("-" * 40)
            
            # Получаем содержимое письма
            email_data = client.get_email_content(email_id)
            if not email_data:
                print(f"❌ Не удалось получить письмо {email_id}")
                continue
            
            print(f"Тема: {email_data['subject'][:60]}...")
            print(f"Дата: {email_data['date']}")
            
            # Проверяем тип письма
            is_maintenance = parser.is_maintenance_email(email_data)
            print(f"Тип: {'🚧 Уведомление о работах' if is_maintenance else '📄 Обычное письмо'}")
            
            if is_maintenance:
                # Парсим данные
                parsed_data = parser.parse_email(email_data)
                if parsed_data:
                    print("✅ Успешно распарсено:")
                    print(f"  Оператор: {parsed_data.get('operator', 'Не найден')}")
                    print(f"  Начало: {parsed_data.get('start_time', 'Не найдено')}")
                    print(f"  Окончание: {parsed_data.get('end_time', 'Не найдено')}")
                    print(f"  Тип работ: {parsed_data.get('work_type', 'Не найден')}")
                    
                    # Показываем сообщение для Telegram
                    telegram_msg = parser.format_for_telegram(parsed_data)
                    print(f"\n📱 Telegram сообщение:")
                    print(telegram_msg[:200] + "..." if len(telegram_msg) > 200 else telegram_msg)
                else:
                    print("❌ Не удалось извлечь данные")
        
        client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        client.disconnect()
        return False

def main():
    """Главная функция теста"""
    
    print("🔧 Тестирование модуля парсинга писем")
    print("=" * 60)
    
    # Тест 1: На примере письма
    success1 = test_parser_with_sample()
    
    # Тест 2: На реальных письмах
    if success1:
        response = input("\n❓ Протестировать на реальных письмах из почты? (y/n): ")
        if response.lower() == 'y':
            success2 = test_parser_with_real_emails()
        else:
            success2 = True
            print("ℹ️ Тест на реальных письмах пропущен")
    else:
        success2 = False
    
    # Итоги
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 Все тесты пройдены успешно!")
        print("➡️ Парсер готов к использованию")
        print("📝 Следующий шаг: создание Telegram бота")
    else:
        print("💡 Есть проблемы с парсером, нужно доработать регулярные выражения")

if __name__ == "__main__":
    main()