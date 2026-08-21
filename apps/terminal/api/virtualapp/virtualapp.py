import os.path
import shutil
from typing import Callable

from django.core.files.storage import default_storage
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from common.api import JMSBulkModelViewSet
from common.serializers import FileSerializer
from terminal import serializers
from terminal.models import VirtualAppPublication, VirtualApp
from common.utils.zip import safe_extract_zip

__all__ = ['VirtualAppViewSet', 'VirtualAppPublicationViewSet']


class UploadMixin:
    get_serializer: Callable
    request: Request
    get_object: Callable

    @staticmethod
    def cleanup_tmp_files(rel_path, extract_to):
        if rel_path and default_storage.exists(rel_path):
            default_storage.delete(rel_path)
        if extract_to and os.path.exists(extract_to):
            shutil.rmtree(extract_to)

    def extract_zip_pkg(self):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data['file']
        save_to = 'virtual_apps/{}'.format(file.name + '.tmp.zip')
        if default_storage.exists(save_to):
            default_storage.delete(save_to)
        rel_path = default_storage.save(save_to, file)
        path = default_storage.path(rel_path)
        extract_to = default_storage.path('virtual_apps/{}.tmp'.format(file.name))
        if os.path.exists(extract_to):
            shutil.rmtree(extract_to)
        try:
            safe_extract_zip(path, extract_to)
        except RuntimeError as e:
            raise ValidationError({'error': _('Invalid zip file') + ': {}'.format(e)})
        tmp_dir = VirtualApp.locate_pkg_root(extract_to, file.name)
        return tmp_dir, rel_path, extract_to

    @action(detail=False, methods=['post'], serializer_class=FileSerializer)
    def upload(self, request, *args, **kwargs):
        rel_path = None
        extract_to = None
        try:
            tmp_dir, rel_path, extract_to = self.extract_zip_pkg()
            manifest = VirtualApp.validate_pkg(tmp_dir)
            name = manifest['name']
            instance = VirtualApp.objects.filter(name=name).first()
            if instance:
                return Response({'error': 'virtual app already exists: {}'.format(name)}, status=400)

            app, serializer = VirtualApp.install_from_dir(tmp_dir)
            return Response(serializer.data, status=201)
        finally:
            self.cleanup_tmp_files(rel_path, extract_to)


class VirtualAppViewSet(UploadMixin, JMSBulkModelViewSet):
    queryset = VirtualApp.objects.all()
    serializer_class = serializers.VirtualAppSerializer
    filterset_fields = ['name', 'is_active']
    search_fields = ['name', 'image_name', 'display_name']
    rbac_perms = {
        'upload': 'terminal.add_virtualapp',
    }


class VirtualAppPublicationViewSet(viewsets.ModelViewSet):
    queryset = VirtualAppPublication.objects.all()
    serializer_class = serializers.VirtualAppPublicationSerializer
    filterset_fields = ['app__name', 'provider__name', 'status']
    search_fields = ['app__name', 'provider__name', ]
