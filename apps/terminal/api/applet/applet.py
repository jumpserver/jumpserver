import os.path
import shutil
import zipfile
from typing import Callable

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from common.api import JMSBulkModelViewSet
from common.serializers import FileSerializer
from common.utils import is_uuid
from terminal import serializers
from terminal.models import AppletPublication, Applet

__all__ = ['AppletViewSet', 'AppletPublicationViewSet']


class DownloadUploadMixin:
    get_serializer: Callable
    request: Request
    get_object: Callable

    def extract_and_check_file(self, request):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)

        file = serializer.validated_data['file']
        save_to = 'applets/{}'.format(file.name + '.tmp.zip')
        if default_storage.exists(save_to):
            default_storage.delete(save_to)
        rel_path = default_storage.save(save_to, file)
        path = default_storage.path(rel_path)
        extract_to = default_storage.path('applets/{}.tmp'.format(file.name))
        if os.path.exists(extract_to):
            shutil.rmtree(extract_to)

        try:
            with zipfile.ZipFile(path) as zp:
                if zp.testzip() is not None:
                    raise ValidationError({'error': _('Invalid zip file')})
                zp.extractall(extract_to)
        except RuntimeError as e:
            raise ValidationError({'error': _('Invalid zip file') + ': {}'.format(e)})

        tmp_dir = os.path.join(extract_to, file.name.replace('.zip', ''))
        manifest = Applet.validate_pkg(tmp_dir)
        return manifest, tmp_dir

    @action(detail=False, methods=['post'], serializer_class=FileSerializer)
    def upload(self, request, *args, **kwargs):
        manifest, tmp_dir = self.extract_and_check_file(request)
        name = manifest['name']
        update = request.query_params.get('update')

        is_enterprise = manifest.get('edition') == Applet.Edition.enterprise
        if is_enterprise and not settings.XPACK_LICENSE_IS_VALID:
            raise ValidationError({'error': _('This is enterprise edition applet')})

        instance = Applet.objects.filter(name=name).first()
        if instance and not update:
            return Response({'error': 'Applet already exists: {}'.format(name)}, status=400)

        applet, serializer = Applet.install_from_dir(tmp_dir, builtin=False)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=['get'])
    def download(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.builtin:
            path = os.path.join(settings.APPS_DIR, 'terminal', 'applets', instance.name)
        else:
            path = default_storage.path('applets/{}'.format(instance.name))
        zip_path = shutil.make_archive(path, 'zip', path)
        with open(zip_path, 'rb') as f:
            response = HttpResponse(f.read(), status=200, content_type='application/octet-stream')
            response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'{}.zip'.format(instance.name)
        os.unlink(zip_path)
        return response


class AppletViewSet(DownloadUploadMixin, JMSBulkModelViewSet):
    queryset = Applet.objects.all()
    serializer_class = serializers.AppletSerializer
    filterset_fields = ['name', 'version', 'builtin', 'is_active']
    search_fields = ['name', 'display_name', 'author']
    rbac_perms = {
        'upload': 'terminal.add_applet',
        'download': 'terminal.view_applet',
    }

    def get_object(self):
        pk = self.kwargs.get('pk')
        if not is_uuid(pk):
            return get_object_or_404(Applet, name=pk)
        else:
            return get_object_or_404(Applet, pk=pk)

    def perform_destroy(self, instance):
        if not instance.name:
            raise ValidationError('Applet is not null')
        path = default_storage.path('applets/{}'.format(instance.name))
        if os.path.exists(path):
            shutil.rmtree(path)
        instance.delete()


class AppletPublicationViewSet(viewsets.ModelViewSet):
    queryset = AppletPublication.objects.all()
    serializer_class = serializers.AppletPublicationSerializer
    filterset_fields = ['host', 'applet', 'status']
    search_fields = ['applet__name', 'applet__display_name', 'host__name']
