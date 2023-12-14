import os.path
import shutil
import zipfile
from typing import Callable

from django.core.files.storage import default_storage
from django.utils._os import safe_join
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

__all__ = ['VirtualAppViewSet', 'VirtualAppPublicationViewSet']


class UploadMixin:
    get_serializer: Callable
    request: Request
    get_object: Callable

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
            with zipfile.ZipFile(path) as zp:
                if zp.testzip() is not None:
                    raise ValidationError({'error': _('Invalid zip file')})
                zp.extractall(extract_to)
        except RuntimeError as e:
            raise ValidationError({'error': _('Invalid zip file') + ': {}'.format(e)})
        tmp_dir = safe_join(extract_to, file.name.replace('.zip', ''))
        return tmp_dir

    @action(detail=False, methods=['post'], serializer_class=FileSerializer)
    def upload(self, request, *args, **kwargs):
        tmp_dir = self.extract_zip_pkg()
        manifest = VirtualApp.validate_pkg(tmp_dir)
        name = manifest['name']
        instance = VirtualApp.objects.filter(name=name).first()
        if instance:
            return Response({'error': 'virtual app already exists: {}'.format(name)}, status=400)

        app, serializer = VirtualApp.install_from_dir(tmp_dir)
        return Response(serializer.data, status=201)


class VirtualAppViewSet(UploadMixin, JMSBulkModelViewSet):
    queryset = VirtualApp.objects.all()
    serializer_class = serializers.VirtualAppSerializer
    filterset_fields = ['name', 'is_active']
    search_fields = ['name', 'image_name']
    rbac_perms = {
        'upload': 'terminal.add_virtualapp',
    }


class VirtualAppPublicationViewSet(viewsets.ModelViewSet):
    queryset = VirtualAppPublication.objects.all()
    serializer_class = serializers.VirtualAppPublicationSerializer
    filterset_fields = ['app__name', 'provider__name', 'status']
    search_fields = ['app__name', 'provider__name', ]
