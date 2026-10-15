import base64
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import struct
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from common import wait_pid, get_system_language, BaseApplication

_default_home = r'C:\Program Files\DBX'

_type_mapping = {
    'postgresql': 'postgres',
    'sqlserver': 'mssql',
    'dameng': 'dm',
}

# 其余协议用的是编译进 DBX 的原生驱动，不需要 agent
# db2 的驱动在驱动包里，但 DBX 0.6.17 的 deep link 没有 db2 的 scheme，manifest 中暂未开放
_agent_mapping = {
    'oracle': 'oracle',
    'dameng': 'dameng',
    'db2': 'db2',
}

# DBX 支持的界面语言，取自其 i18n 的 supportedLocales
_locales = ('az', 'en', 'es', 'it', 'ja', 'ko', 'pt-BR', 'tr', 'zh-CN', 'zh-TW')
# 语言标签前缀与 DBX locale 的对应，写不在 _locales 里的值 DBX 会当成没设置
_locale_prefixes = (
    ('zh-hant', 'zh-TW'), ('zh-tw', 'zh-TW'), ('zh-hk', 'zh-TW'), ('zh-mo', 'zh-TW'), ('zh', 'zh-CN'),
    ('pt', 'pt-BR'), ('az', 'az'), ('en', 'en'), ('es', 'es'), ('it', 'it'),
    ('ja', 'ja'), ('ko', 'ko'), ('tr', 'tr'),
)

_jre_key = '21'
_seed_marker = '.jms_seeded.json'

# 发布机上的 DBX 由应用包统一升级，关掉它自己的更新检查与联网拉取，
# 这些键写进 dbx.db 的 app_state 表就是 DBX 自己的设置
_editor_settings = {
    'autoUpdateApp': False,
    'autoDownloadUpdates': False,
    'updateNotificationsEnabled': False,
    'autoUpdateDrivers': False,
    'autoUpdateJdbc': False,
    'autoUpdateMcp': False,
    'autoUpdatePlugins': False,
    # 右上角那个更新图标由工具栏开关控制，和上面的自动更新是两回事
    'toolbarItems': {'checkUpdates': False},
}

# 代填密码时用于定位控件，取自 DBX 各语言包的 connection.savePassword 与 connection.saveAndConnect
_save_password_labels = (
    'Save password', '保存密码', '儲存密碼', 'パスワードを保存', '비밀번호 저장',
    'Guardar contraseña', 'Salvar senha', 'Salva password', 'Parolayı kaydet', 'Parolu yadda saxla',
)
_submit_labels = (
    'Save & Connect', '保存并连接', '儲存並連線', '保存して接続', '저장 후 연결',
    'Guardar y conectar', 'Salvar e Conectar', 'Salva & Connetti', 'Kaydet ve Bağlan',
    'Yadda saxla və əlaqə qur',
)
_fill_timeout = 20
# tinker 不接管 applet 的标准输出，排查代填与语言问题只能靠这个文件
_log_file = os.environ.get('DBX_LOG_FILE', os.path.join(tempfile.gettempdir(), 'jms-dbx.log'))


def applet_build():
    # 版本号不随每次打包变化，日志里带上 app.py 的指纹，便于确认发布机上跑的是哪一版
    try:
        with open(os.path.abspath(__file__), 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:8]
    except OSError:
        return 'unknown'


def log(message):
    try:
        with open(_log_file, 'a', encoding='utf-8') as f:
            f.write('%s %s\n' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message))
    except OSError:
        pass


class AppletApplication(BaseApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dbx_home = os.environ.get('DBX_HOME', _default_home)
        self.path = os.path.join(dbx_home, 'DBX.exe')
        self.drivers_home = os.environ.get('DBX_DRIVERS_HOME', os.path.join(dbx_home, 'agents'))

        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.name = f'{self.asset.name}[{now}]'

        self.username = self.account.username
        if self.username.lower() == 'null':
            self.username = ''
        self.password = self.account.secret
        self.use_sysdba = self.get_use_sysdba()
        self.host = self.asset.address
        self.port = self.asset.get_protocol_port(self.protocol)
        if self.tinker_forward:
            self.host = self.tinker_forward.host
            self.port = self.tinker_forward.port

        self.db = self.asset.spec_info.db_name or ''
        self.lang = self.get_lang()
        self.app_work_path = self.get_app_work_path()
        self.agents_path = self.get_agents_path()
        self.pid = None

    def get_use_sysdba(self):
        # Oracle 是否以 sysdba 连接由 connect_options 给出，老版本没有该选项时按特权账号判断
        use_sysdba = getattr(self.connect_option, 'use_sysdba', None)
        if use_sysdba is None:
            return bool(getattr(self.account, 'privileged', False))
        return str(use_sysdba).lower() in ('true', '1', 'yes', 'on')

    def get_lang(self):
        lang = (getattr(self.connect_option, 'lang', '') or get_system_language() or '').replace('_', '-')
        for locale in _locales:
            if lang.lower() == locale.lower():
                return locale
        lang = lang.lower()
        for prefix, locale in _locale_prefixes:
            if lang == prefix or lang.startswith(prefix + '-'):
                return locale
        return ''

    @property
    def _type(self):
        return _type_mapping.get(self.protocol, self.protocol)

    @staticmethod
    def get_app_work_path():
        return os.path.join(Path.home(), 'AppData', 'Roaming', 'com.dbx.app')

    @staticmethod
    def get_agents_path():
        return os.path.join(Path.home(), '.dbx', 'agents')

    def clean(self):
        # 只清数据目录，agents 是驱动，清掉下次会话得重新播种
        if os.environ.get('DBX_CLEAN_HOME_AT_CLOSE', 'true') in ['true', 'True', '1']:
            shutil.rmtree(self.app_work_path, ignore_errors=True)

    @staticmethod
    def _read_json(path, default=None):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError):
            return {} if default is None else default

    @staticmethod
    def _write_json(path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)

    def _update_state(self, agent, version):
        # DBX 靠 state.json 判断驱动装没装，只铺文件不更新它照样会去下载
        bundle_state = self._read_json(os.path.join(self.drivers_home, 'state.json'))
        state = self._read_json(os.path.join(self.agents_path, 'state.json'))

        installed = state.get('installed_drivers') or {}
        installed[agent] = bundle_state.get('installed_drivers', {}).get(agent) or {
            'version': version, 'jre': _jre_key,
            'installed_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        state['installed_drivers'] = installed
        # 指向安装目录里的 JRE，省掉每个会话用户一份 100MB 的托管 JRE
        state['java_runtime'] = {
            'mode': 'custom',
            'custom_java_path': os.path.join(self.drivers_home, f'jre-{_jre_key}'),
        }
        state.setdefault('pending_jre_cleanup', [])

        self._write_json(os.path.join(self.agents_path, 'state.json'), state)

    def init_agent(self):
        # DBX 固定到 %USERPROFILE%\.dbx\agents 找驱动，而每个会话都是独立用户
        agent = _agent_mapping.get(self.protocol)
        if not agent:
            return

        src = os.path.join(self.drivers_home, 'drivers', agent)
        if not os.path.isdir(src):
            print(f'Driver {agent} not found in {self.drivers_home}, please check the driver package')
            return

        bundle = self._read_json(os.path.join(self.drivers_home, '.jms_bundle.json'))
        version = bundle.get('drivers', {}).get(agent, '')

        marker_path = os.path.join(self.agents_path, _seed_marker)
        seeded = self._read_json(marker_path)

        dst = os.path.join(self.agents_path, 'drivers', agent)
        if seeded.get(agent) != version or not os.path.isdir(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
            seeded[agent] = version
            self._write_json(marker_path, seeded)

        self._update_state(agent, version)

    def init_config(self):
        # 安装目录下的 dbx.db 用来固定 AI、MCP、插件、更新检查等默认设置
        config_src = os.path.join(os.path.dirname(self.path), 'dbx.db')
        if not os.path.exists(config_src):
            return
        os.makedirs(self.app_work_path, exist_ok=True)
        shutil.copy2(config_src, self.app_work_path)

    def init_settings(self):
        # DBX 的设置存在数据目录的 dbx.db 里，启动时只会 CREATE TABLE IF NOT EXISTS，
        # 先把更新相关的开关写进去，用户就不会收到更新提示，也不会自己把 DBX 升级掉
        os.makedirs(self.app_work_path, exist_ok=True)
        try:
            conn = sqlite3.connect(os.path.join(self.app_work_path, 'dbx.db'))
            try:
                with conn:
                    conn.execute(
                        'CREATE TABLE IF NOT EXISTS app_state (key TEXT PRIMARY KEY, value_json TEXT NOT NULL)'
                    )
                    row = conn.execute(
                        "SELECT value_json FROM app_state WHERE key = 'editor_settings'"
                    ).fetchone()
                    settings = {}
                    if row:
                        try:
                            settings = json.loads(row[0])
                        except ValueError:
                            settings = {}
                    if not isinstance(settings, dict):
                        settings = {}
                    settings.update(_editor_settings)
                    conn.execute(
                        "INSERT OR REPLACE INTO app_state (key, value_json) VALUES ('editor_settings', ?)",
                        (json.dumps(settings),)
                    )
            finally:
                conn.close()
        except sqlite3.Error as e:
            log(f'settings: {e}')

    def launch(self):
        self.clean()
        self.init_config()
        self.init_settings()
        self.init_agent()

    def _get_exec_params(self, with_password=False):
        params = {
            'name': self.name,
            'type': self._type,
            'host': self.host,
            'port': self.port,
            'database': self.db,
            'user': self.username,
        }
        # 默认不把密码放进命令行，改由 fill_password 填进连接对话框；
        # one_time 会让对话框自动提交，只能在兜底时一起用
        if with_password:
            params['password'] = self.password
            params['one_time'] = 'true'
        # DBX 的 sysdba 开关等价于给 agent 传这个选项
        if self.protocol == 'oracle' and self.use_sysdba:
            params['url_params'] = 'AUTH TYPE=SYSDBA'
        query = '&'.join(f'{k}={quote(str(v), safe="")}' for k, v in params.items())
        return f'dbx://connection/new?{query}'

    @staticmethod
    def _free_port():
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]

    @staticmethod
    def _page_socket_urls(port):
        # WebView2 的调试端点，窗口不一定只有一个，全都拿出来
        try:
            with urlopen(f'http://127.0.0.1:{port}/json/list', timeout=2) as resp:
                targets = json.load(resp)
        except (OSError, ValueError):
            return []
        return [
            t['webSocketDebuggerUrl'] for t in targets
            if t.get('type') == 'page' and t.get('webSocketDebuggerUrl')
        ]

    @staticmethod
    def _evaluate(socket_url, expression):
        """向 WebView 发一条 Runtime.evaluate，够用的极简 WebSocket 客户端"""
        _, _, rest = socket_url.partition('://')
        netloc, _, path = rest.partition('/')
        host, _, port = netloc.partition(':')

        conn = socket.create_connection((host, int(port or 80)), timeout=5)
        try:
            key = base64.b64encode(os.urandom(16)).decode()
            conn.sendall((
                f'GET /{path} HTTP/1.1\r\n'
                f'Host: {netloc}\r\n'
                'Upgrade: websocket\r\n'
                'Connection: Upgrade\r\n'
                f'Sec-WebSocket-Key: {key}\r\n'
                'Sec-WebSocket-Version: 13\r\n\r\n'
            ).encode())

            buf = b''
            while b'\r\n\r\n' not in buf:
                chunk = conn.recv(4096)
                if not chunk:
                    return None
                buf += chunk
            if b'101' not in buf.split(b'\r\n', 1)[0]:
                return None

            payload = json.dumps({
                'id': 1, 'method': 'Runtime.evaluate',
                'params': {'expression': expression, 'returnByValue': True},
            }).encode()
            header = b'\x81'
            mask = os.urandom(4)
            if len(payload) < 126:
                header += bytes([0x80 | len(payload)])
            else:
                header += bytes([0x80 | 126]) + struct.pack('>H', len(payload))
            masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            conn.sendall(header + mask + masked)

            data = AppletApplication._read_frame(conn)
            if not data:
                return None
            result = json.loads(data).get('result', {}).get('result', {})
            return result.get('value')
        finally:
            conn.close()

    @staticmethod
    def _read_frame(conn):
        def recv(n):
            buf = b''
            while len(buf) < n:
                chunk = conn.recv(n - len(buf))
                if not chunk:
                    return b''
                buf += chunk
            return buf

        while True:
            head = recv(2)
            if len(head) < 2:
                return b''
            opcode = head[0] & 0x0F
            length = head[1] & 0x7F
            if length == 126:
                length = struct.unpack('>H', recv(2))[0]
            elif length == 127:
                length = struct.unpack('>Q', recv(8))[0]
            body = recv(length)
            if opcode == 0x1:
                return body
            if opcode == 0x8:
                return b''

    def _fill_script(self):
        return """(() => {
  const visible = el => !!el && !!(el.getClientRects().length || el.offsetWidth || el.offsetHeight);
  const dialog = [...document.querySelectorAll('[role="dialog"]')].filter(visible).pop();
  if (!dialog) return 'no-dialog';
  const input = [...dialog.querySelectorAll('input[type="password"]')].find(visible);
  if (!input) return 'no-password';
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(input, %s);
  input.dispatchEvent(new Event('input', {bubbles: true}));
  const boxes = [...dialog.querySelectorAll('input[type="checkbox"]')].filter(visible);
  const labels = %s;
  const save = boxes.find(b => labels.includes(b.getAttribute('aria-label') || '')) || boxes[0];
  if (save && save.checked) save.click();
  return 'filled';
})()""" % (json.dumps(self.password), json.dumps(list(_save_password_labels)))

    @staticmethod
    def _submit_script():
        # 右上角的关闭按钮排在内容之后，是对话框里最后一个 button，只能在页脚里找提交按钮
        return """(() => {
  const visible = el => !!el && !!(el.getClientRects().length || el.offsetWidth || el.offsetHeight);
  const dialog = [...document.querySelectorAll('[role="dialog"]')].filter(visible).pop();
  if (!dialog) return 'no-dialog';
  const footer = dialog.querySelector('[data-slot="dialog-footer"]') || dialog;
  const buttons = [...footer.querySelectorAll('button')]
    .filter(b => visible(b) && !b.disabled && !b.closest('[data-slot="dialog-close"]'));
  const labels = %s;
  const submit = buttons.find(b => labels.includes(b.textContent.trim())) || buttons[buttons.length - 1];
  if (!submit) return 'no-submit';
  submit.click();
  return 'ok';
})()""" % json.dumps(list(_submit_labels))

    def _locale_script(self):
        # DBX 的界面语言存在 localStorage，启动时读不到才回落到 WebView 的语言，
        # 而 WebView 的语言被 wry 钉死成了发布机的 Windows 界面语言
        return """(() => {
  const want = %s;
  // DBX 的取值规则：先看自己存的设置，没有再按 WebView 语言推断
  const fromTag = tag => {
    const v = (tag || '').replace('_', '-').toLowerCase();
    if (v === 'zh' || v.startsWith('zh-')) {
      return (v.includes('hant') || v.startsWith('zh-tw') || v.startsWith('zh-hk') || v.startsWith('zh-mo')) ? 'zh-TW' : 'zh-CN';
    }
    for (const [p, l] of [['az','az'],['en','en'],['es','es'],['it','it'],['ja','ja'],['ko','ko'],['pt','pt-BR'],['tr','tr']]) {
      if (v === p || v.startsWith(p + '-')) return l;
    }
    return null;
  };
  const supported = ['az','en','es','it','ja','ko','pt-BR','tr','zh-CN','zh-TW'];
  let stored = null;
  try {
    stored = localStorage.getItem('dbx-locale');
  } catch (e) {
    return 'no-storage';
  }
  const current = supported.includes(stored) ? stored
    : [...(navigator.languages || []), navigator.language].map(fromTag).find(Boolean) || 'en';
  if (current === want) return 'ready';
  try {
    localStorage.setItem('dbx-locale', want);
  } catch (e) {
    return 'no-storage';
  }
  location.reload();
  return 'reloading';
})()""" % json.dumps(self.lang)

    def wait_page(self, port):
        deadline = time.time() + _fill_timeout
        while time.time() < deadline:
            if self._page_socket_urls(port):
                return True
            time.sleep(0.2)
        return False

    def apply_locale(self, port):
        options = sorted(k for k in vars(self.connect_option)) or None
        log(f'locale: want={self.lang!r} lang={getattr(self.connect_option, "lang", None)!r} connect_options={options}')
        if not self.lang:
            return
        deadline = time.time() + _fill_timeout
        while time.time() < deadline:
            for socket_url in self._page_socket_urls(port):
                try:
                    result = self._evaluate(socket_url, self._locale_script())
                except (OSError, ValueError) as e:
                    result = str(e)
                log(f'locale: {result}')
                if result == 'ready':
                    return
                if result == 'reloading':
                    # 刷新后遮罩由 _mask_worker 补回来
                    time.sleep(1.5)
            time.sleep(0.5)

    def open_connection(self, env, startupinfo, with_password=False):
        subprocess.Popen(
            [self.path, self._get_exec_params(with_password)],
            shell=False, startupinfo=startupinfo, env=env
        )

    @staticmethod
    def _mask_script():
        # 代填过程会露出连接对话框，用一层与应用同色的遮罩盖住；
        # 对话框是 portal 出来的，光靠 z-index 未必压得住，所以把遮罩放进浏览器顶层。
        # 填值和点击都是直接调 DOM，不受遮罩影响
        return """(() => {
  const id = 'jms-connect-mask';
  // 取 index.html 里给 html/body 定死的底色，跟着暗色主题走
  const bg = document.documentElement.classList.contains('dark') ? 'rgb(19 20 22)' : 'rgb(255 255 255)';
  let mask = document.getElementById(id);
  if (!mask) {
    mask = document.createElement('div');
    mask.id = id;
    const style = document.createElement('style');
    style.textContent = '@keyframes jms-spin{to{transform:rotate(360deg)}}';
    const spinner = document.createElement('div');
    spinner.style.cssText = 'width:28px;height:28px;border-radius:50%;animation:jms-spin 1s linear infinite;' +
      'border:3px solid rgba(128,128,128,.25);border-top-color:rgba(128,128,128,.85)';
    mask.appendChild(style);
    mask.appendChild(spinner);
  }
  // popover 打开时 UA 会给一套自己的盒模型，这里全部覆盖掉铺满窗口
  mask.style.cssText = 'position:fixed;inset:0;margin:0;padding:0;border:0;width:auto;height:auto;' +
    'max-width:none;max-height:none;overflow:hidden;z-index:2147483647;display:flex;' +
    'align-items:center;justify-content:center;background:' + bg;
  // 始终挂在 body 末尾，后插入的节点盖不过去
  document.body.appendChild(mask);
  let layer = 'z-index';
  try {
    if ('popover' in HTMLElement.prototype) {
      mask.setAttribute('popover', 'manual');
      if (!mask.matches(':popover-open')) mask.showPopover();
      layer = 'popover';
    }
  } catch (e) {}
  // 回报窗口中心到底是谁在最上面，遮罩再出问题时日志里能直接看出被什么压住了
  const hit = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
  const covered = hit && hit.closest && hit.closest('#' + id)
    ? 'top'
    : 'under-' + (hit ? (hit.getAttribute('data-slot') || hit.id || hit.tagName) : 'none');
  return 'ok:' + layer + ':' + covered;
})()"""

    @staticmethod
    def _unmask_script():
        return """(() => {
  const m = document.getElementById('jms-connect-mask');
  if (!m) return 'ok';
  try {
    if (m.matches(':popover-open')) m.hidePopover();
  } catch (e) {}
  m.remove();
  return 'ok';
})()"""

    def switch_mask(self, port, on):
        script = self._mask_script() if on else self._unmask_script()
        for socket_url in self._page_socket_urls(port):
            try:
                log(f'mask({on}): {self._evaluate(socket_url, script)}')
            except (OSError, ValueError) as e:
                log(f'mask({on}): {e}')

    def _mask_worker(self, port, stop):
        # 对话框由 Vue 在任意时刻弹出，还可能被刷新冲掉，所以持续往所有页面补遮罩
        script = self._mask_script()
        last = None
        while not stop.is_set():
            for socket_url in self._page_socket_urls(port):
                try:
                    result = self._evaluate(socket_url, script)
                except (OSError, ValueError) as e:
                    result = str(e)
                if result != last:
                    log(f'mask: {result}')
                    last = result
            stop.wait(0.2)

    def fill_password(self, port):
        """URL 里不带密码，等对话框出现后填进去并取消勾选保存密码"""
        deadline = time.time() + _fill_timeout
        while time.time() < deadline:
            time.sleep(0.3)
            for socket_url in self._page_socket_urls(port):
                try:
                    filled = self._evaluate(socket_url, self._fill_script())
                    if filled != 'filled':
                        if filled != 'no-dialog':
                            log(f'fill: {filled}')
                        continue
                    time.sleep(0.3)
                    submitted = self._evaluate(socket_url, self._submit_script())
                except (OSError, ValueError) as e:
                    log(f'fill: {e}')
                    continue
                log(f'fill: filled, submit: {submitted}')
                if submitted == 'ok':
                    return True
        return False

    def run(self):
        self.launch()

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        # 调试端口用于设置界面语言和代填密码
        port = self._free_port()
        env = os.environ.copy()
        browser_args = env.get('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS', '')
        env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = f'{browser_args} --remote-debugging-port={port}'.strip()

        # 先起空窗口，设好语言再打开连接，避免刷新页面丢掉连接对话框
        ret = subprocess.Popen([self.path], shell=False, startupinfo=startupinfo, env=env)
        self.pid = ret.pid
        log(f'launch: build={applet_build()} pid={self.pid} port={port} protocol={self.protocol}')

        # 从第一帧起就持续盖住窗口，设语言、刷新、开连接、代填全在遮罩之下
        stop_mask = threading.Event()
        masker = threading.Thread(target=self._mask_worker, args=(port, stop_mask), daemon=True)
        masker.start()
        try:
            self.wait_page(port)
            self.apply_locale(port)
            self.open_connection(env, startupinfo)

            if not self.fill_password(port):
                # 代填失败时退回带密码的连接地址，保证会话可用
                log('fill: failed, fallback to the connection url with password')
                self.open_connection(env, startupinfo, with_password=True)
                time.sleep(1)
        finally:
            stop_mask.set()
            masker.join(timeout=2)
            self.switch_mask(port, False)
        log('run: done')

    def wait(self):
        wait_pid(self.pid)
        self.clean()
