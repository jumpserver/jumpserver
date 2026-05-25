import os
import yaml
import json
from django.conf import settings
from common.utils import get_logger
from common.decorators import Singleton
from common.const import Language


logger = get_logger(__name__)

class Setting:
    VENDOR = getattr(settings, 'VENDOR', '')


@Singleton
class CertVendorDriverConfig:
    """
    从 YAML 配置文件读取所有证书相关配置。

    CA 相关路径/密码（ca_cert_file / ca_key_file / ca_key_pass）属于系统敏感配置，
    只能在系统设置（config.yml / Django settings）中配置，不允许写入此 YAML。

    YAML 结构约定：
      cert:                           # 系统级配置段
        gmssl_bin:    gmssl           # gmssl 二进制路径
        challenge_ttl: 300            # Challenge 码 Redis 存活秒数
        enroll:
          enabled:    true            # 是否开启证书签发
          key_algo:   SM2             # 签发密钥算法：SM2 或 RSA
          subject_cn: username              # 用户证书 Subject CN 取自用户的哪个字段
          subject_o:  JumpServer      # 用户证书 Subject O（组织名）
      # 其余 key 为厂商 SDK 方法映射（供前端 API 层使用）
      newUKeyAPI: ...
      checkInstall: ...
      getCertCN: ...
      ...
    """

    def __init__(self):
        if not settings.AUTH_CERT:
            logger.debug('CertVendorDriverConfig: authentication backend not enabled, skipping config load')
            return
        config_file = getattr(settings, 'AUTH_CERT_VENDOR_DRIVER_CONFIG_FILE', None)
        self._raw = self._load_yaml(config_file)
        self._cert = self._raw.get('cert') or {}
        self._enroll = self._cert.get('enroll') or {}

    # ── YAML 加载 ────────────────────────────────────────────────────────────

    @staticmethod
    def _load_yaml(config_file):
        if not config_file or not os.path.isfile(config_file):
            logger.warning('CertVendorDriverConfig: config file not found: %s', config_file)
            return {}
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    # ── CA / 证书链（只读系统设置，不允许在 YAML 中配置）────────────────────────

    @property
    def ca_cert_file(self):
        """CA 根证书路径，只从系统设置读取。"""
        return getattr(settings, 'CA_CERT_FILE', None)

    @property
    def ca_key_file(self):
        """CA 私钥路径，只从系统设置读取。"""
        return getattr(settings, 'CA_KEY_FILE', None)

    @property
    def ca_key_pass(self):
        """CA 私钥密码，只从系统设置读取。"""
        return getattr(settings, 'CA_KEY_PASS', '')

    @property
    def driver_js_file(self):
        """返回厂商 SDK 驱动文件的 FileResponse，供 API 层使用。"""
        return getattr(settings, 'AUTH_CERT_VENDOR_DRIVER_JS_FILE', None)

    # ── 工具 ─────────────────────────────────────────────────────────────────

    @property
    def gmssl_bin(self):
        """gmssl 二进制路径，默认 'gmssl'（系统 PATH 中查找）。"""
        return 'gmssl'

    # ── 认证流程 ──────────────────────────────────────────────────────────────

    @property
    def challenge_ttl(self):
        """Challenge 码在 Redis 中的存活时间（秒），默认 300。"""
        v = self._cert.get('challenge_ttl', 300)
        return int(v)

    # ── 证书签发 ──────────────────────────────────────────────────────────────

    @property
    def enroll_enabled(self):
        """是否开启用户证书签发功能。"""
        v = self._enroll.get('enabled', True)
        return bool(v)

    @property
    def enroll_key_algo(self):
        """签发证书时生成密钥对的算法，SM2 或 RSA。"""
        return self._enroll.get('key_algo', 'SM2')

    @property
    def enroll_subject_cn(self):
        """用户证书 Subject CN 取自用户模型的哪个字段，默认 'username'。"""
        return self._enroll.get('subject_cn', 'username')

    @property
    def enroll_subject_o(self):
        """用户证书 Subject O（组织名）。"""
        return self._enroll.get('subject_o', Setting.VENDOR)
    
    @property
    def enroll_validity_days(self):
        """签发证书的有效期（天），默认 365。"""
        v = self._enroll.get('validity_days', 365)
        return int(v)

    # ── 厂商 SDK 映射（原始数据，供 API 层序列化给前端）───────────────────────
        
    @staticmethod
    def _render(data, trans_filter=None):
        """
        渲染 YAML 数据中的 Jinja2 模板表达式。
          - {{ settings.xxx }}  → 系统设置值（任何时候都生效）
          - {{ user.xxx }}      → 原样保留，留给前端 JS 运行时解析
          - {{ 'text' | trans }} → 按 trans_filter 翻译；不传则原文返回（初始化阶段）
        """
        from jinja2 import Undefined, Environment

        class KeepUndefined(Undefined):
            """未定义变量原样保留占位符，支持任意深度的属性链。"""
            def __str__(self):
                return '{{ ' + self._undefined_name + ' }}'
            def __getattr__(self, name):
                return KeepUndefined(name=f'{self._undefined_name}.{name}')

        template_str = json.dumps(data, ensure_ascii=False)
        env = Environment(undefined=KeepUndefined)
        env.filters['trans'] = trans_filter or (lambda s: s)
        rendered = env.from_string(template_str).render(settings=Setting)
        return json.loads(rendered)

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
        return {k: v for k, v in data.items() if k not in ('i18n',)}


cert_vd_cfg = CertVendorDriverConfig()
