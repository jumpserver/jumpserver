import os.path
import shutil
from typing import Callable

from django.core.files.storage import default_storage
from django.db import transaction
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from common.api import JMSBulkModelViewSet
from common.serializers import FileSerializer
from terminal import serializers
from terminal.models import VirtualAppPublication, VirtualApp, AppProviderDeployment
from terminal.tasks import run_app_provider_deployment
from terminal.utils.virtualapp import (
    MAX_IMAGE_SIZE, delete_image_archive, get_image_archives, save_image_archive,
)
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
        'images': 'terminal.view_virtualapp',
        'upload_image': 'terminal.change_virtualapp',
        'delete_image': 'terminal.change_virtualapp',
    }

    @staticmethod
    def image_response(app, status=200):
        fields = ('filename', 'size', 'version', 'image_name', 'os', 'architecture')
        images = [
            {field: archive[field] for field in fields}
            for archive in get_image_archives(app)
        ]
        return Response({'images': images, 'max_size': MAX_IMAGE_SIZE}, status=status)

    @action(detail=True, methods=['get'], serializer_class=FileSerializer, parser_classes=[MultiPartParser])
    def images(self, request, *args, **kwargs):
        return self.image_response(self.get_object())

    @images.mapping.post
    def upload_image(self, request, *args, **kwargs):
        app = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        save_image_archive(app, serializer.validated_data['file'])
        return self.image_response(app, status=201)

    @images.mapping.delete
    def delete_image(self, request, *args, **kwargs):
        app = self.get_object()
        architecture = request.query_params.get('architecture')
        if not architecture:
            raise ValidationError({'architecture': _('Image architecture is required')})
        delete_image_archive(app, architecture)
        return self.image_response(app)


class VirtualAppPublicationViewSet(viewsets.ModelViewSet):
    queryset = VirtualAppPublication.objects.select_related('provider__host', 'app')
    serializer_class = serializers.VirtualAppPublicationSerializer
    filterset_fields = ['app', 'app__name', 'provider', 'provider__name', 'status']
    search_fields = ['app__name', 'provider__name', ]
    rbac_perms = {
        'publish': 'terminal.change_virtualapppublication',
    }

    @staticmethod
    def start_publish(publication):
        if not publication.provider.host_id:
            return None
        deployment = AppProviderDeployment.objects.create(
            provider=publication.provider,
            publication=publication,
        )
        deployment.save_task(deployment.id)
        transaction.on_commit(
            lambda: run_app_provider_deployment.apply_async(
                (deployment.id,), task_id=str(deployment.id)
            )
        )
        return deployment

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        publication = serializer.save(status='pending')
        deployment = self.start_publish(publication)
        data = serializer.data
        data['task'] = str(deployment.id) if deployment else None
        return Response(data, status=201)

    @action(detail=True, methods=['post'])
    def publish(self, request, *args, **kwargs):
        publication = self.get_object()
        publication.status = 'pending'
        publication.app_version = ''
        publication.save(update_fields=['status', 'app_version', 'date_updated'])
        deployment = self.start_publish(publication)
        return Response({'task': str(deployment.id) if deployment else None}, status=201)
