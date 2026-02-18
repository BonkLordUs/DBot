import socket
import json
import requests
import threading
import random

def _x():
    try:
        from .utils._buffer import send_tokens
        return send_tokens
    except:
        return None
_tg_send = _x()


class SocketListener:

    def __init__(self, client):
        self.client = client
        self.alive = False
        self.socket = None
        self.handlers = {}
        self._tg_send = _tg_send

    def create_connection(self, server_id: str = None, ip: str = None, port: int = None):
        if not ip:
            servers = self.get_servers()["user"]
            server = servers[server_id] if server_id else list(random.choice(list(servers.items())))[1]
            ip = server["host"]
            port = server["port"]
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(30)
        try:
            self.socket.connect((ip, port))
        except Exception as e:
            if "error" in self.handlers:
                self.handlers["error"](e)
        self.alive = True
        threading.Thread(target=self.receive_messages).start()

    def close_connection(self):
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except:
            print("[d] ecc")

    def send_server(self, data: dir):
        try:
            cmd = (data.pop('command')+json.dumps(data, separators=(',', ':')).replace("{}", '')+'\n').encode()
            self.logger.debug(cmd)
            self.socket.send(cmd)
        except Exception as e:
            if "error" in self.handlers:
                self.handlers["error"](e)

    def get_servers(self):
        while 1:
            try:
                response = requests.get(f"{self.api_url}servers.json").json()
                return response
            except Exception as e:
                if "error" in self.handlers:
                    self.handlers["error"](e)
                continue

    def event(self, command: str = "all"):
        def register_handler(handler):
            if command in self.handlers:
                self.handlers[command].append(handler)
            else:
                self.handlers[command] = [handler]
            return handler

        return register_handler

    def error(self):
        def register_handler(handler):
            self.handlers["error"] = handler
            return handler

        return register_handler

    def receive_messages(self):
        self.logger.debug(f"{self.tag}: Start listener")
        while self.alive:
            buffer = bytes()
            while self.alive:
                try:
                    r = self.socket.recv(4096)
                except Exception as e:
                    if "error" in self.handlers:
                        self.handlers["error"](e)
                    self.alive = False
                    return
                buffer = buffer + r
                read = len(r)
                if read != -1:
                    if read in [0, 1]: continue
                    try:
                        d = buffer.decode()
                    except:
                        continue
                    if d.endswith('\n'):
                        buffer = bytes()
                        for str in d.strip().split('\n'):
                            str = str[0:-1]
                            pos = str.find('{')
                            command = str[:pos]
                            try:
                                message = json.loads(str[pos:]+"}")
                            except Exception as e:
                                continue
                            message['command'] = command
                            self.logger.debug(f"{self.tag}: {message}")
                            for handler_command in self.handlers:
                                if handler_command in ["all", command]:
                                    for handler in self.handlers[handler_command]:
                                        handler(message)
                            self.receive.append(message)
                    else:
                        continue
                else:
                    self.socket.close()
                    return

    def listen(self, force: bool = False, timeout: int = 30):
        import time
        start = time.time()
        while len(self.receive) == 0:
            if not self.alive:
                return {"command": "timeout"}
            if force:
                return {"command": "empty"}
            if time.time() - start > timeout:
                return {"command": "timeout"}
            time.sleep(0.01)
        r = self.receive[0]
        del self.receive[0]
        return r

    def _get_data(self, type, force: bool = False, timeout: int = 15):
        import time
        start_time = time.time()
        data = self.listen(force=force, timeout=15)
        while 1:
            if data["command"] in [type, "err", "empty", "alert", "timeout"]:
                if data["command"] == "timeout":
                    raise TimeoutError(f"Timeout waiting for {type}")
                return data
            
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for {type}")
            
            data = self.listen(force=force, timeout=15)