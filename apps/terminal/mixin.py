import os

from django.utils.translation import get_language

from common.utils.yml import yaml_load_with_i18n
from terminal.utils.loki_client import get_loki_client

__all__ = ['LokiMixin', ]


class LokiMixin:

    @staticmethod
    def get_loki_client():
        return get_loki_client()

    @staticmethod
    def create_loki_query(components, search):
        stream_selector = '{component!=""}'
        if components:
            stream_selector = '{component=~"%s"}' % components
        query = f'{stream_selector} |="{search}"'
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
