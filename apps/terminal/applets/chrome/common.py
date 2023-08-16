import abc
import base64
import json
import locale
import os
import subprocess
import sys
import time
from subprocess import CREATE_NO_WINDOW
from threading import Thread

_blockInput = None
_messageBox = None
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    import win32ui

    # import win32con

    _messageBox = win32ui.MessageBox

    _blockInput = ctypes.windll.user32.BlockInput
    _blockInput.argtypes = [wintypes.BOOL]
    _blockInput.restype = wintypes.BOOL


def block_input():
    if _blockInput:
        _blockInput(True)


def unblock_input():
    if _blockInput:
        _blockInput(False)


def notify_err_message(msg):
    if _messageBox:
        # _messageBox 是阻塞当前线程的，所以需要开启一个新线程执行
        t = Thread(target=_messageBox, args=(msg, 'Error'), kwargs={})
        t.daemon = True
        t.start()


def decode_content(content: bytes) -> str:
    for encoding_name in ['utf-8', 'gbk', 'gb2312']:
        try:
            return content.decode(encoding_name)
        except Exception as e:
            print(e)
    encoding_name = locale.getpreferredencoding()
    return content.decode(encoding_name)


def check_pid_alive(pid) -> bool:
    # tasklist  /fi "PID eq 508" /fo csv
    # '"映像名称","PID","会话名      ","会话#   ","内存使用 "\r\n"wininit.exe","508","Services","0","6,920 K"\r\n'
    try:

        csv_ret = subprocess.check_output(["tasklist", "/fi", f'PID eq {pid}', "/fo", "csv"],
                                          creationflags=CREATE_NO_WINDOW)
        content = decode_content(csv_ret)
        content_list = content.strip().split("\r\n")
        if len(content_list) != 2:
            print("check pid {} ret invalid: {}".format(pid, content))
            return False
        ret_pid = content_list[1].split(",")[1].strip('"')
        return str(pid) == ret_pid
    except Exception as e:
        print("check pid {} err: {}".format(pid, e))
        return False


def wait_pid(pid):
    while 1:
        time.sleep(5)
        ok = check_pid_alive(pid)
        if not ok:
            print("pid {} is not alive".format(pid))
            break


class DictObj(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, val in self.items():
            if isinstance(val, (list, tuple)):
                setattr(self, key, [DictObj(x) if isinstance(x, dict) else x for x in val])
            else:
                setattr(self, key, DictObj(val) if isinstance(val, dict) else val)

    def __getattr__(self, item):
        return self.get(item, None)


class User(DictObj):
    id: str
    name: str
    username: str


class Step(DictObj):
    step: int
    target: str
    command: str
    value: str


class Specific(DictObj):
    # web
    autofill: str
    username_selector: str
    password_selector: str
    submit_selector: str
    script: list[Step]

    # database
    db_name: str


class Category(DictObj):
    value: str
    label: str


class Protocol(DictObj):
    id: str
    name: str
    port: int


class Asset(DictObj):
    id: str
    name: str
    address: str
    protocols: list[Protocol]
    category: Category
    spec_info: Specific

    def get_protocol_port(self, protocol):
        for item in self.protocols:
            if item.name == protocol:
                return item.port
        return None


class LabelValue(DictObj):
    label: str
    value: str


class Account(DictObj):
    id: str
    name: str
    username: str
    secret: str
    secret_type: LabelValue


class ProtocolSetting(DictObj):
    autofill: str
    username_selector: str
    password_selector: str
    submit_selector: str
    script: list[Step]
    safe_mode: bool


class PlatformProtocolSetting(DictObj):
    name: str
    port: int
    setting: ProtocolSetting


class Platform(DictObj):
    id: str
    name: str
    charset: LabelValue
    type: LabelValue
    protocols: list[PlatformProtocolSetting]

    def get_protocol_setting(self, protocol):
        for item in self.protocols:
            if item.name == protocol:
                return item.setting
        return None


class Manifest(DictObj):
    name: str
    version: str
    path: str
    exec_type: str
    connect_type: str
    protocols: list[str]


def get_manifest_data() -> dict:
    current_dir = os.path.dirname(__file__)
    manifest_file = os.path.join(current_dir, 'manifest.json')
    try:
        with open(manifest_file, "r", encoding='utf8') as f:
            return json.load(f)
    except Exception as e:
        print(e)
    return {}


def read_app_manifest(app_dir) -> dict:
    main_json_file = os.path.join(app_dir, "manifest.json")
    if not os.path.exists(main_json_file):
        return {}
    with open(main_json_file, 'r', encoding='utf8') as f:
        return json.load(f)


def convert_base64_to_dict(base64_str: str) -> dict:
    try:
        data_json = base64.decodebytes(base64_str.encode('utf-8')).decode('utf-8')
        return json.loads(data_json)
    except Exception as e:
        print(e)
    return {}


class BaseApplication(abc.ABC):

    def __init__(self, *args, **kwargs):
        self.app_name = kwargs.get('app_name', '')
        self.protocol = kwargs.get('protocol', '')
        self.manifest = Manifest(kwargs.get('manifest', {}))
        self.user = User(kwargs.get('user', {}))
        self.asset = Asset(kwargs.get('asset', {}))
        self.account = Account(kwargs.get('account', {}))
        self.platform = Platform(kwargs.get('platform', {}))

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError('run')

    @abc.abstractmethod
    def wait(self):
        raise NotImplementedError('wait')
