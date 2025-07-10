import imaplib
import email
from email.header import decode_header
import ssl
import logging
import json
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime


class EmailClient:
    """Клиент для работы с IMAP почтой"""

    def __init__(self, server: str, port: int, login: str, password: str, state_file: str = 'bot_state.json'):
        """
        Инициализация клиента

        Args:
            server: IMAP сервер (например, imap.yandex.ru)
            port: Порт IMAP (обычно 993 для SSL)
            login: Логин для входа
            password: Пароль (лучше пароль приложения)
            state_file: Файл для хранения состояния бота (время последней проверки)
        """
        self.server = server
        self.port = port
        self.login = login
        self.password = password
        self.connection = None
        self.logger = logging.getLogger(__name__)
        self.state_file = state_file

    def connect(self) -> bool:
        """
        Подключение к IMAP серверу

        Returns:
            bool: True если подключение успешно, False иначе
        """
        try:
            self.logger.info(f"Подключаемся к {self.server}:{self.port}")

            # Создаем SSL контекст
            context = ssl.create_default_context()

            # Подключаемся к серверу
            self.connection = imaplib.IMAP4_SSL(self.server, self.port, ssl_context=context)

            # Авторизуемся
            result = self.connection.login(self.login, self.password)

            if result[0] == 'OK':
                self.logger.info("Успешное подключение к почтовому серверу")
                return True
            else:
                self.logger.error(f"Ошибка авторизации: {result}")
                return False

        except Exception as e:
            self.logger.error(f"Ошибка подключения: {str(e)}")
            return False

    def load_last_check_time(self) -> Optional[datetime]:
        """
        Загрузить время последней проверки из файла состояния

        Returns:
            datetime: Время последней проверки или None если файла нет
        """
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    last_check_str = state_data.get('last_check_time')
                    if last_check_str:
                        last_check = datetime.fromisoformat(last_check_str)
                        self.logger.info(f"Загружено время последней проверки: {last_check}")
                        return last_check

            self.logger.info("Файл состояния не найден, это первый запуск")
            return None

        except Exception as e:
            self.logger.error(f"Ошибка загрузки состояния: {str(e)}")
            return None

    def save_last_check_time(self, check_time: datetime = None):
        """
        Сохранить время последней проверки в файл состояния

        Args:
            check_time: Время для сохранения (по умолчанию текущее время)
        """
        try:
            if check_time is None:
                check_time = datetime.now()

            state_data = {
                'last_check_time': check_time.isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Сохранено время последней проверки: {check_time}")

        except Exception as e:
            self.logger.error(f"Ошибка сохранения состояния: {str(e)}")

    def disconnect(self):
        """Отключение от сервера"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                self.logger.info("Отключение от почтового сервера")
            except Exception as e:
                self.logger.error(f"Ошибка при отключении: {str(e)}")

    def select_mailbox(self, mailbox: str = 'INBOX') -> bool:
        """
        Выбор почтового ящика

        Args:
            mailbox: Название ящика (по умолчанию INBOX)

        Returns:
            bool: True если выбор успешен
        """
        try:
            result = self.connection.select(mailbox)
            if result[0] == 'OK':
                self.logger.info(f"Выбран ящик: {mailbox}")
                return True
            else:
                self.logger.error(f"Ошибка выбора ящика {mailbox}: {result}")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при выборе ящика: {str(e)}")
            return False

    def search_new_emails_from_sender(self, sender_email: str) -> List[int]:
        """
        Поиск новых писем от конкретного отправителя с момента последней проверки

        Args:
            sender_email: Email отправителя

        Returns:
            List[int]: Список ID новых писем
        """
        try:
            # Загружаем время последней проверки
            last_check = self.load_last_check_time()

            if last_check is None:
                # Если это первый запуск, ищем письма за последние 24 часа
                since_date = (datetime.now() - timedelta(hours=24)).strftime("%d-%b-%Y")
                self.logger.info(f"Первый запуск - поиск писем от {sender_email} с {since_date}")
            else:
                # Ищем письма с момента последней проверки
                since_date = last_check.strftime("%d-%b-%Y")
                self.logger.info(f"Поиск новых писем от {sender_email} с {since_date}")

            # Поисковый запрос
            search_criteria = f'(FROM "{sender_email}" SINCE {since_date})'
            result, message_ids = self.connection.search(None, search_criteria)

            if result != 'OK':
                self.logger.error(f"Ошибка поиска: {result}")
                return []

            if not message_ids[0]:
                self.logger.info("Новых писем не найдено")
                return []

            # Получаем все ID писем
            all_ids = [int(id_) for id_ in message_ids[0].split()]

            # Если это не первый запуск, фильтруем по точному времени
            if last_check is not None:
                new_ids = []
                for email_id in all_ids:
                    email_date = self._get_email_date(email_id)
                    if email_date and email_date > last_check:
                        new_ids.append(email_id)

                self.logger.info(f"Найдено {len(new_ids)} новых писем (из {len(all_ids)} общих)")
                return new_ids
            else:
                self.logger.info(f"Найдено {len(all_ids)} писем за последние 24 часа")
                return all_ids

        except Exception as e:
            self.logger.error(f"Ошибка при поиске новых писем: {str(e)}")
            return []

    def _get_email_date(self, email_id: int) -> Optional[datetime]:
        """
        Получить дату письма

        Args:
            email_id: ID письма

        Returns:
            datetime: Дата письма или None
        """
        try:
            # Получаем только заголовок с датой для скорости
            result, msg_data = self.connection.fetch(str(email_id), '(BODY[HEADER.FIELDS (DATE)])')

            if result != 'OK' or not msg_data[0]:
                return None

            header = msg_data[0][1].decode('utf-8', errors='ignore')

            # Ищем строку с датой
            for line in header.split('\n'):
                if line.lower().startswith('date:'):
                    date_str = line[5:].strip()
                    try:
                        # Парсим дату письма
                        email_date = parsedate_to_datetime(date_str)
                        # Приводим к локальному времени (убираем timezone info для сравнения)
                        return email_date.replace(tzinfo=None)
                    except Exception as e:
                        self.logger.error(f"Ошибка парсинга даты '{date_str}': {str(e)}")
                        return None

            return None

        except Exception as e:
            self.logger.error(f"Ошибка получения даты письма {email_id}: {str(e)}")
            return None

    def search_emails_from_sender(self, sender_email: str, days_back: int = 1) -> List[int]:
        """
        Поиск писем от конкретного отправителя (старый метод для совместимости)

        Args:
            sender_email: Email отправителя
            days_back: Количество дней назад для поиска

        Returns:
            List[int]: Список ID писем
        """
        try:
            # Формируем дату для поиска
            since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")

            # Поисковый запрос
            search_criteria = f'(FROM "{sender_email}" SINCE {since_date})'

            self.logger.info(f"Поиск писем от {sender_email} с {since_date}")

            result, message_ids = self.connection.search(None, search_criteria)

            if result == 'OK':
                if message_ids[0]:
                    ids = message_ids[0].split()
                    email_ids = [int(id_) for id_ in ids]
                    self.logger.info(f"Найдено {len(email_ids)} писем")
                    return email_ids
                else:
                    self.logger.info("Писем не найдено")
                    return []
            else:
                self.logger.error(f"Ошибка поиска: {result}")
                return []

        except Exception as e:
            self.logger.error(f"Ошибка при поиске писем: {str(e)}")
            return []

    def get_email_content(self, email_id: int) -> Optional[Dict]:
        """
        Получение содержимого письма

        Args:
            email_id: ID письма

        Returns:
            Dict: Словарь с данными письма или None
        """
        try:
            # Получаем письмо
            result, message_data = self.connection.fetch(str(email_id), '(RFC822)')

            if result != 'OK':
                self.logger.error(f"Ошибка получения письма {email_id}")
                return None

            # Парсим письмо
            raw_email = message_data[0][1]
            email_message = email.message_from_bytes(raw_email)

            # Извлекаем основные данные
            email_data = {
                'id': email_id,
                'subject': self._decode_mime_words(email_message.get('Subject', '')),
                'from': self._decode_mime_words(email_message.get('From', '')),
                'date': email_message.get('Date', ''),
                'body': self._extract_body(email_message)
            }

            return email_data

        except Exception as e:
            self.logger.error(f"Ошибка обработки письма {email_id}: {str(e)}")
            return None

    def mark_as_read(self, email_id: int) -> bool:
        """
        Пометить письмо как прочитанное

        Args:
            email_id: ID письма

        Returns:
            bool: True если успешно
        """
        try:
            result = self.connection.store(str(email_id), '+FLAGS', '\\Seen')
            if result[0] == 'OK':
                self.logger.info(f"Письмо {email_id} помечено как прочитанное")
                return True
            else:
                self.logger.error(f"Ошибка пометки письма {email_id}: {result}")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при пометке письма: {str(e)}")
            return False

    def _decode_mime_words(self, text: str) -> str:
        """Декодирование MIME заголовков"""
        try:
            decoded_fragments = decode_header(text)
            decoded_text = ''

            for fragment, encoding in decoded_fragments:
                if isinstance(fragment, bytes):
                    if encoding:
                        decoded_text += fragment.decode(encoding)
                    else:
                        decoded_text += fragment.decode('utf-8')
                else:
                    decoded_text += fragment

            return decoded_text
        except Exception as e:
            self.logger.error(f"Ошибка декодирования заголовка: {str(e)}")
            return text

    def _extract_body(self, email_message) -> str:
        """Извлечение текста письма"""
        try:
            body = ""

            if email_message.is_multipart():
                # Если письмо многочастное
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    # Ищем текстовые части
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        body = part.get_payload(decode=True)
                        break
                    elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                        # Если plain text не найден, берем HTML
                        body = part.get_payload(decode=True)
            else:
                # Простое письмо
                body = email_message.get_payload(decode=True)

            # Декодируем в строку
            if isinstance(body, bytes):
                # Пытаемся определить кодировку
                try:
                    body = body.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        body = body.decode('cp1251')
                    except UnicodeDecodeError:
                        body = body.decode('utf-8', errors='ignore')

            return body.strip()

        except Exception as e:
            self.logger.error(f"Ошибка извлечения тела письма: {str(e)}")
            return ""

    def get_new_emails_from_sender(self, sender_email: str, update_state: bool = True, retry_count: int = 3) -> List[Dict]:
        """
        Получить все новые письма от отправителя с момента последней проверки

        Args:
            sender_email: Email отправителя
            update_state: Обновить ли время последней проверки после получения писем
            retry_count: Количество попыток при ошибках соединения

        Returns:
            List[Dict]: Список словарей с данными новых писем
        """
        last_error = None

        for attempt in range(retry_count):
            try:
                # Проверяем соединение и переподключаемся если нужно
                if not self._ensure_connection():
                    self.logger.error("Не удалось установить соединение с сервером")
                    continue

                # Ищем новые письма
                new_email_ids = self.search_new_emails_from_sender(sender_email)

                if not new_email_ids:
                    if update_state:
                        self.save_last_check_time()
                    return []

                # Получаем содержимое новых писем
                emails = []
                for email_id in new_email_ids:
                    email_data = self.get_email_content(email_id)
                    if email_data:
                        emails.append(email_data)

                self.logger.info(f"Получено {len(emails)} новых писем")

                # Обновляем время последней проверки
                if update_state:
                    self.save_last_check_time()

                return emails

            except Exception as e:
                last_error = e
                error_msg = str(e).lower()

                # Проверяем, является ли это ошибкой соединения
                if any(err in error_msg for err in ['broken pipe', 'connection', 'socket', 'timeout']):
                    self.logger.warning(f"Ошибка соединения (попытка {attempt + 1}/{retry_count}): {str(e)}")

                    # Закрываем текущее соединение
                    self._disconnect_internal()

                    # Ждем перед повторной попыткой
                    if attempt < retry_count - 1:
                        import time
                        time.sleep(5)  # Пауза 5 секунд перед повторной попыткой
                        continue
                else:
                    # Для других ошибок не повторяем
                    self.logger.error(f"Ошибка получения новых писем: {str(e)}")
                    break

        # Если все попытки исчерпаны
        self.logger.error(f"Не удалось получить письма после {retry_count} попыток. Последняя ошибка: {str(last_error)}")
        return []

    def _ensure_connection(self) -> bool:
        """
        Убедиться что соединение активно, переподключиться если нужно

        Returns:
            bool: True если соединение активно
        """
        try:
            # Проверяем есть ли соединение
            if not self.connection:
                self.logger.info("Соединение отсутствует, подключаемся...")
                return self.connect() and self.select_mailbox()

            # Проверяем активность соединения простым NOOP командой
            try:
                result = self.connection.noop()
                if result[0] == 'OK':
                    return True
                else:
                    self.logger.warning(f"NOOP команда вернула: {result}")
            except Exception as e:
                self.logger.warning(f"Ошибка проверки соединения: {str(e)}")

            # Если проверка не прошла, переподключаемся
            self.logger.info("Переподключение к серверу...")
            self._disconnect_internal()
            return self.connect() and self.select_mailbox()

        except Exception as e:
            self.logger.error(f"Ошибка проверки соединения: {str(e)}")
            return False

    def _disconnect_internal(self):
        """Внутреннее отключение без логирования"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass  # Игнорируем ошибки при отключении
            finally:
                self.connection = None

    def get_unread_emails_from_sender(self, sender_email: str) -> List[Dict]:
        """
        Получить все непрочитанные письма от отправителя (старый метод для совместимости)

        Args:
            sender_email: Email отправителя

        Returns:
            List[Dict]: Список словарей с данными писем
        """
        try:
            # Поиск непрочитанных писем от отправителя
            search_criteria = f'(FROM "{sender_email}" UNSEEN)'
            result, message_ids = self.connection.search(None, search_criteria)

            if result != 'OK' or not message_ids[0]:
                self.logger.info(f"Непрочитанных писем от {sender_email} не найдено")
                return []

            ids = message_ids[0].split()
            emails = []

            for email_id in ids:
                email_data = self.get_email_content(int(email_id))
                if email_data:
                    emails.append(email_data)

            self.logger.info(f"Получено {len(emails)} непрочитанных писем")
            return emails

        except Exception as e:
            self.logger.error(f"Ошибка получения непрочитанных писем: {str(e)}")
            return []


# Пример использования
if __name__ == "__main__":
    # Настройка логирования для тестирования
    logging.basicConfig(level=logging.INFO)

    # Создаем клиент (замените на ваши данные)
    client = EmailClient(
        server="imap.yandex.ru",
        port=993,
        login="your_email@company.ru",
        password="your_app_password"
    )

    # Тестируем подключение
    if client.connect():
        if client.select_mailbox():
            # Ищем новые письма от конкретного отправителя
            emails = client.get_new_emails_from_sender("sender@domain.ru")

            for email_data in emails:
                print(f"Тема: {email_data['subject']}")
                print(f"От: {email_data['from']}")
                print(f"Дата: {email_data['date']}")
                print(f"Содержимое: {email_data['body'][:200]}...")
                print("-" * 50)

        client.disconnect()
