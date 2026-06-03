import os
import yaml
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from common.utils import get_logger
from common.decorators import Singleton
from common.const import Language
from .utils import detect_cert_algorithm


logger = get_logger(__name__)


# @Singleton
class UKeySDKConfig:

    def __init__(self):
        if not settings.AUTH_UKEY:
            logger.debug('UKeySDKConfig: authentication backend not enabled')
            return
        cf_path = self.get_sdk_config_yaml_path()
        self._raw = self._load_yaml(cf_path)

    # ── YAML 加载 ────────────────────────────────────────────────────────────

    def _vendor_path(self, filename):
        return os.path.join(
            settings.PROJECT_DIR,
            "apps", "authentication", "backends", "ukey", "vendors",
            settings.AUTH_UKEY_VENDOR, filename,
        )

    def get_sdk_script_js_path(self):
        return self._vendor_path('sdk_script.js')

    def get_sdk_config_yaml_path(self):
        return self._vendor_path('sdk_config.yaml')

    @staticmethod
    def _load_yaml(config_file):
        if not config_file or not os.path.isfile(config_file):
            logger.warning('UKeySDKConfig: config file not found: %s', config_file)
            return {}
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    # ── CA / 证书链（只读系统设置，不允许在 YAML 中配置）────────────────────────

    @property
    def ca_cert_content(self):
        """CA 根证书 PEM 内容，只从系统设置读取。"""
        return getattr(settings, 'AUTH_UKEY_CA_CERT_CONTENT', '') or ''

    @property
    def ca_key_content(self):
        """CA 私钥 PEM 内容，只从系统设置读取。"""
        return getattr(settings, 'AUTH_UKEY_CA_KEY_CONTENT', '') or ''

    @property
    def ca_key_pass(self):
        """CA 私钥密码，只从系统设置读取。"""
        return str(getattr(settings, 'AUTH_UKEY_CA_KEY_PASS', ''))
    
    @property
    def ca_cert_asym_alg(self):
        # 从 CA 证书内容解析出签名算法类型，返回 'RSA' 或 'SM2' 等字符串，供 YAML 配置中使用
        return detect_cert_algorithm(self.ca_cert_content)

    # ── 工具 ─────────────────────────────────────────────────────────────────

    @property
    def gmssl_bin(self):
        """gmssl 二进制路径，默认 'gmssl'（系统 PATH 中查找）。"""
        return 'gmssl'

    # ── 认证流程 ──────────────────────────────────────────────────────────────

    @property
    def challenge_ttl(self):
        """Challenge 码在 Redis 中的存活时间（秒），默认 300。"""
        v = getattr(settings, 'AUTH_UKEY_CHALLENGE_TTL', 300)
        return int(v)

    # ── 证书签发 ──────────────────────────────────────────────────────────────

    @property
    def enroll_enabled(self):
        """是否开启用户证书签发功能。"""
        v = getattr(settings, 'AUTH_UKEY_ENROLL_ENABLED', False)
        return bool(v)

    @property
    def enroll_validity_days(self):
        """签发证书的有效期（天），默认 365。"""
        v = getattr(settings, 'AUTH_UKEY_ENROLL_VALIDITY_DAYS', 365)
        return int(v)
    
    @property
    def default_pin(self):
        """证书默认 PIN 码，默认为空字符串（不设置 PIN）。"""
        v = getattr(settings, 'AUTH_UKEY_DEFAULT_PIN', '')
        return str(v)

    # ── 厂商 SDK 映射（原始数据，供 API 层序列化给前端）───────────────────────
        
    @staticmethod
    def _render(data, trans_filter=None):
        """
        只处理 YAML 数据中的 i18n 翻译标记，不做模板变量替换。
          - {{ 'text' | trans }} → 按 trans_filter 翻译；不传则原文返回
        """
        import re
        _filter = trans_filter or (lambda s: s)
        _pattern = re.compile(r"""\{\{\s*['"](.+?)['"]\s*\|\s*trans\s*\}\}""")

        def _translate(s):
            return _pattern.sub(lambda m: _filter(m.group(1)), s)

        def _walk(obj):
            if isinstance(obj, dict):
                return {k: _walk(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_walk(item) for item in obj]
            if isinstance(obj, str):
                return _translate(obj)
            return obj

        return _walk(data)

    def _build_trans_filter(self, lang):
        """构建 Jinja2 | trans filter 函数，按 lang 从 YAML i18n 表查找翻译。
        未找到翻译时原文返回；语言键自动归一化（zh_hant → zh-hant）。
        """
        i18n_raw = self._raw.get('i18n') or {}
        i18n = {
            text: {
                Language.to_internal_code(lk.replace('_', '-')): lv
                for lk, lv in entries.items()
            }
            for text, entries in i18n_raw.items()
            if isinstance(entries, dict)
        }

        def trans_filter(s):
            translations = i18n.get(str(s))
            if not translations:
                return s
            return translations.get(lang) or translations.get('en') or s

        return trans_filter

    def get_vendor_sdk_data(self, lang='en'):
        """返回去掉 'cert'/'i18n' 顶层 key 后的厂商 SDK 方法映射。
        YAML 中任意字符串值均可用 {{ 'text' | trans }} 语法标记为可翻译。
        """
        lang = Language.to_internal_code(lang)
        trans_filter = self._build_trans_filter(lang)
        data = self._render(self._raw, trans_filter)
        data = self._apply_cert_config_to_data(data)
        data = {k: v for k, v in data.items() if k not in ('i18n',)}
        return data
    
    # 当一个 config 值是含这些 key 的 dict 时，视为"算法分支字典"，自动按当前证书算法解析
    _ALGO_BRANCH_KEYS = frozenset({'SM2', 'RSA-1024', 'RSA-2048', 'default'})

    @classmethod
    def _is_algo_branch(cls, value):
        """判断 value 是否为算法分支字典（至少含一个已知算法 key）。"""
        return isinstance(value, dict) and bool(cls._ALGO_BRANCH_KEYS & value.keys())

    def _resolve_algo_branch(self, branch, algo_key):
        """从算法分支字典中取当前算法对应的值，找不到时退回 default，再找不到返回 None。"""
        if algo_key in branch:
            return branch[algo_key]
        return branch.get('default')

    def _apply_cert_config_to_data(self, data):
        """将 'config' 配置段渲染后添加到 data['config']，供前端 API 层使用。
        
        YAML config 中值为算法分支字典（含 SM2/RSA-1024/RSA-2048/default 等 key）的字段，
        会自动根据 CA 证书算法类型解析为对应的标量值，无需在此处逐字段枚举。
        """
        config = data.get('config') or {}
        asym_alg_name = self.ca_cert_asym_alg
        algo_key = asym_alg_name or 'default'

        # 自动展开所有算法分支字典字段
        resolved_config = {}
        for k, v in config.items():
            if self._is_algo_branch(v):
                resolved_config[k] = self._resolve_algo_branch(v, algo_key)
            else:
                resolved_config[k] = v

        # 追加后端专有字段（不在 YAML config 中配置）
        resolved_config.update({
            'asymAlgName': asym_alg_name,
            'challenge_ttl': self.challenge_ttl,
            'enroll': {
                'enabled': self.enroll_enabled,
                'validity_days': self.enroll_validity_days,
            },
            'pin': {
                'default': self.default_pin,
            },
            'api': {
                'ukey_sdk_script_url': reverse('api-auth:ukey:ukey-sdk-script'),
                'enroll_cert_url': reverse('api-auth:ukey:ukey-enroll-cert'),
                'bind_user_ukey_sn_url': reverse('api-auth:ukey:bind-user-ukey-sn'),
                'user_detail_url': reverse('users:user-list') + '{user_id}/',
            },
        })
        data['config'] = resolved_config
        return data


ukey_sdk_config = UKeySDKConfig()
