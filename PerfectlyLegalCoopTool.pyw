try:
    import clipboard, os, json, socket, threading, traceback, time, re, ttkthemes, shutil
    import tkinter as tk
    from tkinter import ttk
    import tkinter.filedialog as tkFileDialog
    import tkinter.messagebox as tkMessageBox
    from sys import maxsize
    from typing import Callable, List, Union
except:
    dependencies = "pypiwin32, pyperclip, clipboard, ttkthemes".split(
        ", ")
    import os, sys, traceback
    import tkinter.messagebox as tkMessageBox
    import tkinter as tk
    error = traceback.format_exc()
    print(error)
    main = tk.Tk()
    tk.Label(main, text="Installing dependencies...").grid(
        row=0, column=0, padx=5, pady=5)
    main.update()
    for dependency in dependencies:
        command = f"{sys.executable} -m pip install {dependency}"
        print(command)
        os.system(command)
    if os.path.isfile("plct_settings.json"):
        tkMessageBox.showinfo(
            "PLCT: Setup", "It appears dependency installation was attempted more than once. Import Error:\n" + error)
    else:
        f = open("plct_settings.json", "w+")
        f.write("{}")
        f.close()
        tkMessageBox.showinfo(
            "PLCT: Setup", "Dependencies were installed, please run " + os.path.split(__file__)[-1] + " again.")
    main.withdraw()


VERSION = "1.1.2"

UPLOADS_ENTIRE_WORLD = True
BUFFER_SIZE = 8192


def resource_path(relative_path):
    try:
        from sys import _MEIPASS
        base_path = _MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


DISCONNECTED_STR = "❌ Disconnected"
CONNECTING_STR = "➖ Connecting..."
CONNECTED_STR = "✔ Connected"

is_pos_command = re.compile(
    r"\/execute in minecraft:overworld run tp @s -?\d+\.\d\d -?\d+\.\d\d -?\d+\.\d\d -?\d+\.\d\d -?\d+\.\d\d").match


def ask_for_directory(og_path: str = None):
    return tkFileDialog.askdirectory(initialdir=og_path)


def ensure_instances_path(selected_path: str) -> Union[None, str]:
    if(is_instances_dir(selected_path)):
        return selected_path.replace("\\", "/")

    sub_path = os.path.join(selected_path, "instances")
    if(is_instances_dir(sub_path)):
        return sub_path.replace("\\", "/")

    parent_path = os.path.abspath(os.path.join(selected_path, os.pardir))
    if(is_instances_dir(parent_path)):
        return parent_path.replace("\\", "/")

    double_parent_path = os.path.abspath(os.path.join(parent_path, os.pardir))
    if(is_instances_dir(double_parent_path)):
        return double_parent_path.replace("\\", "/")

    triple_parent_path = os.path.abspath(
        os.path.join(double_parent_path, os.pardir))
    if(is_instances_dir(triple_parent_path)):
        return triple_parent_path.replace("\\", "/")

    return None


def is_instances_dir(path: str):
    return count_instances(path) > 0


def count_instances(instances_path: str) -> int:
    return len(get_all_instance_paths(instances_path))


def get_all_instance_paths(instances_path: str) -> List[str]:
    try:
        instance_paths = []
        for instance_name in os.listdir(instances_path):
            instance_path = os.path.join(instances_path, instance_name)
            if os.path.exists(os.path.join(instance_path, "instance.cfg")):
                instance_paths.append(instance_path.replace("\\", "/"))
        return instance_paths
    except:
        return []


def get_all_worlds_from_instance(instance_path: str) -> List[str]:
    worlds_path = os.path.join(instance_path, ".minecraft", "saves")
    if os.path.isdir(worlds_path):
        return [os.path.join(worlds_path, i) for i in os.listdir(worlds_path) if os.path.isfile(os.path.join(worlds_path, i, "level.dat"))]
    return []


def get_all_worlds_from_instances(instances_path: str) -> List[str]:
    worlds = []
    for instance in get_all_instance_paths(instances_path):
        worlds.extend(get_all_worlds_from_instance(instance))
    return worlds


def get_latest_world_from_instances(instances_path: str) -> str:
    try:
        return max(get_all_worlds_from_instances(instances_path), key=lambda x: os.path.getmtime(os.path.join(x, "level.dat")))
    except:
        return None


class PLCTClient:
    def __init__(self, app) -> None:
        self._app: PerfectlyLegalCoopTool = app
        self._send_lock = threading.Lock()
        self._socket: socket.socket = None
        self._connecting = False
        self._port = None
        self._address = None

    def _listen_thread(self) -> None:
        while self._socket is not None:
            try:
                newrecv = self._socket.recv(BUFFER_SIZE)
                self._receive_bytes += newrecv
                end_index = -1
                for i in range(len(self._receive_bytes)):
                    if chr(self._receive_bytes[i]) == "}":
                        end_index = i + 1
                        break

                if end_index != -1:
                    pack: dict = json.loads(
                        self._receive_bytes[:end_index].decode())
                    self._receive_bytes = self._receive_bytes[end_index:]
                    self._on_pack(pack)
            except:
                self.disconnect()

    def _on_pack(self, pack: str) -> None:
        try:
            pack_type = pack["type"]
            if pack_type == "copy":
                self._app.set_clipboard(pack["copymsg"])
            elif pack_type == "end":
                self.disconnect()
            elif pack_type == "pong":
                self._app._got_pong()
        except:
            print("Pack Error:")
            traceback.print_exc()

    def connect(self, address: str = None, port: int = None, return_callback: Callable = None) -> bool:
        self._connecting = True
        if address:
            self._address = address
        if port:
            self._port = port
        assert self._address is not None and self._port is not None
        self.disconnect()
        time.sleep(0.05)  # Magic number :(
        print("Attempting new connection...")
        self._send_lock = threading.Lock()
        success = False
        try:
            s = socket.socket()
            s.connect((self._address, self._port))
            self._socket = s
            print("Success!")
            success = True
        except:
            print("Failed.")
            self.disconnect()
        self._receive_bytes = b''
        threading.Thread(target=self._listen_thread).start()
        self._connecting = False
        if return_callback is not None:
            return_callback(success)
        return success

    def disconnect(self) -> None:
        try:
            if self._socket is not None:
                self.send_with_lock(json.dumps({"type": "end"}).encode())
                self._socket.close()
        except:
            pass
        self._socket = None

    def send_with_lock(self, b: bytes) -> None:
        with self._send_lock:
            self.send(b)

    def send(self, b: bytes) -> None:
        if self._socket is not None:
            self._socket.sendall(b)

    def get_send_lock(self) -> threading.Lock:
        return self._send_lock

    def get_status(self) -> str:
        if self._socket is not None:
            return "connected"
        elif self._connecting:
            return "connecting"
        else:
            return "disconnected"

    def get_status_display(self) -> str:
        if self._socket is not None:
            return CONNECTED_STR
        elif self._connecting:
            return CONNECTING_STR
        else:
            return DISCONNECTED_STR


class RetractableFrame(ttk.LabelFrame):
    def __init__(self, master, text) -> None:
        ttk.LabelFrame.__init__(self, master=master, text=text)
        self._text = text
        self.inner_frame = ttk.Frame(self)
        self._is_out = True
        self.inner_frame.grid(row=0, column=0)
        self._filler_widget = ttk.Label(
            self, text="Click to expand", foreground="#aaaaaa")
        self.bind("<Button 1>", self._on_click)
        self._filler_widget.bind("<Button 1>", self._on_click)

    def _on_click(self, *args) -> None:
        if self._is_out:
            self.retract()
        else:
            self.extend()

    def extend(self) -> None:
        self._is_out = True
        self._filler_widget.grid_remove()
        self.inner_frame.grid(row=0, column=0)

    def retract(self) -> None:
        self._is_out = False
        self.inner_frame.grid_remove()
        self._filler_widget.grid(row=0, column=0, padx=5, pady=5)


class IntEntry(ttk.Entry):
    def __init__(self, parent, max=maxsize, on_key_callback: Callable = None):
        self.max = max
        self.parent = parent
        self.on_key_callback = on_key_callback
        vcmd = (self.parent.register(self.validateInt),
                '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        ttk.Entry.__init__(self, parent, validate='key', validatecommand=vcmd)

    def get_int(self) -> int:
        try:
            return int(self.get())
        except:
            return 0

    def validateInt(self, action, index, value_if_allowed,
                    prior_value, text, validation_type, trigger_type, widget_name):
        if self.on_key_callback is not None:
            self.on_key_callback()
        if value_if_allowed == "":
            return True
        if value_if_allowed:
            try:
                if (len(value_if_allowed) > 1 and value_if_allowed[0] == "0") or (int(value_if_allowed) > self.max):
                    return False
                return True
            except ValueError:
                return False
        else:
            return False


class AngleBox(tk.Toplevel):
    def __init__(self, app):
        tk.Toplevel.__init__(self, app)
        self.title("PLCT: Angle")
        self.resizable(0, 0)
        self.attributes("-topmost", True)

        self._var = tk.StringVar(app, "0.00")
        self._app: PerfectlyLegalCoopTool = app
        # ttk.Label justify doesn't work smh
        tk.Label(self, textvariable=self._var, font=("Arial", 50), width=6, justify=tk.CENTER).grid(
            row=0, column=0, padx=5, pady=5, sticky="we")
        self.after(0, self._loop)

    def _get_angle_str(self, angle: float):
        while angle > 180:
            angle -= 360
        while angle < -180:
            angle += 360

        return "%0.2f" % angle

    def _loop(self, *args):
        self.after(50, self._loop)
        clip = self._app._clipboard_var.get()
        if clip != "" and not "not" in clip.lower():
            try:
                self._var.set(self._get_angle_str(float(clip.split()[-2])))
            except:
                pass
        else:
            self._var.set("0.00")


class PerfectlyLegalCoopTool(ttkthemes.ThemedTk):
    def __init__(self, settings: dict = {}, settings_path: str = None) -> None:
        ttkthemes.ThemedTk.__init__(self, theme="breeze".lower())
        self.title("Perfectly Legal Coop Tool v" + VERSION)
        self.resizable(0, 0)
        self.protocol("WM_DELETE_WINDOW", self._exit)
        self.wm_attributes("-topmost", 1)
        try:
            self.iconbitmap(resource_path("PLC.ico"))
        except:
            pass

        # Variables
        self._plct_client: PLCTClient = PLCTClient(self)
        self._instances_folder = settings.get("instancesFolder", "")
        self._last_paste = ""
        self._settings_path = settings_path
        self._original_settings = settings.copy()
        self._uploading = False
        self._saveable = False
        self._intentional_disconnect = True
        self._ctries = 0
        self._last_ping = 0
        self._last_pong = 0

        # Tk Variables
        self._receive_clipboard_var = tk.BooleanVar(
            self, settings.get("receiveClipboard", False))
        self._send_clipboard_var = tk.BooleanVar(
            self, settings.get("sendClipboard", False))
        self._connection_status_var = tk.StringVar(
            self, DISCONNECTED_STR)
        self._instances_folder_var = tk.StringVar(self, self._instances_folder)
        self._clipboard_var = tk.StringVar(
            self, "(Not Connected)")

        # Tk Widgets
        self._address_entry: ttk.Entry
        self._port_entry: IntEntry
        self._clipboard_password_entry: ttk.Entry
        self._upload_password_entry: ttk.Entry
        self._save_button: ttk.Button
        self._upload_button: ttk.Button
        self.angle_box: tk.Toplevel = None

        # Setup
        self._init_widgets()

        self._address_entry.insert(0, settings.get("address", ""))
        self._port_entry.insert(0, settings.get("port", 25563))
        self._clipboard_password_entry.insert(
            0, settings.get("clipboardPassword", ""))
        self._instances_folder_var.set(".................... Currently Unset" if (
            self._instances_folder is None or self._instances_folder == "") else ".................... " + self._instances_folder)
        self._upload_password_entry.insert(
            0, settings.get("uploadPassword", ""))

        self._reset_states()

        self.after(0, self._loop)

    def _init_widgets(self) -> None:
        main_frame = ttk.Frame()
        main_frame.grid(row=0, column=0)

        self._init_connection_widgets(main_frame)
        self._init_clipboard_widgets(main_frame)
        self._init_upload_widgets(main_frame)

        save_frame = ttk.Frame(main_frame)
        save_frame.grid(row=100, column=0, padx=5, pady=5)
        self._save_button = ttk.Button(
            save_frame, text="Save", command=self._save)
        self._save_button.grid(row=0, column=0, padx=5)
        self._undo_button = ttk.Button(
            save_frame, text="Undo Changes", command=self._reload_original_settings)
        self._undo_button.grid(row=0, column=1, padx=5)

        ttk.Label(
            main_frame, text=f"PLCT v{VERSION} by Duncan", font=("Arial", 6)).grid(row=200, columnspan=50, padx=2, pady=2)

    def _init_connection_widgets(self, parent) -> None:
        outer_connection_frame = RetractableFrame(parent, text="Connection")
        outer_connection_frame.grid(row=0, column=0, padx=5, pady=5)
        connection_frame = outer_connection_frame.inner_frame
        ttk.Label(connection_frame, textvariable=self._connection_status_var).grid(
            row=0, column=0, padx=5, pady=5, columnspan=2)

        entry_frame = ttk.Frame(connection_frame)
        entry_frame.grid(row=1, column=0, padx=5, pady=5,
                         sticky="w", columnspan=2)

        ttk.Label(entry_frame, text="Address/Port:").grid(row=0, column=0)
        self._address_entry = ttk.Entry(
            entry_frame, width=10, validate='key', validatecommand=self._set_saveable)
        self._address_entry.grid(row=0, column=1)
        self._port_entry = IntEntry(entry_frame, 65535, self._set_saveable)
        self._port_entry.config(width=7)
        self._port_entry.grid(row=0, column=2)

        #button_frame = ttk.Frame(connection_frame)
        #button_frame.grid(row=2, column=0, pady=5, sticky="w", padx=5)
        button_frame = connection_frame

        ttk.Button(button_frame, text="Connect",
                   command=self._connect_button).grid(row=10, column=0, padx=5, sticky="we", pady=5)
        ttk.Button(button_frame, text="Disconnect",
                   command=self._disconnect_button).grid(row=10, column=1, padx=5, sticky="we", pady=5)

    def _init_clipboard_widgets(self, parent) -> None:
        outer_clipboard_frame = RetractableFrame(parent, text="Coop Clipboard")
        outer_clipboard_frame.grid(row=1, column=0, padx=5, pady=5)
        clipboard_frame = outer_clipboard_frame.inner_frame
        outer_clipboard_frame.retract()

        ttk.Checkbutton(clipboard_frame, text="Receive Clipboard", variable=self._receive_clipboard_var, command=self._on_receive_clipboard_button).grid(
            row=0, column=0, padx=5, pady=5)

        current_clipboard_frame = ttk.Frame(clipboard_frame)
        current_clipboard_frame.grid(
            row=1, column=0, padx=5, pady=5, sticky="w")

        ttk.Label(current_clipboard_frame, text="Server's Clipboard:").grid(
            row=0, column=0)
        tk.Label(current_clipboard_frame, textvariable=self._clipboard_var, width=25).grid(
            row=1, column=0)

        ttk.Button(current_clipboard_frame,
                   text="Show Angle Box", command=self._show_angle_box).grid(row=2, column=0)

        ttk.Separator(clipboard_frame, orient=tk.HORIZONTAL).grid(
            row=100, column=0, columnspan=5, pady=5, sticky="we")

        send_frame = ttk.Frame(clipboard_frame)
        send_frame.grid(row=101, column=0, padx=5, pady=5, sticky="w")

        ttk.Checkbutton(send_frame, text="Send Clipboard",
                        variable=self._send_clipboard_var, command=self._on_send_clipboard_button).grid(row=0, column=0)

        password_frame = ttk.Frame(send_frame)
        password_frame.grid(row=1, column=0, sticky="w")

        ttk.Label(password_frame, text="Send Password:").grid(row=0, column=0)
        self._clipboard_password_entry = ttk.Entry(
            password_frame, validate='key', validatecommand=self._set_saveable, width=14)
        self._clipboard_password_entry.grid(row=0, column=1)

    def _init_upload_widgets(self, parent) -> None:
        outer_upload_frame = RetractableFrame(parent, text="World Upload")
        outer_upload_frame.grid(row=2, column=0, padx=5, pady=5)
        upload_frame = outer_upload_frame.inner_frame
        outer_upload_frame.retract()

        path_frame = ttk.Frame(upload_frame)
        path_frame.grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(path_frame, text="MultiMC Instances Folder:").grid(
            row=0, column=0, pady=3, columnspan=2)
        tk.Label(path_frame, textvariable=self._instances_folder_var, anchor=tk.E, width=15).grid(
            row=1, column=1, padx=5, pady=0, sticky="w")
        ttk.Button(path_frame, text="Set", command=self._set_instances_path_button, width=3).grid(
            row=1, column=0, pady=0, sticky="w")

        ttk.Separator(upload_frame, orient=tk.HORIZONTAL).grid(
            row=1, column=0, columnspan=5, sticky="we", pady=5)

        button_frame = ttk.Frame(upload_frame)
        button_frame.grid(row=2, column=0, padx=5, pady=5)

        self._upload_button = ttk.Button(button_frame, text="Upload Latest World",
                                         command=self._upload_latest_button, width=18)
        self._upload_button.grid(row=0, column=0, sticky="w")

        ttk.Button(button_frame, text="Test",
                   command=self._test_latest_button, width=4).grid(row=0, column=1, sticky="w")

        password_frame = ttk.Frame(upload_frame)
        password_frame.grid(row=3, column=0, padx=5, pady=5)

        ttk.Label(password_frame, text="Upload Password:").grid(
            row=0, column=0)
        self._upload_password_entry = ttk.Entry(
            password_frame, validate='key', validatecommand=self._set_saveable, width=14)
        self._upload_password_entry.grid(row=0, column=1)

    def _show_angle_box(self, *args) -> None:
        if self.angle_box is None:
            self.angle_box = AngleBox(self)
        elif not self.angle_box.winfo_exists():
            self.angle_box = None
            self.angle_box = AngleBox(self)
        self.angle_box.focus()

    def _set_instances_path_button(self, *args) -> None:
        ans = ask_for_directory(self._instances_folder)
        if ans != "":
            instances_folder = ensure_instances_path(ans)
            if instances_folder is None:
                tkMessageBox.showerror("Easy Multi: Not an instances folder.",
                                       "The selected directory was not an instances folder\nor the folder doesn't contain any instances yet.\nAttempts to located a related instances folder also failed.")
            else:
                self._instances_folder = instances_folder
                self._instances_folder_var.set(".................... Currently Unset" if (
                    self._instances_folder is None or self._instances_folder == "") else ".................... " + self._instances_folder)
                self._set_saveable()

    def _on_receive_clipboard_button(self, *args) -> None:
        if self._receive_clipboard_var.get():
            message = self._clipboard_var.get()
            if not (clipboard.paste() == message or message == ""):
                clipboard.copy(message)
            print("Received clipboard.")
        self._set_saveable()

    def _upload_latest_button(self, *args) -> None:
        if not self._uploading:
            threading.Thread(target=self._upload_latest_world).start()

    def _upload_latest_world(self) -> None:
        self._uploading = True
        try:
            self._upload_button.config(text="Uploading...")
            if self._plct_client.get_status() == "connected" and self._instances_folder is not None and self._instances_folder != "":
                world_path = get_latest_world_from_instances(
                    self._instances_folder)
                if not UPLOADS_ENTIRE_WORLD:
                    level_dat_path = os.path.join(world_path, "level.dat")
                    self._plct_client.send_with_lock(json.dumps({
                        "type": "upload",
                        "password": self._upload_password_entry.get(),
                        "name": "level.dat",
                        "dir": "world",
                        "size": os.path.getsize(level_dat_path)
                    }).encode())
                    with open(level_dat_path, "rb") as dat_file:
                        while True:
                            data = dat_file.read(BUFFER_SIZE)
                            if not data:
                                break
                            self._plct_client.send_with_lock(data)
                        dat_file.close()
                else:
                    self._archive_upload_world(world_path)
                self._plct_client.send_with_lock(json.dumps({
                    "type": "uploaddone",
                    "password": self._upload_password_entry.get()
                }).encode())
                tkMessageBox.showinfo("PLCT: Upload Latest World",
                                      "Successfully uploaded " + (world_path.replace("\\", "/")) + ".\n(If the password was incorrect, the server ignored your upload)")
            else:
                tkMessageBox.showerror(
                    "PLCT: Upload Latest World", ((
                        "\nNo instances folder set." if self._instances_folder is None or self._instances_folder == "" else ""
                    ) + (
                        "" if self._plct_client.get_status(
                        ) == "connected" else "\nNot connected to any server."
                    )).rstrip())
        except:
            tkMessageBox.showerror(
                "PLCT: Upload Latest World", "Failed to upload world:\n" + traceback.format_exc())
            print("Failed")
        self._uploading = False
        self._upload_button.config(text="Upload Latest World")

    def send_file(self, file_path: str, dir: str) -> None:
        self._plct_client.send_with_lock(json.dumps({
            "type": "upload",
            "password": self._upload_password_entry.get(),
            "dir": dir.replace("\\", "/"),
            "size": os.path.getsize(file_path),
            "name": os.path.split(file_path.replace("\\", "/"))[-1].strip("/")
        }).encode())
        with open(file_path, "rb") as f:
            with self._plct_client.get_send_lock():
                while True:
                    data = f.read(BUFFER_SIZE)
                    if not data:
                        break
                    self._plct_client.send(data)
                # As uploads can take a while, update last pong as to not needlessly terminate the socket.
                self._got_pong()
            f.close()

    # New World Upload
    def _archive_upload_world(self, world_path) -> None:
        world_name = os.path.split(world_path)[-1]
        zip_name = world_name + ".zip"
        shutil.make_archive(world_name, "zip", world_path)
        self.send_file(os.path.join(os.getcwd(), zip_name), "")
        os.remove(zip_name)

    # Old World Upload
    def _upload_entire_world(self, world_path) -> None:
        world_name = os.path.split(
            world_path.replace("\\", "/"))[-1].strip("/")

        files_to_upload = ["level.dat"]
        folders_to_upload = ["advancements", "data",
                             "playerdata", "poi", "region", "stats"]

        for file_name in files_to_upload:
            self.send_file(os.path.join(world_path, file_name), world_name)
        for folder_name in folders_to_upload:
            folder_path = os.path.join(world_path, folder_name)
            if os.path.isdir(folder_path):
                for file_name in os.listdir(folder_path):
                    self.send_file(os.path.join(folder_path, file_name),
                                   os.path.join(world_name, folder_name))

    def _test_latest_button(self, *args) -> None:
        if self._instances_folder is not None and self._instances_folder != "":
            tkMessageBox.showinfo("PLCT: Test Latest World", "Current latest world: " +
                                  get_latest_world_from_instances(self._instances_folder).replace("\\", "/"))
        else:
            tkMessageBox.showerror(
                "PLCT: Test Latest World", "No instances folder set.")

    def _reset_states(self) -> None:
        self._save_button.config(state="disabled")
        self._undo_button.config(state="disabled")
        self._clipboard_password_entry.config(
            state=("enabled" if self._send_clipboard_var.get() else "disabled"))
        self._saveable = False

    def _loop(self) -> None:
        self._connection_status_var.set(self._plct_client.get_status_display())
        if not self._plct_client.get_status() == "connected":
            self._clipboard_var.set("(Not Connected)")

        threading.Thread(target=self._inner_loop).start()

    # Anything that can take more than a ms or two or uses a lock should go in here.
    # Prevents tk from appearing crashed while send lock is in use.
    def _inner_loop(self) -> None:
        new_paste = clipboard.paste()
        if new_paste != self._last_paste:
            self._last_paste = new_paste
            if self._send_clipboard_var.get() and self._clipboard_var.get() != new_paste and is_pos_command(new_paste):
                print("Sending clipboard...")
                self._plct_client.send_with_lock(json.dumps({
                    "type": "copy",
                    "password": self._clipboard_password_entry.get(),
                    "copymsg": new_paste
                }).encode())

        if not self._intentional_disconnect and self._plct_client.get_status() == "disconnected":
            if self._ctries < 5:
                threading.Thread(target=self._plct_client.connect,
                                 args=(None, None, self._got_pong)).start()
                self._ctries += 1
            else:
                print("Failed to reconnect after 5 tries, giving up.")
                self._intentional_disconnect = True
                tkMessageBox.showwarning(
                    "PLCT: Disconnected", "You have disconnected from the server and could not reconnect after 5 attempts.")
                self._ctries = 0

        if self._plct_client.get_status() == "connected":

            if abs(time.time() - self._last_ping) > 10:
                self._plct_client.send_with_lock(
                    json.dumps({"type": "ping"}).encode())
                self._last_ping = time.time()

            stopped_responding = False
            with self._plct_client.get_send_lock():
                if abs(time.time() - self._last_pong) > 20:
                    print("Server stopped responding, reconnecting...")
                    stopped_responding = True
            if stopped_responding:
                self._plct_client.disconnect()

        self.after(50, self._loop)

    def _connect_button(self, *args) -> None:
        threading.Thread(target=self._plct_client.connect, args=(
            self._address_entry.get(), self._port_entry.get_int(), self._on_first_connect)).start()

    def _disconnect_button(self, *args) -> None:
        self._intentional_disconnect = True
        self._plct_client.disconnect()

    def _on_first_connect(self, success: bool) -> None:
        self._intentional_disconnect = not success
        self._last_ping = time.time()
        self._got_pong(success)

    def _got_pong(self, success: bool = True) -> None:
        if success:
            self._last_pong = time.time()
            self._ctries = 0

    def set_clipboard(self, message) -> None:
        self._clipboard_var.set(message)
        if self._receive_clipboard_var.get():
            if not (clipboard.paste() == message or message == ""):
                clipboard.copy(message)
            print("Received clipboard.")

    def _exit(self, *args) -> None:
        ans = False
        if self._saveable:
            ans = tkMessageBox.askyesnocancel("PLCT: Exit", "Save settings?")
        if ans is not None:
            if ans:
                self._save()
            self._intentional_disconnect = True
            self._plct_client.disconnect()
            self.destroy()

    def _on_send_clipboard_button(self, *args) -> None:
        self._clipboard_password_entry.config(
            state=("enabled" if self._send_clipboard_var.get() else "disabled"))
        self._set_saveable()

    def _set_saveable(self, *args) -> None:
        self._save_button.config(state="enabled")
        self._undo_button.config(state="enabled")
        self._saveable = True
        return True

    def _save(self) -> None:
        print("Saving...")
        try:
            new_settings = {
                "address": self._address_entry.get(),
                "port": self._port_entry.get_int(),
                "receiveClipboard": self._receive_clipboard_var.get(),
                "sendClipboard": self._send_clipboard_var.get(),
                "clipboardPassword": self._clipboard_password_entry.get(),
                "instancesFolder": self._instances_folder,
                "uploadPassword": self._upload_password_entry.get()
            }
            with open(self._settings_path, "w+") as settings_file:
                json.dump(new_settings, settings_file, indent=4)
                settings_file.close()
            self._original_settings = new_settings.copy()
        except:
            print("Failed to save.")
        self._reset_states()

    def _reload_original_settings(self, *args) -> None:
        self._address_entry.delete(0, tk.END)
        self._address_entry.insert(
            0, self._original_settings.get("address", ""))
        self._port_entry.delete(0, tk.END)
        self._port_entry.insert(
            0, self._original_settings.get("port", ""))
        self._receive_clipboard_var.set(
            self._original_settings.get("receiveClipboard", False))
        self._send_clipboard_var.set(
            self._original_settings.get("sendClipboard", False))

        self._clipboard_password_entry.config(state="enabled")
        self._clipboard_password_entry.delete(0, tk.END)
        self._clipboard_password_entry.insert(
            0, self._original_settings.get("clipboardPassword", ""))

        self._upload_password_entry.config(state="enabled")
        self._upload_password_entry.delete(0, tk.END)
        self._upload_password_entry.insert(
            0, self._original_settings.get("uploadPassword", ""))

        self._instances_folder = self._original_settings.get(
            "instancesFolder", "")
        self._instances_folder_var.set(".................... Currently Unset" if (
            self._instances_folder is None or self._instances_folder == "") else ".................... " + self._instances_folder)

        self._reset_states()


def main():
    settings_json = {}
    if os.path.isfile("plct_settings.json"):
        with open("plct_settings.json", "r") as settings_file:
            settings_json = json.load(settings_file)
            settings_file.close()
    plct = PerfectlyLegalCoopTool(settings_json, "plct_settings.json")
    plct.mainloop()


if __name__ == "__main__":
    try:
        main()
    except:
        import webbrowser, os, time, traceback
        error = traceback.format_exc()
        print(error)
        ans = tkMessageBox.askyesno(
            "PLCT Error", "An error has occured running PLCT,\ncreate error file and open?")
        if ans:
            if not os.path.isdir("crashes"):
                os.mkdir("crashes")
            name = str(time.time()) + ".txt"
            f = open("crashes/" + name, "w+")
            f.write(error)
            f.close()
            webbrowser.open(os.path.abspath(
                os.path.join(os.getcwd(), "crashes", name)))
