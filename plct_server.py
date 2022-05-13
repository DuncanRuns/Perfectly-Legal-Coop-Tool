import os, socket, sys, threading, json, traceback

BUFFER_SIZE = 8192


class PLCTClientInstance:
    def __init__(self, sock, addr, server) -> None:
        self._socket: socket.socket = sock
        self._server: PLCTServer = server
        self._addr = addr
        self._receive_bytes = b''
        self._send_lock = threading.Lock()
        self._start_listen_thread()

    def _start_listen_thread(self):
        threading.Thread(target=self._listen_thread).start()

    def _listen_thread(self):
        while self._server is not None:
            try:
                newrecv = self._socket.recv(BUFFER_SIZE)
                self._receive_bytes += newrecv
                end_index = -1
                for i in range(len(self._receive_bytes)):
                    if chr(self._receive_bytes[i]) == "}":
                        end_index = i + 1
                        break

                while end_index != -1:
                    pack: dict = json.loads(
                        self._receive_bytes[:end_index].decode())
                    self._receive_bytes = self._receive_bytes[end_index:]
                    self._on_pack(pack)
                    end_index = -1
                    for i in range(len(self._receive_bytes)):
                        if chr(self._receive_bytes[i]) == "}":
                            end_index = i + 1
                            break
            except:
                self.close()

    def _download_file(self, size: int, name: str, dir: str) -> None:
        print("Downloading file " + name + "...", end="")
        sys.stdout.flush()
        dir_path = os.path.join("upload", dir).replace("\\", "/")
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        file_path = os.path.join(dir_path, name).replace("\\", "/")
        bytes_left = size
        with open(file_path, "wb") as f:
            if len(self._receive_bytes) > 0:
                newrecv = self._receive_bytes
                self._receive_bytes = b''
                if bytes_left < BUFFER_SIZE:
                    self._receive_bytes = newrecv[bytes_left:]
                    newrecv = newrecv[:bytes_left]
                bytes_left -= len(newrecv)
                f.write(newrecv)
            while bytes_left > 0:
                newrecv = self._socket.recv(min(bytes_left, BUFFER_SIZE))
                if bytes_left < BUFFER_SIZE:
                    self._receive_bytes = newrecv[bytes_left:]
                    newrecv = newrecv[:bytes_left]
                bytes_left -= len(newrecv)
                f.write(newrecv)
            f.close()
            print("!")

    def _fake_download_file(self, size: int) -> None:
        print("Fake Downloading file...")
        bytes_left = size
        if len(self._receive_bytes) > 0:
            newrecv = self._receive_bytes
            self._receive_bytes = b''
            if bytes_left < BUFFER_SIZE:
                self._receive_bytes = newrecv[bytes_left:]
                newrecv = newrecv[:bytes_left]
            bytes_left -= len(newrecv)
        while bytes_left > 0:
            newrecv = self._socket.recv(min(bytes_left, BUFFER_SIZE))
            if bytes_left < BUFFER_SIZE:
                self._receive_bytes = newrecv[bytes_left:]
                newrecv = newrecv[:bytes_left]
            bytes_left -= len(newrecv)
        print("!")

    def _on_pack(self, pack: dict) -> None:
        try:
            pack_type = pack["type"]

            if pack_type == "end":
                self.close()

            elif pack_type == "copy":
                password = pack["password"]
                message = pack["copymsg"]
                self._server.set_clipboard(message, password)

            elif pack_type == "upload":
                file_name = pack["name"]
                dir = pack.get("dir", "")
                size = pack["size"]
                password = pack["password"]
                if self._server.is_upload_pass(password):
                    self._download_file(size, file_name, dir)
                else:
                    self._fake_download_file(size)

            elif pack_type == "uploaddone":
                password = pack["password"]
                if self._server.is_upload_pass(password):
                    print("Created done file.")
                    open("upload/done", "w+").close()
                    self._server.clear_clipboard()
        except:
            traceback.print_exc()
            raise

    def close(self) -> None:
        try:
            self.send(json.dumps({"type": "end"}).encode())
            self._socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            self._server.remove_client(self)
            self._server = None
            self._socket.close()
        except:
            pass

    def send(self, b: bytes) -> None:
        with self._send_lock:
            self._socket.sendall(b)


class PLCTServer:
    def __init__(self, settings: dict) -> None:
        self._address: str = settings.get("address", "127.0.0.1")
        self._port: int = settings.get("port", 25563)
        self._clipboard_password: str = settings.get(
            "clipboardPassword", "admin")
        self._upload_password: str = settings.get("uploadPassword", "admin")
        self._socket: socket.socket = None
        self._clients: list[PLCTClientInstance] = []
        self._clipboard = ""

    def remove_client(self, client) -> None:
        if client in self._clients:
            self._clients.remove(client)
            print("Disconnected: " + str(client._addr))

    def set_clipboard(self, message, password) -> None:
        if password == self._clipboard_password:
            self._clipboard = message
            print("Clipboard updated: " + message)
            self._send_to_all(self._get_clipboard_pack())

    def clear_clipboard(self) -> None:
        self.set_clipboard("", self._clipboard_password)

    def _get_clipboard_pack(self) -> bytes:
        return json.dumps({
            "type": "copy",
            "copymsg": self._clipboard
        }).encode()

    def _send_to_all(self, b: bytes) -> None:
        for c in self._clients:
            c.send(b)

    def _accept_thread(self) -> None:
        while self._socket is not None:
            try:
                client_sock, addr = self._socket.accept()
                client = PLCTClientInstance(client_sock, addr, self)
                self._clients.append(client)
                print("Connected: " + str(addr))
                client_sock.send(self._get_clipboard_pack())
            except:
                pass

    def is_upload_pass(self, password) -> bool:
        return password == self._upload_password

    def start(self) -> None:
        if self._socket is None:
            self._socket = socket.socket()
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self._address, self._port))
            self._socket.listen()
            threading.Thread(target=self._accept_thread).start()

    def stop(self) -> None:
        for c in self._clients:
            c.close()
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        self._socket.close()
        self._socket = None
    close = end = kill = stop


def main():
    if os.path.isfile("plct_server_settings.json"):
        with open("plct_server_settings.json", "r") as settings_file:
            settings = json.load(settings_file)
            settings_file.close()
    else:
        settings = {}
    s = PLCTServer(settings)
    s.start()

    while input("Type \"end\", \"stop\", \"close\", or \"kill\" to end.\n") not in ["end", "stop", "kill", "close"]:
        pass

    print("Ending...")
    s.stop()


if __name__ == "__main__":
    main()
