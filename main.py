#!/usr/bin/env python3
"""
Главный файл Email-Telegram бота
Автоматически проверяет почту и отправляет уведомления в Telegram
"""

import time
import logging
import signal
import sys
import os
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List

# Импортируем наши модули
try:
    from email_client import EmailClient
    from parser import EmailParser
    from telegram_bot import TelegramBotSync
except ImportError as e:
    print(f"❌ Ошибка импорта модулей: {e}")
    print("📝 Убедитесь, что все файлы находятся в корне проекта")
    sys.exit(1)


class EmailTelegramBot:
    """Основной класс бота для мониторинга почты и отправки уведомлений"""

    def __init__(self):
        """Инициализация бота"""

        # Загружаем настройки
        load_dotenv()

        # Настройка логирования
        self._setup_logging()

        # Загружаем конфигурацию
        self.config = self._load_config()

        # Инициализируем компоненты
        self.email_client = None
        self.parser = EmailParser()
        self.telegram_bot = None

        # Флаг для остановки бота
        self.running = False

        # Счетчики статистики
        self.stats = {
            'emails_processed': 0,
            'notifications_sent': 0,
            'errors': 0,
            'started_at': datetime.now()
        }

        self.logger.info("Email-Telegram бот инициализирован")

    def _setup_logging(self):
        """Настройка логирования"""

        # Создаем папку для логов
        os.makedirs('logs', exist_ok=True)

        # Настраиваем форматирование
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        # Настраиваем уровень логирования
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                # Вывод в консоль
                logging.StreamHandler(sys.stdout),
                # Запись в файл
                logging.FileHandler(
                    f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log',
                    encoding='utf-8'
                )
            ]
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Логирование настроено (уровень: {log_level})")

    def _load_config(self) -> Dict:
        """Загрузка конфигурации из переменных окружения"""

        config = {
            # Email настройки
            'email_server': os.getenv('EMAIL_SERVER', 'imap.yandex.ru'),
            'email_port': int(os.getenv('EMAIL_PORT', 993)),
            'email_login': os.getenv('EMAIL_LOGIN'),
            'email_password': os.getenv('EMAIL_PASSWORD'),
            'email_sender': os.getenv('EMAIL_SENDER'),

            # Telegram настройки
            'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN'),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
            'telegram_proxy': os.getenv('TELEGRAM_PROXY_URL'),

            # Настройки бота
            'check_interval': int(os.getenv('CHECK_INTERVAL', 1800)),  # 30 минут
            'max_errors': int(os.getenv('MAX_ERRORS', 5)),
            'error_cooldown': int(os.getenv('ERROR_COOLDOWN', 300)),  # 5 минут
        }

        # Проверяем обязательные настройки
        required_settings = [
            'email_login', 'email_password', 'email_sender',
            'telegram_token', 'telegram_chat_id'
        ]

        missing_settings = [key for key in required_settings if not config[key]]

        if missing_settings:
            self.logger.error(f"Не заданы обязательные настройки: {missing_settings}")
            self.logger.error("Проверьте .env файл")
            sys.exit(1)

        self.logger.info("Конфигурация загружена успешно")
        return config

    def _initialize_components(self) -> bool:
        """Инициализация всех компонентов бота"""

        try:
            # Инициализируем email клиент
            self.logger.info("Инициализация email клиента...")
            self.email_client = EmailClient(
                server=self.config['email_server'],
                port=self.config['email_port'],
                login=self.config['email_login'],
                password=self.config['email_password']
            )

            # Инициализируем Telegram бота
            self.logger.info("Инициализация Telegram бота...")
            self.telegram_bot = TelegramBotSync(
                bot_token=self.config['telegram_token'],
                chat_id=self.config['telegram_chat_id'],
                proxy_url=self.config['telegram_proxy']
            )

            return True

        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {str(e)}")
            return False

    def _test_connections(self) -> bool:
        """Тестирование всех подключений"""

        self.logger.info("Тестирование подключений...")

        # Тест email подключения
        try:
            if not self.email_client.connect():
                self.logger.error("Ошибка подключения к почте")
                return False

            if not self.email_client.select_mailbox():
                self.logger.error("Ошибка выбора почтового ящика")
                return False

            self.logger.info("✅ Подключение к почте успешно")

        except Exception as e:
            self.logger.error(f"Ошибка тестирования почты: {str(e)}")
            return False

        # Тест Telegram подключения
        try:
            if not self.telegram_bot.test_connection():
                self.logger.error("Ошибка подключения к Telegram")
                return False

            self.logger.info("✅ Подключение к Telegram успешно")

        except Exception as e:
            self.logger.error(f"Ошибка тестирования Telegram: {str(e)}")
            return False

        return True

    def _process_new_emails(self) -> int:
        """Обработка новых писем"""

        processed_count = 0

        try:
            # Получаем новые письма с повторными попытками
            new_emails = self.email_client.get_new_emails_from_sender(
                self.config['email_sender'],
                update_state=True,
                retry_count=3
            )

            if not new_emails:
                self.logger.debug("Новых писем не найдено")
                return 0

            self.logger.info(f"Найдено {len(new_emails)} новых писем")

            for email_data in new_emails:
                try:
                    self.logger.info(f"Обработка письма: {email_data['subject'][:50]}...")

                    # Проверяем, является ли письмо уведомлением о работах
                    if not self.parser.is_maintenance_email(email_data):
                        self.logger.info("Письмо не является уведомлением о работах, пропускаем")
                        continue

                    # Парсим данные
                    parsed_data = self.parser.parse_email(email_data)

                    if not parsed_data:
                        self.logger.warning("Не удалось распарсить письмо")
                        continue

                    # Отправляем уведомление в Telegram
                    if self.telegram_bot.send_maintenance_notification(parsed_data):
                        self.logger.info("✅ Уведомление отправлено в Telegram")
                        self.stats['notifications_sent'] += 1
                        processed_count += 1
                    else:
                        self.logger.error("❌ Ошибка отправки в Telegram")
                        self.stats['errors'] += 1

                    self.stats['emails_processed'] += 1

                except Exception as e:
                    self.logger.error(f"Ошибка обработки письма: {str(e)}")
                    self.stats['errors'] += 1

            return processed_count

        except Exception as e:
            error_msg = str(e).lower()

            # Для ошибок соединения логируем как warning, а не error
            if any(err in error_msg for err in ['broken pipe', 'connection', 'socket', 'timeout']):
                self.logger.warning(f"Временная ошибка соединения: {str(e)}")
                self.logger.info("Соединение будет восстановлено при следующей попытке")
            else:
                self.logger.error(f"Ошибка обработки новых писем: {str(e)}")
                self.stats['errors'] += 1

            return 0

    def _send_startup_notification(self):
        """Отправка уведомления о запуске бота"""

        startup_message = f"""🚀 *Email-Telegram бот запущен*

📧 Мониторинг: {self.config['email_sender']}
⏰ Интервал проверки: {self.config['check_interval']} сек
🕒 Время запуска: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

_Бот готов к работе!_"""

        try:
            self.telegram_bot.send_message(startup_message)
            self.logger.info("Уведомление о запуске отправлено")
        except Exception as e:
            self.logger.error(f"Ошибка отправки уведомления о запуске: {str(e)}")

    def _send_stats_notification(self):
        """Отправка статистики работы"""

        uptime = datetime.now() - self.stats['started_at']
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)

        stats_message = f"""📊 *Статистика работы бота*

⏰ Время работы: {hours}ч {minutes}м
📧 Обработано писем: {self.stats['emails_processed']}
📤 Отправлено уведомлений: {self.stats['notifications_sent']}
❌ Ошибок: {self.stats['errors']}

🕒 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"""

        try:
            self.telegram_bot.send_message(stats_message, disable_notification=True)
            self.logger.info("Статистика отправлена")
        except Exception as e:
            self.logger.error(f"Ошибка отправки статистики: {str(e)}")

    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для корректного завершения"""

        def signal_handler(signum, frame):
            self.logger.info(f"Получен сигнал {signum}, завершение работы...")

            # Если это второй Ctrl+C, принудительно завершаем
            if hasattr(self, '_shutdown_initiated'):
                self.logger.warning("Принудительное завершение...")
                import os
                os._exit(0)

            self._shutdown_initiated = True
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def start(self):
        """Запуск бота"""

        self.logger.info("🚀 Запуск Email-Telegram бота...")

        # Инициализируем компоненты
        if not self._initialize_components():
            self.logger.error("Ошибка инициализации, завершение работы")
            return

        # Тестируем подключения
        if not self._test_connections():
            self.logger.error("Ошибка тестирования подключений, завершение работы")
            return

        # Настраиваем обработчики сигналов
        self._setup_signal_handlers()

        # Отправляем уведомление о запуске
        self._send_startup_notification()

        # Запускаем основной цикл
        self.running = True
        error_count = 0
        last_stats_time = datetime.now()

        self.logger.info(f"Бот запущен, интервал проверки: {self.config['check_interval']} секунд")

        while self.running:
            try:
                cycle_start = datetime.now()

                # Обрабатываем новые письма
                processed = self._process_new_emails()

                if processed > 0:
                    self.logger.info(f"Цикл завершен, обработано {processed} писем")
                    error_count = 0  # Сбрасываем счетчик ошибок при успехе
                else:
                    # Если писем не было, это нормально, не считаем как ошибку
                    error_count = 0

                # Отправляем статистику каждые 24 часа
                if (datetime.now() - last_stats_time).total_seconds() > 86400:  # 24 часа
                    self._send_stats_notification()
                    last_stats_time = datetime.now()

                # Ждем до следующей проверки
                if self.running:
                    time.sleep(self.config['check_interval'])

            except Exception as e:
                error_msg = str(e).lower()

                # Разделяем ошибки на критические и временные
                is_connection_error = any(err in error_msg for err in [
                    'broken pipe', 'connection', 'socket', 'timeout', 'network'
                ])

                if is_connection_error:
                    # Для ошибок соединения не увеличиваем критический счетчик
                    self.logger.warning(f"Временная ошибка соединения в основном цикле: {str(e)}")
                    self.logger.info("Попытка продолжить работу...")
                    time.sleep(60)  # Пауза 1 минута при ошибках соединения
                else:
                    # Для других ошибок увеличиваем счетчик
                    error_count += 1
                    self.logger.error(f"Критическая ошибка в основном цикле: {str(e)}")
                    self.stats['errors'] += 1

                    # Если слишком много критических ошибок подряд
                    if error_count >= self.config['max_errors']:
                        self.logger.error(f"Превышено максимальное количество критических ошибок ({error_count})")

                        try:
                            self.telegram_bot.send_error_notification(
                                f"Критические ошибки в работе бота. Ошибок подряд: {error_count}"
                            )
                        except:
                            pass

                        self.logger.info(f"Пауза на {self.config['error_cooldown']} секунд")
                        time.sleep(self.config['error_cooldown'])
                        error_count = 0
                    else:
                        time.sleep(30)  # Короткая пауза при единичных ошибках

        self.logger.info("Бот остановлен")

    def stop(self):
        """Остановка бота"""

        self.logger.info("Остановка бота...")
        self.running = False

        # Отключаемся от почты
        if self.email_client:
            self.email_client.disconnect()

        # Отправляем уведомление об остановке
        if self.telegram_bot:
            try:
                stop_message = f"""🛑 *Email-Telegram бот остановлен*

📊 Статистика сессии:
• Обработано писем: {self.stats['emails_processed']}
• Отправлено уведомлений: {self.stats['notifications_sent']}
• Ошибок: {self.stats['errors']}

🕒 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"""

                self.telegram_bot.send_message(stop_message)
            except Exception as e:
                self.logger.error(f"Ошибка отправки уведомления об остановке: {str(e)}")


def main():
    """Главная функция"""

    print("🤖 Email-Telegram бот")
    print("=" * 50)

    try:
        # Создаем и запускаем бота
        bot = EmailTelegramBot()
        bot.start()

    except KeyboardInterrupt:
        print("\n⚠️ Получен сигнал прерывания")
        print("ℹ️ Если бот не останавливается, нажмите Ctrl+C еще раз для принудительного завершения")
    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        sys.exit(1)
    finally:
        print("👋 Завершение работы")


if __name__ == "__main__":
    main()
