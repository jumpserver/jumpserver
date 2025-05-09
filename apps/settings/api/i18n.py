import json
import os

from django.conf import settings
from django.utils._os import safe_join
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from common.const.choices import Language


class ComponentI18nApi(RetrieveAPIView):
    base_path = 'locale'
    permission_classes = [AllowAny]
    lang_data = {}

    def get_component_translations(self, name):
        if not settings.DEBUG and name in self.lang_data:
            return self.lang_data[name]

        component_dir = safe_join(settings.APPS_DIR, 'i18n', name)
        if os.path.exists(component_dir):
            files = os.listdir(component_dir)
        else:
            files = []
        data = {}
        for file in files:
            if not file.endswith('.json'):
                continue
            lang = file.split('.')[0]
            with open(safe_join(component_dir, file), 'r') as f:
                data[lang] = json.load(f)
        self.lang_data[name] = data
        return data

    def retrieve(self, request, *args, **kwargs):
        name = kwargs.get('name')
        lang = request.query_params.get('lang')
        flat = request.query_params.get('flat', '1')
        data = self.get_component_translations(name)

        if not lang:
            return Response(data)

        if lang not in dict(Language.get_code_mapper()).keys():
            lang = 'en'

        code = Language.to_internal_code(lang, with_filename=True)
        data = data.get(code) or {}
        if flat == '0':
            # 这里要使用原始的 lang, lina 会 merge
            data = {lang: data}
        return Response(data)
