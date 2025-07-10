import re
import logging
from typing import Dict, Optional, List
from datetime import datetime


class EmailParser:
    """Парсер для извлечения данных из уведомлений о технических работах"""

    def __init__(self):
        """Инициализация парсера"""
        self.logger = logging.getLogger(__name__)

        # Регулярные выражения для поиска данных
        self.patterns = {
            # Оператор (Мотив, Билайн, МТС, Devino и т.д.)
            'operator': [
                r'оператор\s+([А-Яа-я\w\s]+?)(?:\s+сообщил|$)',
                r'оператора\s+([А-Яа-я\w\s]+?)(?:\s|$)',
                r'стороне оператора\s+([А-Яа-я\w\s]+?)(?:\s|$)',
                r'платформе\s+([А-Яа-я\w\s]+?)(?:\s|\.)',  # Новый паттерн для Devino
                r'платформы\s+([А-Яа-я\w\s]+?)(?:\s|\.)',
                r'сервисам\s+платформы\s+([А-Яа-я\w\s]+?)(?:\s|\.)',
                # Поиск в теме письма
                r'работы на платформе\s+([А-Яа-я\w\s]+?)(?:\s|$)',
            ],

            # Время начала работ
            'start_time': [
                r'[Нн]ачало работ[:\s]*\*?\*?\s*(\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2})',
                r'[Нн]ачало[:\s]*\*?\*?\s*(\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2})',
                r'[Сс]\s*(\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2})',
            ],

            # Время окончания работ
            'end_time': [
                r'[Оо]кончание работ[:\s]*\*?\*?\s*(\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2})',
                r'[Оо]кончание[:\s]*\*?\*?\s*(\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2})',
                r'[Пп]о\s*(\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2})',
            ],

            # Тип работ
            'work_type': [
                r'(технических работ)',
                r'(плановые работы)',
                r'(внеплановые работы)',
                r'(профилактические работы)',
                r'(аварийные работы)',
                # Поиск в теме
                r'([Вв]неплановые работы)',
                r'([Пп]лановые работы)',
            ],
        }

    def parse_email(self, email_data: Dict) -> Optional[Dict]:
        """
        Парсинг письма с уведомлением о технических работах

        Args:
            email_data: Словарь с данными письма (subject, body, from, date)

        Returns:
            Dict: Извлеченные данные или None если не удалось распарсить
        """
        try:
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')

            # Сохраняем тему для анализа типа работ
            self._current_subject = subject

            # Объединяем тему и тело для поиска
            full_text = f"{subject}\n{body}"

            self.logger.info(f"Парсинг письма: {subject[:50]}...")

            # Извлекаем данные
            parsed_data = {
                'original_subject': subject,
                'original_body': body,
                'email_date': email_data.get('date', ''),
                'email_from': email_data.get('from', ''),
                'operator': self._extract_operator(full_text),
                'start_time': self._extract_start_time(full_text),
                'end_time': self._extract_end_time(full_text),
                'work_type': self._extract_work_type(full_text),
                'description': self._extract_description(body),
                'parsed_at': datetime.now().isoformat()
            }

            # Очищаем временную переменную
            if hasattr(self, '_current_subject'):
                delattr(self, '_current_subject')

            # Проверяем, что основные данные найдены
            if parsed_data['operator'] or parsed_data['start_time'] or parsed_data['end_time']:
                self.logger.info("Успешно извлечены данные из письма")
                return parsed_data
            else:
                self.logger.warning("Не удалось извлечь основные данные из письма")
                return None

        except Exception as e:
            self.logger.error(f"Ошибка парсинга письма: {str(e)}")
            # Очищаем временную переменную в случае ошибки
            if hasattr(self, '_current_subject'):
                delattr(self, '_current_subject')
            return None

    def _extract_operator(self, text: str) -> Optional[str]:
        """Извлечение названия оператора"""
        try:
            # Специальные паттерны для разных операторов
            operator_patterns = [
                # Для классических операторов
                r'оператор\s+([А-Яа-я\w\s]+?)(?:\s+сообщил|$)',
                r'оператора\s+([А-Яа-я\w\s]+?)(?:\s|$|\.)',
                r'стороне оператора\s+([А-Яа-я\w\s]+?)(?:\s|$|\.)',

                # Для Devino Telecom
                r'платформе\s+(Devino\s+Telecom)',
                r'платформы\s+(DEVINO)',

                # Поиск в теме письма
                r'работы на стороне оператора\s+([А-Яа-я\w\s]+?)(?:\s|$)',
                r'работы на платформе\s+([А-Яа-я\w\s]+?)(?:\s|$)',
            ]

            for pattern in operator_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    operator = match.group(1).strip()
                    # Очищаем от лишних символов
                    operator = re.sub(r'[^\w\s]', '', operator).strip()
                    if operator:
                        # Специальная обработка для Devino
                        if 'devino' in operator.lower():
                            return "Devino Telecom"
                        self.logger.debug(f"Найден оператор: {operator}")
                        return operator

            # Поиск известных операторов по ключевым словам
            known_operators = [
                'Билайн', 'МТС', 'Мегафон', 'Теле2', 'Yota', 'Мотив',
                'Devino Telecom'
            ]

            text_lower = text.lower()
            for operator in known_operators:
                if operator.lower() in text_lower:
                    self.logger.debug(f"Найден оператор по ключевому слову: {operator}")
                    return operator

            return None

        except Exception as e:
            self.logger.error(f"Ошибка извлечения оператора: {str(e)}")
            return None

    def _extract_start_time(self, text: str) -> Optional[str]:
        """Извлечение времени начала работ"""
        try:
            for pattern in self.patterns['start_time']:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    start_time = match.group(1).strip()
                    self.logger.debug(f"Найдено время начала: {start_time}")
                    return start_time

            return None

        except Exception as e:
            self.logger.error(f"Ошибка извлечения времени начала: {str(e)}")
            return None

    def _extract_end_time(self, text: str) -> Optional[str]:
        """Извлечение времени окончания работ"""
        try:
            for pattern in self.patterns['end_time']:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    end_time = match.group(1).strip()
                    self.logger.debug(f"Найдено время окончания: {end_time}")
                    return end_time

            return None

        except Exception as e:
            self.logger.error(f"Ошибка извлечения времени окончания: {str(e)}")
            return None

    def _extract_work_type(self, text: str) -> Optional[str]:
        """Извлечение типа работ"""
        try:
            # Если есть тема письма, используем её как основной источник
            if hasattr(self, '_current_subject') and self._current_subject:
                subject = self._current_subject.strip()

                # Очищаем тему от лишних символов
                clean_subject = re.sub(r'^\s*[Rr][Ee]:\s*', '', subject)  # Убираем Re:
                clean_subject = clean_subject.strip()

                # Если тема содержит информацию о работах, используем её
                work_indicators = ['работы', 'работ', 'обслуживание', 'техническ']
                if any(indicator in clean_subject.lower() for indicator in work_indicators):
                    self.logger.debug(f"Используем тему как тип работ: {clean_subject}")
                    return clean_subject

            # Если тема не подходит, ищем в тексте
            specific_patterns = [
                r'([Вв]неплановые\s+работы[^.]*)',
                r'([Пп]лановые\s+работы[^.]*)',
                r'([Аа]варийные\s+работы[^.]*)',
                r'([Пп]рофилактические\s+работы[^.]*)',
                r'([Тт]ехнические\s+работы[^.]*)',
            ]

            for pattern in specific_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    work_type = match.group(1).strip()
                    self.logger.debug(f"Найден тип работ в тексте: {work_type}")
                    return work_type

            # Поиск по ключевым словам (упрощенная версия)
            text_lower = text.lower()

            if 'внеплановые' in text_lower:
                return 'Внеплановые работы'
            elif 'плановые' in text_lower:
                return 'Плановые работы'
            elif 'аварийные' in text_lower:
                return 'Аварийные работы'
            elif 'профилактические' in text_lower:
                return 'Профилактические работы'
            elif 'технических работ' in text_lower:
                return 'Технические работы'

            return None

        except Exception as e:
            self.logger.error(f"Ошибка извлечения типа работ: {str(e)}")
            return None

    def _extract_description(self, body: str) -> str:
        """Извлечение описания (очищенный текст письма)"""
        try:
            # Убираем HTML теги
            clean_body = re.sub(r'<[^>]+>', '', body)

            # Убираем множественные пробелы и переносы строк
            clean_body = re.sub(r'\s+', ' ', clean_body).strip()

            # Убираем служебную информацию
            unwanted_patterns = [
                r'Copyright.*?rights reserved',
                r'Обратная связь',
                r'Отписаться от рассылки',
                r'Открыть в браузере',
                r'Информационная рассылка',
                r'\+7\s*\(\d+\)\s*\d+-\d+-\d+',  # Телефоны
                r'Бесплатная линия.*?России',
            ]

            for pattern in unwanted_patterns:
                clean_body = re.sub(pattern, '', clean_body, flags=re.IGNORECASE)

            # Убираем лишние пробелы после очистки
            clean_body = re.sub(r'\s+', ' ', clean_body).strip()

            # Извлекаем основную часть сообщения
            # Ищем текст между "Уважаемые клиенты" и контактами/копирайтом
            main_content_match = re.search(
                r'(Уважаемые клиенты.*?)(?:Техническая поддержка|Copyright|\+7|$)',
                clean_body,
                re.IGNORECASE | re.DOTALL
            )

            if main_content_match:
                main_content = main_content_match.group(1).strip()
                # Ограничиваем длину
                if len(main_content) > 300:
                    main_content = main_content[:300] + "..."
                return main_content

            # Если не нашли основной контент, возвращаем очищенный текст
            if len(clean_body) > 300:
                clean_body = clean_body[:300] + "..."

            return clean_body if clean_body else "Описание недоступно"

        except Exception as e:
            self.logger.error(f"Ошибка извлечения описания: {str(e)}")
            return "Ошибка обработки описания"

    def format_for_telegram(self, parsed_data: Dict) -> str:
        """
        Форматирование данных для отправки в Telegram

        Args:
            parsed_data: Распарсенные данные

        Returns:
            str: Отформатированное сообщение для Telegram
        """
        try:
            # Эмодзи для красивого оформления
            emoji_map = {
                'Мотив': '📱',
                'Билайн': '🟡',
                'МТС': '🔴',
                'Мегафон': '🟢',
                'Теле2': '⚫',
                'Yota': '🟣',
                'Devino Telecom': '💻',
                'Devino': '💻',
                'DEVINO': '💻'
            }

            operator = parsed_data.get('operator', 'Неизвестный оператор')
            work_type = parsed_data.get('work_type', 'Технические работы')

            emoji = emoji_map.get(operator, '📡')

            # Формируем сообщение
            message_parts = [
                f"{emoji} *{operator}*",
                f"🚧 *{work_type}*",
                ""
            ]

            # Добавляем время начала
            if parsed_data.get('start_time'):
                message_parts.append(f"⏰ *Начало:* {parsed_data['start_time']}")

            # Добавляем время окончания
            if parsed_data.get('end_time'):
                message_parts.append(f"⏱ *Окончание:* {parsed_data['end_time']}")

            # Добавляем описание только если оно информативно
            description = parsed_data.get('description', '')
            if description and len(description) > 50 and 'ошибка' not in description.lower():
                message_parts.extend([
                    "",
                    f"📝 *Описание:*",
                    description
                ])

            # Добавляем время уведомления
            message_parts.extend([
                "",
                f"📬 _{datetime.now().strftime('%d.%m.%Y %H:%M')}_"
            ])

            return "\n".join(message_parts)

        except Exception as e:
            self.logger.error(f"Ошибка форматирования сообщения: {str(e)}")
            # Возвращаем базовое сообщение в случае ошибки
            return f"📡 Уведомление о технических работах\n\n{parsed_data.get('original_subject', 'Без темы')}"

    def is_maintenance_email(self, email_data: Dict) -> bool:
        """
        Проверка, является ли письмо уведомлением о технических работах

        Args:
            email_data: Данные письма

        Returns:
            bool: True если это уведомление о работах
        """
        try:
            subject = email_data.get('subject', '').lower()
            body = email_data.get('body', '').lower()

            # Ключевые слова для определения уведомлений о работах
            keywords = [
                'технических работ',
                'профилактических работ',
                'плановые работы',
                'внеплановые работы',
                'аварийные работы',
                'начало работ',
                'окончание работ',
                'техническое обслуживание',
                'затруднения в доставке',
                'временные неполадки'
            ]

            full_text = f"{subject} {body}"

            for keyword in keywords:
                if keyword in full_text:
                    self.logger.debug(f"Найдено ключевое слово: {keyword}")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Ошибка проверки типа письма: {str(e)}")
            return False


# Пример использования
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(level=logging.DEBUG)

    # Тестовые данные (ваш пример)
    test_email = {
        'subject': 'Уведомление о технических работах Внеплановые работы на стороне оператора Мотив',
        'body': '''Уважаемые клиенты!
Оператор Мотив сообщил о необходимости проведения технических работ.
Начало работ:** 19.06.2025 21:00 **(МСК/GMT+3)
Окончание работ:** 20.06.2025 02:00** (МСК/GMT+3)
В указанный промежуток времени могут наблюдаться затруднения в доставке сообщений абонентам данного оператора.''',
        'from': 'no-reply@devinotele.com',
        'date': '2025-06-19 18:30:00'
    }

    # Создаем парсер
    parser = EmailParser()

    # Проверяем, является ли письмо уведомлением о работах
    if parser.is_maintenance_email(test_email):
        print("✅ Это уведомление о технических работах")

        # Парсим данные
        parsed = parser.parse_email(test_email)

        if parsed:
            print("\n📊 Извлеченные данные:")
            for key, value in parsed.items():
                if key not in ['original_body', 'description']:  # Не выводим длинные поля
                    print(f"  {key}: {value}")

            print("\n📱 Сообщение для Telegram:")
            telegram_message = parser.format_for_telegram(parsed)
            print(telegram_message)
        else:
            print("❌ Не удалось извлечь данные")
    else:
        print("ℹ️ Это не уведомление о технических работах")
