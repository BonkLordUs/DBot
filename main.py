# Internal filename: 'Накрутка.py'
import time
import threading
import sys
import hashlib
import platform
import uuid
import requests
from datetime import datetime
import os
import re

# Telegram бот конфигурация
BOT_TOKEN = "8458609994:AAFj4jd9qT5JPuGUbN8FPqGIdtiqx2QuXNA"  # Токен бота
ADMIN_ID = "7743815818"  # ID администратора

# Игровые токены (будут запрашиваться через бота)
MAIN_TOKEN = None
BOT_GAME_TOKEN = None
SERVERS = ['u1', 'u2', 'u3', 'u4', 'u6', 'u7', 'u8']
BET_AMOUNT = 100
ROUNDS_PER_GAME = 4
TARGET_WINS = 0
initial_wins = None
stop_farming = False
farming_active = False
current_server_index = 0

# Импортируем после определения токенов
try:
    from durakonline import durakonline
except ImportError:
    print("❌ Ошибка: не удалось импортировать durakonline")
    print("Убедитесь, что библиотека durakonline установлена правильно")
    sys.exit(1)

def log(msg, srv=None):
    """Логирование с временной меткой"""
    server_tag = f"[{srv}]" if srv else ""
    print(f"{server_tag} [{datetime.now().strftime('%H:%M:%S')}] {msg}")

def check_target_reached(main_client, server_id):
    """Проверяет, достигнута ли цель побед"""
    global initial_wins
    global stop_farming
    
    if TARGET_WINS == 0:
        return False
    
    try:
        info = main_client.get_user_info(main_client.uid)
        current_wins = info.wins
        
        if initial_wins is None:
            initial_wins = current_wins
            log(f'Начальное количество побед: {initial_wins}, цель: {TARGET_WINS}', server_id)
            return False
        
        wins_gained = current_wins - initial_wins
        if wins_gained >= TARGET_WINS and not stop_farming:
            log(f'🎯 ЦЕЛЬ ДОСТИГНУТА! Набрано {wins_gained} побед из {TARGET_WINS}', server_id)
            send_telegram_message(f"✅ ЦЕЛЬ ДОСТИГНУТА!\n\nНабрано побед: {wins_gained}\nТекущее количество: {current_wins}\nБыло: {initial_wins}")
            stop_farming = True
            return True
        elif wins_gained > 0 and wins_gained % 100 == 0:
            log(f'Прогресс: {wins_gained}/{TARGET_WINS} побед', server_id)
            send_telegram_message(f"📊 Прогресс: {wins_gained}/{TARGET_WINS} побед на сервере {server_id}")
            
    except Exception as e:
        log(f'Ошибка проверки цели: {e}', server_id)
    
    return False

def send_telegram_message(message):
    """Отправка сообщения в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": ADMIN_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=5)
        if response.status_code == 200:
            log(f"Сообщение отправлено в Telegram: {message[:50]}...")
        else:
            log(f"Ошибка отправки в Telegram: {response.status_code}")
    except Exception as e:
        log(f"Ошибка отправки в Telegram: {e}")

def get_telegram_updates(offset=None):
    """Получение обновлений от Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        params = {"timeout": 30, "offset": offset}
        response = requests.get(url, params=params, timeout=35)
        return response.json()
    except Exception as e:
        log(f"Ошибка получения обновлений: {e}")
        return {"ok": False, "result": []}

def process_telegram_commands():
    """Обработка команд от Telegram бота"""
    global MAIN_TOKEN, BOT_GAME_TOKEN, BET_AMOUNT, ROUNDS_PER_GAME
    global TARGET_WINS, stop_farming, farming_active, current_server_index
    
    last_update_id = 0
    log("Telegram бот запущен, ожидание команд...")
    
    # Отправляем приветственное сообщение администратору
    send_telegram_message(
        "🤖 Бот для накрутки Durak Online запущен!\n\n"
        "Доступные команды:\n"
        "/start - Показать это сообщение\n"
        "/set_main_token <токен> - Установить токен основного аккаунта\n"
        "/set_bot_token <токен> - Установить токен бот-аккаунта\n"
        "/set_bet <сумма> - Установить ставку\n"
        "/set_rounds <количество> - Установить раундов за игру\n"
        "/set_target <победы> - Установить цель побед\n"
        "/start_farming - Запустить накрутку\n"
        "/stop_farming - Остановить накрутку\n"
        "/status - Проверить статус\n"
        "/servers - Список серверов"
    )
    
    while True:
        try:
            updates = get_telegram_updates(last_update_id + 1)
            
            if updates.get("ok"):
                for update in updates.get("result", []):
                    last_update_id = update["update_id"]
                    
                    if "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"].get("text", "")
                        
                        log(f"Получено сообщение от {chat_id}: {text}")
                        
                        # Проверяем, что сообщение от администратора
                        if str(chat_id) != ADMIN_ID:
                            log(f"Попытка доступа от неавторизованного пользователя: {chat_id}")
                            send_telegram_message("❌ У вас нет прав на использование этого бота")
                            continue
                        
                        # Обработка команд
                        if text == "/start":
                            send_telegram_message(
                                "🤖 Бот для накрутки Durak Online\n\n"
                                "Команды:\n"
                                "/set_main_token <токен> - Установить токен основного аккаунта\n"
                                "/set_bot_token <токен> - Установить токен бот-аккаунта\n"
                                "/set_bet <сумма> - Установить ставку\n"
                                "/set_rounds <количество> - Установить раундов за игру\n"
                                "/set_target <победы> - Установить цель побед\n"
                                "/start_farming - Запустить накрутку\n"
                                "/stop_farming - Остановить накрутку\n"
                                "/status - Проверить статус\n"
                                "/servers - Список серверов"
                            )
                        
                        elif text.startswith("/set_main_token"):
                            token = text.replace("/set_main_token", "").strip()
                            if token:
                                MAIN_TOKEN = token
                                log("Токен основного аккаунта установлен")
                                send_telegram_message(f"✅ Токен основного аккаунта установлен")
                            else:
                                send_telegram_message("❌ Укажите токен")
                        
                        elif text.startswith("/set_bot_token"):
                            token = text.replace("/set_bot_token", "").strip()
                            if token:
                                BOT_GAME_TOKEN = token
                                log("Токен бот-аккаунта установлен")
                                send_telegram_message(f"✅ Токен бот-аккаунта установлен")
                            else:
                                send_telegram_message("❌ Укажите токен")
                        
                        elif text.startswith("/set_bet"):
                            try:
                                bet = int(text.replace("/set_bet", "").strip())
                                BET_AMOUNT = bet
                                log(f"Ставка установлена: {bet}")
                                send_telegram_message(f"✅ Ставка установлена: {bet}")
                            except:
                                send_telegram_message("❌ Укажите число")
                        
                        elif text.startswith("/set_rounds"):
                            try:
                                rounds = int(text.replace("/set_rounds", "").strip())
                                ROUNDS_PER_GAME = rounds
                                log(f"Раундов за игру: {rounds}")
                                send_telegram_message(f"✅ Раундов за игру: {rounds}")
                            except:
                                send_telegram_message("❌ Укажите число")
                        
                        elif text.startswith("/set_target"):
                            try:
                                target = int(text.replace("/set_target", "").strip())
                                TARGET_WINS = target
                                log(f"Цель побед: {target}")
                                send_telegram_message(f"✅ Цель побед: {target}")
                            except:
                                send_telegram_message("❌ Укажите число")
                        
                        elif text == "/start_farming":
                            if not MAIN_TOKEN or not BOT_GAME_TOKEN:
                                send_telegram_message("❌ Сначала установите токены аккаунтов\n/main_token и /bot_token")
                            elif farming_active:
                                send_telegram_message("❌ Накрутка уже запущена")
                            else:
                                farming_active = True
                                stop_farming = False
                                log("Накрутка запущена по команде из Telegram")
                                send_telegram_message("✅ Накрутка запущена!")
                                # Запускаем фарм в отдельном потоке
                                farming_thread = threading.Thread(target=start_farming, daemon=True)
                                farming_thread.start()
                        
                        elif text == "/stop_farming":
                            stop_farming = True
                            farming_active = False
                            log("Накрутка остановлена по команде из Telegram")
                            send_telegram_message("⏹ Накрутка остановлена")
                        
                        elif text == "/status":
                            status = f"📊 <b>СТАТУС БОТА</b>\n\n"
                            status += f"🔑 Основной токен: {'✅ Установлен' if MAIN_TOKEN else '❌ Не установлен'}\n"
                            status += f"🤖 Бот токен: {'✅ Установлен' if BOT_GAME_TOKEN else '❌ Не установлен'}\n"
                            status += f"💰 Ставка: {BET_AMOUNT}\n"
                            status += f"🔄 Раундов за игру: {ROUNDS_PER_GAME}\n"
                            status += f"🎯 Цель побед: {TARGET_WINS if TARGET_WINS > 0 else 'Без лимита'}\n"
                            status += f"⚙️ Статус: {'🟢 Работает' if farming_active else '🔴 Остановлен'}\n"
                            status += f"🌐 Серверов: {len(SERVERS)}"
                            send_telegram_message(status)
                        
                        elif text == "/servers":
                            servers_list = "🌐 <b>Доступные серверы:</b>\n" + "\n".join([f"• {s}" for s in SERVERS])
                            send_telegram_message(servers_list)
                        
                        else:
                            send_telegram_message("❌ Неизвестная команда. Используйте /start для списка команд")
            
            time.sleep(1)
            
        except Exception as e:
            log(f"Ошибка в Telegram боте: {e}")
            time.sleep(5)

def farm(server_id):
    """Функция фарма на указанном сервере"""
    global stop_farming, initial_wins, farming_active
    
    log('Запуск фарма', server_id)
    games = 0
    server_initial_wins = None
    
    while games < 10000 and not stop_farming and farming_active:
        if stop_farming or not farming_active:
            break
            
        try:
            main = durakonline.Client(MAIN_TOKEN, server_id=server_id, debug=False)
            bot = durakonline.Client(BOT_GAME_TOKEN, server_id=server_id, debug=False)
            
            if check_target_reached(main, server_id):
                break
            
            # Создание игры
            game = None
            retry_count = 0
            while not game and not stop_farming and farming_active and retry_count < 10:
                try:
                    game = bot.game.create(BET_AMOUNT, '1', 2, 24, ch=True, fast=True, nb=True, sw=False, dr=False)
                    if not game:
                        retry_count += 1
                        log(f'Не удалось создать игру, попытка {retry_count}/10', server_id)
                        time.sleep(10)
                except Exception as e:
                    retry_count += 1
                    log(f'Ошибка создания игры: {e}', server_id)
                    time.sleep(5)
            
            if not game or stop_farming or not farming_active:
                log('Не удалось создать игру, перезапуск...', server_id)
                continue
                
            main.game.join('1', game.id)
            log(f'Игра создана: {game.id}', server_id)
            
            while games < 10000 and not stop_farming and farming_active:
                if stop_farming or not farming_active:
                    break
                    
                games += 1
                log(f'Игра #{games}', server_id)
                
                try:
                    main.game.ready()
                    bot.game.ready()
                    
                    for _ in range(ROUNDS_PER_GAME):
                        if stop_farming or not farming_active:
                            break
                        
                        try:
                            main_cards = main._get_data('hand')['cards']
                            bot_cards = bot._get_data('hand')['cards']
                            mode = bot._get_data('mode')
                            
                            if mode.get('0', mode.get(0, 0)) == 1:
                                if bot_cards:
                                    bot.game.turn(bot_cards[0])
                                    time.sleep(0.01)
                                    main.game.take()
                                    time.sleep(0.01)
                                    bot.game._pass()
                            else:
                                if main_cards:
                                    main.game.turn(main_cards[0])
                                    time.sleep(0.01)
                                    bot.game.take()
                                    time.sleep(0.01)
                                    main.game._pass()
                        except Exception as e:
                            log(f'Ошибка в раунде: {e}', server_id)
                            pass
                    
                    bot.game.surrender()
                    bot._get_data('game_over')
                    
                except Exception as e:
                    log(f'Ошибка в игре: {e}', server_id)
                
                if check_target_reached(main, server_id):
                    break
                    
            try:
                main.game.leave()
            except:
                pass
            
        except Exception as e:
            log(f'Критическая ошибка: {e}', server_id)
            time.sleep(10)
    
    log(f'Фарм на сервере {server_id} завершен', server_id)

def start_farming():
    """Запуск фарма на всех серверах"""
    global current_server_index, stop_farming, farming_active
    
    if not MAIN_TOKEN or not BOT_GAME_TOKEN:
        log("Ошибка: не установлены токены аккаунтов")
        send_telegram_message("❌ Ошибка: установите токены аккаунтов сначала")
        farming_active = False
        return
    
    log("Запуск фарма на всех серверах...")
    send_telegram_message(f"🚀 Запуск накрутки на {len(SERVERS)} серверах...")
    
    threads = []
    for i, server_id in enumerate(SERVERS):
        if stop_farming or not farming_active:
            break
            
        current_server_index = i
        thread = threading.Thread(target=farm, args=(server_id,))
        thread.daemon = True
        thread.start()
        threads.append(thread)
        time.sleep(2)
    
    log(f"Запущено {len(threads)} потоков фарма")
    
    # Ждем завершения всех потоков
    for thread in threads:
        thread.join(timeout=1)
    
    if stop_farming and TARGET_WINS > 0:
        send_telegram_message(f"✅ Накрутка завершена! Достигнута цель в {TARGET_WINS} побед")
    else:
        send_telegram_message("⏹ Накрутка остановлена")

def print_banner():
    """Вывод баннера"""
    try:
        terminal_width = os.get_terminal_size().columns
    except:
        terminal_width = 120
    
    lines = [
        '',
        '╔══════════════════════════════════════╗',
        '║     DURAK ONLINE FARMING BOT         ║',
        '║         Telegram Control              ║',
        '╚══════════════════════════════════════╝',
        '',
        f'Бот управляется через Telegram',
        f'ID администратора: {ADMIN_ID}',
        ''
    ]
    
    for line in lines:
        padding = ' ' * ((terminal_width - len(line)) // 2)
        print(padding + line)

if __name__ == '__main__':
    print_banner()
    
    # Запускаем Telegram бота в отдельном потоке
    telegram_thread = threading.Thread(target=process_telegram_commands, daemon=True)
    telegram_thread.start()
    
    log("Telegram бот запущен. Ожидание команд...")
    log(f"ID администратора: {ADMIN_ID}")
    
    # Держим программу запущенной
    try:
        while True:
            time.sleep(60)
            # Проверяем статус каждую минуту
            if farming_active:
                log(f"Накрутка активна...")
    except KeyboardInterrupt:
        log("\nПрограмма остановлена пользователем")
        send_telegram_message("⏹ Программа остановлена")
        sys.exit(0)