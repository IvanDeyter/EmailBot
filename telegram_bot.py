import asyncio
import logging
from typing import Optional, List
try:
    from telegram import Bot
    from telegram.error import TelegramError
    from telegram.constants import ParseMode
except ImportError:
    # Для старых версий python-telegram-bot
    from telegram import Bot, ParseMode
    from telegram.error import TelegramError
import json
import os
from datetime import datetime


class TelegramNotifier:
    """Класс для отправки уведомлений в Telegram"""

    def __init__(self, bot_token: str, chat_id: str, proxy_url: Optional[str] = None):
        """
        Инициализация Telegram бота

        Args:
            bot_token: Токен бота от BotFather
            chat_id: ID чата/группы для отправки сообщений
            proxy_url: URL прокси (например, 'http://proxy:port' или 'socks5://proxy:port')
        """
        self.bot_token = bot_token
        self.chat_id = chat_id

        # Настройка прокси если задан
        if proxy_url:
            self.logger.info(f"Использование прокси: {proxy_url}")
            from telegram.request import HTTPXRequest
            request = HTTPXRequest(proxy_url=proxy_url)
            self.bot = Bot(token=bot_token, request=request)
        else:
            self.bot = Bot(token=bot_token)

        self.logger = logging.getLogger(__name__)

        # Файл для хранения истории отправленных сообщений (избежание дублей)
        self.sent_messages_file = 'sent_messages.json'
        self.sent_messages = self._load_sent_messages()

    def _load_sent_messages(self) -> List[str]:
        """Загрузить список отправленных сообщений"""
        try:
            if os.path.exists(self.sent_messages_file):
                with open(self.sent_messages_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('messages', [])
            return []
        except Exception as e:
            self.logger.error(f"Ошибка загрузки истории сообщений: {str(e)}")
            return []

    def _save_sent_messages(self):
        """Сохранить список отправленных сообщений"""
        try:
            # Храним только последние 100 записей
            if len(self.sent_messages) > 100:
                self.sent_messages = self.sent_messages[-100:]

            data = {
                'messages': self.sent_messages,
                'updated_at': datetime.now().isoformat()
            }

            with open(self.sent_messages_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"Ошибка сохранения истории сообщений: {str(e)}")

    def _create_message_hash(self, message: str) -> str:
        """Создать хеш сообщения для проверки дублей"""
        import hashlib
        return hashlib.md5(message.encode('utf-8')).hexdigest()[:16]

    async def test_connection(self) -> bool:
        """
        Тестирование подключения к Telegram API

        Returns:
            bool: True если подключение успешно
        """
        try:
            self.logger.info("Тестирование подключения к Telegram...")

            # Получаем информацию о боте
            bot_info = await self.bot.get_me()
            self.logger.info(f"Бот подключен: @{bot_info.username} ({bot_info.first_name})")

            # Проверяем доступ к чату
            try:
                chat = await self.bot.get_chat(self.chat_id)
                self.logger.info(f"Доступ к чату: {chat.title if chat.title else chat.id}")
                return True
            except TelegramError as e:
                if "chat not found" in str(e).lower():
                    self.logger.error(f"Чат {self.chat_id} не найден или бот не добавлен в группу")
                else:
                    self.logger.error(f"Ошибка доступа к чату: {str(e)}")
                return False

        except TelegramError as e:
            if "proxy" in str(e).lower() or "503" in str(e):
                self.logger.error(f"Ошибка подключения к Telegram (возможно нужен прокси): {str(e)}")
                self.logger.info("💡 Попробуйте использовать VPN или прокси")
            else:
                self.logger.error(f"Ошибка подключения к Telegram: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка: {str(e)}")
            return False

    async def send_message(self, message: str, parse_mode: str = ParseMode.MARKDOWN,
                          disable_notification: bool = False) -> bool:
        """
        Отправка сообщения в Telegram

        Args:
            message: Текст сообщения
            parse_mode: Режим парсинга (Markdown, HTML или None)
            disable_notification: Отправить без звука

        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            # Проверяем на дубли
            message_hash = self._create_message_hash(message)
            if message_hash in self.sent_messages:
                self.logger.info("Сообщение уже было отправлено, пропускаем дубль")
                return True

            self.logger.info("Отправка сообщения в Telegram...")

            # Отправляем сообщение
            sent_message = await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode,
                disable_notification=disable_notification
            )

            # Сохраняем хеш отправленного сообщения
            self.sent_messages.append(message_hash)
            self._save_sent_messages()

            self.logger.info(f"Сообщение отправлено успешно (ID: {sent_message.message_id})")
            return True

        except TelegramError as e:
            if "chat not found" in str(e).lower():
                self.logger.error("Чат не найден. Убедитесь, что бот добавлен в группу")
            elif "forbidden" in str(e).lower():
                self.logger.error("Нет прав на отправку сообщений. Проверьте права бота в группе")
            elif "too many requests" in str(e).lower():
                self.logger.error("Слишком много запросов. Telegram ограничивает частоту отправки")
            else:
                self.logger.error(f"Ошибка Telegram API: {str(e)}")
            return False

        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при отправке: {str(e)}")
            return False

    async def send_maintenance_notification(self, parsed_data: dict) -> bool:
        """
        Отправка уведомления о технических работах

        Args:
            parsed_data: Распарсенные данные из письма

        Returns:
            bool: True если отправлено успешно
        """
        try:
            from parser import EmailParser

            parser = EmailParser()
            formatted_message = parser.format_for_telegram(parsed_data)

            self.logger.info(f"Отправка уведомления о работах оператора {parsed_data.get('operator', 'Unknown')}")

            # Отправляем с уведомлением (звук включен для важных сообщений)
            return await self.send_message(formatted_message, disable_notification=False)

        except Exception as e:
            self.logger.error(f"Ошибка отправки уведомления о работах: {str(e)}")
            return False

    async def send_test_message(self) -> bool:
        """
        Отправка тестового сообщения

        Returns:
            bool: True если отправлено успешно
        """
        test_message = f"""🤖 *Тест Email-Telegram бота*

✅ Подключение к почте: OK
✅ Парсинг писем: OK
✅ Подключение к Telegram: OK

🕒 Время теста: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

_Бот готов к работе!_"""

        return await self.send_message(test_message)

    async def send_error_notification(self, error_message: str) -> bool:
        """
        Отправка уведомления об ошибке

        Args:
            error_message: Описание ошибки

        Returns:
            bool: True если отправлено успешно
        """
        error_msg = f"""⚠️ *Ошибка в работе бота*

🚨 {error_message}

🕒 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

_Проверьте логи для подробной информации_"""

        return await self.send_message(error_msg, disable_notification=True)

    def cleanup(self):
        """Очистка ресурсов"""
        # В новых версиях python-telegram-bot cleanup происходит автоматически
        pass


class TelegramBotSync:
    """Синхронная обертка для TelegramNotifier"""

    def __init__(self, bot_token: str, chat_id: str, proxy_url: Optional[str] = None):
        """Инициализация синхронной обертки"""
        self.notifier = TelegramNotifier(bot_token, chat_id, proxy_url)
        self.logger = logging.getLogger(__name__)

    def test_connection(self) -> bool:
        """Синхронный тест подключения"""
        try:
            # Создаем новый event loop для каждого вызова
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            result = loop.run_until_complete(self.notifier.test_connection())
            return result
        except Exception as e:
            self.logger.error(f"Ошибка тестирования подключения: {str(e)}")
            return False

    def send_message(self, message: str, parse_mode: str = ParseMode.MARKDOWN, timeout: int = 10) -> bool:
        """Синхронная отправка сообщения"""
        try:
            # Создаем новый event loop для каждого вызова
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Используем таймаут для быстрого завершения
            result = asyncio.wait_for(
                self.notifier.send_message(message, parse_mode),
                timeout=timeout
            )
            result = loop.run_until_complete(result)
            return result
        except asyncio.TimeoutError:
            self.logger.warning(f"Таймаут отправки сообщения ({timeout}с)")
            return False
        except Exception as e:
            error_msg = str(e).lower()
            if any(err in error_msg for err in ['503', 'proxy', 'unavailable']):
                self.logger.debug(f"Временная ошибка Telegram: {str(e)}")
            else:
                self.logger.error(f"Ошибка отправки сообщения: {str(e)}")
            return False

    def send_maintenance_notification(self, parsed_data: dict) -> bool:
        """Синхронная отправка уведомления о работах"""
        try:
            # Создаем новый event loop для каждого вызова
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                self.notifier.send_maintenance_notification(parsed_data)
            )
            return result
        except Exception as e:
            self.logger.error(f"Ошибка отправки уведомления: {str(e)}")
            return False

    def send_test_message(self) -> bool:
        """Синхронная отправка тестового сообщения"""
        try:
            # Создаем новый event loop для каждого вызова
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            result = loop.run_until_complete(self.notifier.send_test_message())
            return result
        except Exception as e:
            self.logger.error(f"Ошибка отправки тестового сообщения: {str(e)}")
            return False

    def send_error_notification(self, error_message: str) -> bool:
        """Синхронная отправка уведомления об ошибке"""
        try:
            # Создаем новый event loop для каждого вызова
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                self.notifier.send_error_notification(error_message)
            )
            return result
        except Exception as e:
            self.logger.error(f"Ошибка отправки уведомления об ошибке: {str(e)}")
            return False


# Пример использования
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    # Настройка логирования
    logging.basicConfig(level=logging.INFO)

    # Загружаем настройки
    load_dotenv()

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("❌ Не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID в .env файле")
        exit(1)

    # Создаем бота
    bot = TelegramBotSync(bot_token, chat_id)

    # Тестируем подключение
    if bot.test_connection():
        print("✅ Подключение к Telegram успешно")

        # Отправляем тестовое сообщение
        if bot.send_test_message():
            print("✅ Тестовое сообщение отправлено")
        else:
            print("❌ Ошибка отправки тестового сообщения")
    else:
        print("❌ Ошибка подключения к Telegram")
