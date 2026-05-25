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
            self._raw = {}
            self._data = {}
            self._cert = {}
            self._enroll = {}
            logger.debug('CertVendorDriverConfig: authentication backend not enabled, skipping config load')
            return
        config_file = getattr(settings, 'AUTH_CERT_VENDOR_DRIVER_CONFIG_FILE', None)
        self._raw = self._load_yaml(config_file)
        self._data = self._render_template(self._raw)
        self._cert = self._data.get('cert') or {}
        self._enroll = self._cert.get('enroll') or {}

    # ── YAML 加载 ────────────────────────────────────────────────────────────

    @staticmethod
    def _load_yaml(config_file):
        if not config_file or not os.path.isfile(config_file):
            logger.warning('CertVendorDriverConfig: config file not found: %s', config_file)
            return {}
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    @staticmethod
    def _render_template(data):
        """
        使用系统设置渲染字符串模板，支持在 YAML 中引用系统设置。
        找不到的变量（如 {{ user.username }}）原样保留，不替换为空，不报错。
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
        rendered = env.from_string(template_str).render(settings=Setting)
        return json.loads(rendered)

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

    def get_vendor_sdk_data(self, lang='en'):
        """返回去掉 'cert' 顶层 key 后的全部数据，即厂商 SDK 方法映射。
        根据 lang 参数将 label / description 字段替换为对应语言的翻译。
        """
        lang = Language.to_internal_code(lang)
        i18n = self._data.get('i18n') or {}
        data = self._apply_i18n(self._data, i18n, lang)
        data = {k: v for k, v in data.items() if k != 'i18n'}
        return data

    @classmethod
    def _apply_i18n(cls, node, i18n, lang):
        """递归遍历数据，将 label / description 的值按 i18n 表翻译。"""
        if isinstance(node, dict):
            result = {}
            for k, v in node.items():
                if k in ('label', 'description') and isinstance(v, str):
                    translations = i18n.get(v)
                    if translations and isinstance(translations, dict):
                        v = translations.get(lang) or v
                result[k] = cls._apply_i18n(v, i18n, lang)
            return result
        if isinstance(node, list):
            return [cls._apply_i18n(item, i18n, lang) for item in node]
        return node


cert_vd_cfg = CertVendorDriverConfig()
