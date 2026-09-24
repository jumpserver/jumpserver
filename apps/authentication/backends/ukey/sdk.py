import os
from copy import deepcopy
from urllib.parse import urlencode
import yaml
from django.conf import settings
from django.urls import reverse
from common.utils import get_logger
from common.const import Language
from .configuration import REVISION, get_snapshot
from .providers import get_provider


logger = get_logger(__name__)


class UKeySDKConfig:

    _sdk_script_cache = {}
    _sdk_config_cache = {}

    def __init__(self, snapshot=None):
        self._snapshot = snapshot if snapshot is not None else get_snapshot()
        self._provider = get_provider(self._snapshot)

    @property
    def snapshot(self):
        return self._snapshot

    @property
    def provider(self):
        return self._provider

    def _vendor_path(self, filename):
        # The constructor validates the fixed vendor allow-list before path use.
        return os.path.join(
            settings.PROJECT_DIR,
            "apps", "authentication", "backends", "ukey", "vendors",
            self.snapshot['AUTH_UKEY_VENDOR'], filename,
        )

    def get_sdk_script_path(self):
        return self._vendor_path('sdk_script.js')

    def get_sdk_config_path(self):
        return self._vendor_path('sdk_config.yaml')

    def load_sdk_script_content(self):
        """返回 SDK JS 文件内容，按 vendor 缓存，vendor 变更或服务重启后自动失效。"""
        vendor = self.snapshot['AUTH_UKEY_VENDOR']
        cache = self._sdk_script_cache
        if vendor not in cache or settings.DEBUG_DEV:
            js_path = self.get_sdk_script_path()
            if not js_path or not os.path.isfile(js_path):
                return None
            with open(js_path, 'rb') as f:
                cache[vendor] = f.read()
        if vendor == 'long_mai' and self.provider.binding_mode == 'certificate':
            with open(self._vendor_path('xjca_adapter.js'), 'rb') as adapter:
                return cache[vendor] + b'\n' + adapter.read()
        return cache[vendor]

    def load_sdk_config_content(self):
        """返回原始 YAML 配置数据，按 vendor 缓存，vendor 变更或服务重启后自动失效。"""
        vendor = self.snapshot['AUTH_UKEY_VENDOR']
        cache = self._sdk_config_cache
        if vendor not in cache or settings.DEBUG_DEV:
            cf_path = self.get_sdk_config_path()
            if not cf_path or not os.path.isfile(cf_path):
                return {}
            cache[vendor] = self._load_yaml(cf_path)
        return cache[vendor]

    @staticmethod
    def _load_yaml(config_file):
        if not config_file or not os.path.isfile(config_file):
            logger.warning('UKeySDKConfig: config file not found: %s', config_file)
            return {}
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    @property
    def ca_cert_asym_alg(self):
        # 从 CA 证书内容解析出签名算法类型，返回 'RSA' 或 'SM2' 等字符串，供 YAML 配置中使用
        return self.provider.ca_algorithm

    # ── 认证流程 ──────────────────────────────────────────────────────────────

    @property
    def challenge_ttl(self):
        """Challenge 码在 Redis 中的存活时间（秒），默认 300。"""
        v = self.snapshot.get('AUTH_UKEY_CHALLENGE_TTL', 300)
        return int(v)

    # ── 证书签发 ──────────────────────────────────────────────────────────────

    @property
    def enroll_enabled(self):
        """是否开启用户证书签发功能。"""
        snapshot = self.snapshot
        return self.provider.supports_enrollment and bool(snapshot['AUTH_UKEY_ENROLL_ENABLED'])

    @property
    def enroll_validity_days(self):
        """签发证书的有效期（天），默认 365。"""
        v = self.snapshot.get('AUTH_UKEY_ENROLL_VALIDITY_DAYS', 365)
        return int(v)
    
    @property
    def default_pin(self):
        """证书默认 PIN 码，默认为空字符串（不设置 PIN）。"""
        v = self.snapshot.get('AUTH_UKEY_DEFAULT_PIN', '')
        return str(v)

    # ── 厂商 SDK 映射（原始数据，供 API 层序列化给前端）───────────────────────
        
    @staticmethod
    def _render(sdk_config, trans_filter=None):
        """
        只处理 YAML 数据中的 i18n 翻译标记，不做模板变量替换。
          - {{ 'text' | trans }} → 按 trans_filter 翻译；不传则原文返回
        """
        import re
        _filter = trans_filter or (lambda s: s)
        _pattern = re.compile(r"""\{\{\s*(['"])(.+?)\1\s*\|\s*trans\s*\}\}""")

        def _translate(s):
            return _pattern.sub(lambda m: _filter(m.group(2)), s)

        def _walk(obj):
            if isinstance(obj, dict):
                return {k: _walk(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_walk(item) for item in obj]
            if isinstance(obj, str):
                return _translate(obj)
            return obj

        return _walk(sdk_config)

    def _build_trans_filter(self, sdk_config, lang):
        """构建 Jinja2 | trans filter 函数，按 lang 从 YAML i18n 表查找翻译。
        未找到翻译时原文返回；语言键自动归一化（zh_hant → zh-hant）。
        """
        lang = Language.to_internal_code(lang)
        i18n_raw = sdk_config.get('i18n') or {}
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
            return translations.get(lang) or s

        return trans_filter


    def get_sdk_config(self, lang='en', include_admin_pin=False):
        """返回去掉 'i18n' 顶层 key 后的厂商 SDK 方法映射。
        YAML 中任意字符串值均可用 {{ 'text' | trans }} 语法标记为可翻译。
        """
        sdk_config = deepcopy(self.load_sdk_config_content())
        provider = self.provider
        if provider.sdk_profile:
            self._apply_provider_config(sdk_config, provider.sdk_profile)
        trans_filter = self._build_trans_filter(sdk_config, lang)
        sdk_config = self._render(sdk_config, trans_filter)
        sdk_config = self._apply_internal_config_to_sdk_config(sdk_config)
        if not include_admin_pin or not provider.expose_default_pin:
            sdk_config['config'].pop('pin', None)
        sdk_config.pop('i18n', None)
        return sdk_config

    def _apply_provider_config(self, sdk_config, profile):
        """应用 CA Provider 的差异区段，复用原厂商初始化与信息展示配置。"""
        override = self._load_yaml(self._vendor_path(profile))
        sdk_config['sdk']['create'].update(override['sdk']['create'])
        replacements = {step['name']: step for step in override['sdk']['setup']['steps']}
        sdk_config['sdk']['setup']['steps'] = [
            replacements.get(step.get('name'), step) for step in sdk_config['sdk']['setup']['steps']
        ]
        sdk_config['info']['when'] = override['info']['when']
        fields = {field['key']: field for field in override['info']['device']}
        for field in sdk_config['info']['device']:
            field.update(fields.get(field['key'], {}))
        # 外部证书不以 CN 映射用户名，证书字段只用于展示。
        if self.provider.binding_mode == 'certificate':
            for field in sdk_config['info']['cert']['fields']:
                field.pop('compare', None)
        for section in ('login', 'operations'):
            sdk_config[section] = override[section]
        sdk_config.setdefault('i18n', {}).update(override['i18n'])
    
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

    def _apply_internal_config_to_sdk_config(self, sdk_config):
        """将 'config' 配置段渲染后添加到 data['config']，供前端 API 层使用。
        
        YAML config 中值为算法分支字典（含 SM2/RSA-1024/RSA-2048/default 等 key）的字段，
        会自动根据 CA 证书算法类型解析为对应的标量值，无需在此处逐字段枚举。
        """
        config = sdk_config.get('config') or {}
        asym_alg_name = self.ca_cert_asym_alg

        # 自动展开所有算法分支字典字段
        resolved_config = {}
        for k, v in config.items():
            if self._is_algo_branch(v):
                resolved_config[k] = self._resolve_algo_branch(v, asym_alg_name)
            else:
                resolved_config[k] = v

        # 追加后端专有字段（不在 YAML config 中配置）
        script_url = reverse('api-auth:ukey:ukey-sdk-script')
        if self.provider.binding_mode == 'certificate':
            script_url += '?' + urlencode({
                'vendor': self.snapshot['AUTH_UKEY_VENDOR'], 'revision': self.snapshot[REVISION],
            })
        resolved_config.update({
            'provider': self.snapshot['AUTH_UKEY_CA_PROVIDER'],
            'vendor': self.snapshot['AUTH_UKEY_VENDOR'],
            'capabilities': self.provider.capabilities,
            'revision': self.snapshot[REVISION],
            'asym_alg_name': asym_alg_name,
            'challenge_ttl': self.challenge_ttl,
            'enroll': {
                'enabled': self.enroll_enabled,
                'validity_days': self.enroll_validity_days,
            },
            'pin': {
                'default': self.default_pin,
            },
            'api': {
                'ukey_sdk_script_url': script_url,
                'enroll_cert_url': reverse('api-auth:ukey:ukey-enroll-cert'),
                'user_detail_url': reverse('users:user-list') + '{user_id}/',
            },
            'api_body': {
                'enroll_cert_url': ['user_id', 'csr'],
                'user_detail_url': ['ukey_sn']
            },
            'api_method': {
                'ukey_sdk_script_url': ['GET'],
                'enroll_cert_url': ['POST'],
                'user_detail_url': ['PATCH'],
            }

        })
        if self.provider.binding_mode == 'certificate':
            base = reverse('api-auth:ukey:ukey-sdk-config').rsplit('ukey-sdk-config/', 1)[0]
            resolved_config['api'] = {
                'ukey_sdk_script_url': script_url,
                'certificate_binding_url': base + 'certificate-binding/{user_id}/',
            }
            resolved_config['api_body'] = {'certificate_binding_url': [
                'action', 'revision', 'challenge_id', 'cert', 'signature', 'hardware_serial', 'binding_version',
            ]}
            resolved_config['api_method'] = {'certificate_binding_url': ['GET', 'POST']}
        sdk_config['config'] = resolved_config
        if not settings.DEBUG_DEV:
            sdk_config.pop('meta', None)
        return sdk_config
