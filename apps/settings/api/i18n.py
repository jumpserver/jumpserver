import json
import os

from django.conf import settings
from django.utils._os import safe_join
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class ComponentI18nApi(RetrieveAPIView):
    base_path = 'locale'
    permission_classes = [AllowAny]
    lang_data = {}

    def get_component_translations(self, name):
        if name in self.lang_data:
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
            _lang = file.split('.')[0]
            with open(safe_join(component_dir, file), 'r') as f:
                data[_lang] = json.load(f)
        self.lang_data[name] = data
        return data

    def retrieve(self, request, *args, **kwargs):
        name = kwargs.get('name')
        lang = request.query_params.get('lang')
        data = self.get_component_translations(name)

        if lang:
            data = data.get(lang) or {}
            flat = request.query_params.get('flat', '1')
            if flat == '0':
                data = {lang: data}
        return Response(data)
