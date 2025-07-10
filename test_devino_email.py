#!/usr/bin/env python3
"""
Тест парсера на реальном письме от Devino Telecom
"""

import logging
import sys
import os

# Добавляем путь к нашим модулям
sys.path.append(os.path.dirname(__file__))

try:
    from parser import EmailParser
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

def test_devino_email():
    """Тест на реальном письме от Devino"""
    
    print("🧪 Тестирование парсера на письме Devino Telecom")
    print("=" * 60)
    
    # Реальные данные письма
    devino_email = {
        'subject': 'Внеплановые работы на платформе Devino Telecom',
        'body': '''Информационная рассылка Открыть в браузере +7 (495) 646-0054 +7 (800) 555-0054 Бесплатная линия по РоссииУведомление о технических работах Внеплановые работы на платформе Devino Telecom 
 
Уважаемые клиенты!
Уведомляем Вас о необходимости проведения внеплановых технических работ на платформе Devino Telecom.
Начало работ:** 26.06.2025 19:00** (МСК/GMT+3)
Окончание работ:** 26.06.2025 20:00** (МСК/GMT+3)
В указанный промежуток возможно несколько прерываний доступа к сервисам платформы DEVINO.
**Техническая поддержка Devino Telecom.**
*Copyright © 2025, All rights reserved.* Обратная связь Отписаться от рассылки''',
        'from': 'no-reply@devinotele.com',
        'date': '2025-06-26 17:00:00'
    }
    
    # Создаем парсер
    parser = EmailParser()
    
    print("📧 Исходное письмо:")
    print(f"Тема: {devino_email['subject']}")
    print(f"От: {devino_email['from']}")
    print("-" * 40)
    
    # Тест 1: Проверка типа письма
    print("\n🔍 Тест 1: Определение типа письма...")
    is_maintenance = parser.is_maintenance_email(devino_email)
    print(f"Результат: {'✅ Уведомление о работах' if is_maintenance else '❌ Обычное письмо'}")
    
    if not is_maintenance:
        print("❌ Парсер не распознал письмо как уведомление о работах")
        return False
    
    # Тест 2: Парсинг данных
    print("\n📊 Тест 2: Извлечение данных...")
    parsed_data = parser.parse_email(devino_email)
    
    if not parsed_data:
        print("❌ Не удалось извлечь данные из письма")
        return False
    
    print("✅ Данные успешно извлечены:")
    print(f"  📝 Оператор: {parsed_data.get('operator', 'НЕ НАЙДЕН')}")
    print(f"  📝 Начало: {parsed_data.get('start_time', 'НЕ НАЙДЕНО')}")
    print(f"  📝 Окончание: {parsed_data.get('end_time', 'НЕ НАЙДЕНО')}")
    print(f"  📝 Тип работ: {parsed_data.get('work_type', 'НЕ НАЙДЕН')}")
    
    # Тест 3: Форматирование для Telegram
    print("\n📱 Тест 3: Форматирование для Telegram...")
    telegram_message = parser.format_for_telegram(parsed_data)
    
    print("✅ Сообщение для Telegram:")
    print("-" * 40)
    print(telegram_message)
    print("-" * 40)
    
    # Проверяем ожидаемые результаты
    expected_results = {
        'operator': 'Devino Telecom',
        'start_time': '26.06.2025 19:00',
        'end_time': '26.06.2025 20:00',
        'work_type': 'внеплановые работы'
    }
    
    print("\n📋 Проверка ожидаемых результатов:")
    all_correct = True
    
    for key, expected in expected_results.items():
        actual = parsed_data.get(key, '')
        if expected.lower() in actual.lower() if actual else False:
            print(f"  ✅ {key}: {actual}")
        else:
            print(f"  ❌ {key}: ожидалось '{expected}', получено '{actual}'")
            all_correct = False
    
    return all_correct

def main():
    """Главная функция теста"""
    
    success = test_devino_email()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Все тесты пройдены успешно!")
        print("✅ Парсер готов для работы с письмами Devino Telecom")
    else:
        print("💡 Есть проблемы с парсингом, нужно доработать регулярные выражения")

if __name__ == "__main__":
    main()