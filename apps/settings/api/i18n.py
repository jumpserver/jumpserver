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

    def get_path(self):
        pass

    def head(self, request, *args, **kwargs):
        return Response()

    def retrieve(self, request, *args, **kwargs):
        name = kwargs.get('name')
        component_dir = safe_join(settings.APPS_DIR, 'locale', name)
        lang = request.query_params.get('lang')
        files = os.listdir(component_dir)
        data = {}
        for file in files:
            if not file.endswith('.json'):
                continue
            _lang = file.split('.')[0]
            with open(safe_join(component_dir, file), 'r') as f:
                data[_lang] = json.load(f)
        if lang:
            data = {lang: data.get(lang) or {}}
        return Response(data)
