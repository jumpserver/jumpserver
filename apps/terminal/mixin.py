import os
import re

from django.utils.translation import get_language

from common.utils.yml import yaml_load_with_i18n
from terminal.utils.loki_client import get_loki_client

__all__ = ['LokiMixin', ]


class LokiMixin:

    @staticmethod
    def get_loki_client():
        return get_loki_client()

    @staticmethod
    def _escape_loki_regex(value):
        # 转义 \ " { } | = ~ ! 等 LogQL stream selector 特殊字符
        return re.sub(r'([\\"{}\[\]|=~!()])', r"\\\1", str(value))

    @staticmethod
    def _escape_loki_filter(value):
        # 转义 line filter 中的 \ 和 " 防止逃逸
        return str(value).replace("\\", "\\\\").replace('"', '\\"')

    @classmethod
    def create_loki_query(cls, components, search):
        stream_selector = '{component!=""}'
        if components:
            escaped = cls._escape_loki_regex(components)
            stream_selector = '{component=~"%s"}' % escaped
        escaped_search = cls._escape_loki_filter(search)
        query = f'{stream_selector} |="{escaped_search}"'
        return query


class ManifestI18nMixin:
    @staticmethod
    def read_manifest_with_i18n(obj, lang='zh'):
        path = os.path.join(obj.path, 'manifest.yml')
        if os.path.exists(path):
            with open(path, encoding='utf8') as f:
                manifest = yaml_load_with_i18n(f, lang)
        else:
            manifest = {}
        return manifest

    @staticmethod
    def readme(obj, lang=''):
        lang = lang[:2]
        readme_file = os.path.join(obj.path, f'README_{lang.upper()}.md')
        if os.path.isfile(readme_file):
            with open(readme_file, 'r') as f:
                return f.read()
        return ''

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = get_language()
        manifest = self.read_manifest_with_i18n(instance, lang)
        data['display_name'] = manifest.get('display_name', getattr(instance, 'display_name', ''))
        data['comment'] = manifest.get('comment', getattr(instance, 'comment', ''))
        data['readme'] = self.readme(instance, lang)
        return data
