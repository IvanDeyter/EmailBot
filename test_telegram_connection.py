#!/usr/bin/env python3
"""
Диагностика подключения к Telegram API
"""

import sys
import os
import requests
import socket
from dotenv import load_dotenv

def test_internet_connection():
    """Проверка интернет соединения"""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        print("✅ Интернет соединение работает")
        return True
    except OSError:
        print("❌ Нет интернет соединения")
        return False

def test_telegram_api_direct():
    """Прямая проверка доступности Telegram API"""
    try:
        response = requests.get("https://api.telegram.org", timeout=10)
        if response.status_code == 200:
            print("✅ Telegram API доступен напрямую")
            return True
        else:
            print(f"⚠️ Telegram API отвечает с кодом: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Telegram API недоступен: {str(e)}")
        return False

def test_bot_token():
    """Проверка токена бота"""
    load_dotenv()
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN не задан в .env")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print(f"✅ Токен бота валиден: @{bot_info.get('username')} ({bot_info.get('first_name')})")
                return True
            else:
                print(f"❌ Ошибка API: {data.get('description')}")
                return False
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {str(e)}")
        return False

def suggest_solutions():
    """Предложение решений"""
    print("\n🔧 Возможные решения:")
    print("1. 🌐 Используйте VPN (рекомендуется)")
    print("2. 🔄 Настройте прокси")
    print("3. 📱 Попробуйте мобильный интернет")
    print("4. ⏰ Попробуйте позже (возможны временные проблемы)")
    
    print("\n💡 Для использования VPN:")
    print("- Включите любой VPN сервис")
    print("- Выберите сервер в США/Европе")
    print("- Перезапустите тест")
    
    print("\n🔧 Для настройки прокси в .env добавьте:")
    print("TELEGRAM_PROXY_URL=http://proxy.example.com:8080")
    print("# или")
    print("TELEGRAM_PROXY_URL=socks5://proxy.example.com:1080")

def main():
    print("🔍 Диагностика подключения к Telegram API")
    print("=" * 50)
    
    # Проверяем интернет
    if not test_internet_connection():
        print("\n💡 Проверьте интернет соединение")
        return
    
    # Проверяем доступность Telegram API
    api_available = test_telegram_api_direct()
    
    # Проверяем токен бота
    token_valid = test_bot_token()
    
    print("\n" + "=" * 50)
    
    if api_available and token_valid:
        print("🎉 Все проверки пройдены!")
        print("➡️ Попробуйте запустить test_telegram.py снова")
    else:
        if not api_available:
            print("⚠️ Проблемы с доступом к Telegram API")
            suggest_solutions()
        
        if not token_valid:
            print("⚠️ Проблемы с токеном бота")
            print("💡 Проверьте TELEGRAM_BOT_TOKEN в .env файле")

if __name__ == "__main__":
    main()