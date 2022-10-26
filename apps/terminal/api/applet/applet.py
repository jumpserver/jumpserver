import os.path
import shutil
import zipfile
import yaml

from django.core.files.storage import default_storage
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from terminal import serializers, models
from terminal.serializers import AppletUploadSerializer


class AppletViewSet(viewsets.ModelViewSet):
    queryset = models.Applet.objects.all()
    serializer_class = serializers.AppletSerializer
    rbac_perms = {
        'upload': 'terminal.add_applet',
    }

    def perform_destroy(self, instance):
        if not instance.name:
            raise ValidationError('Applet is not null')
        path = default_storage.path('applets/{}'.format(instance.name))
        if os.path.exists(path):
            shutil.rmtree(path)
        instance.delete()

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

        with zipfile.ZipFile(path) as zp:
            if zp.testzip() is not None:
                return Response({'msg': 'Invalid Zip file'}, status=400)
            zp.extractall(extract_to)

        tmp_dir = os.path.join(extract_to, file.name.replace('.zip', ''))
        files = ['manifest.yml', 'icon.png', 'i18n.yml']
        for name in files:
            path = os.path.join(tmp_dir, name)
            if not os.path.exists(path):
                raise ValidationError({'error': 'Missing file {}'.format(name)})

        with open(os.path.join(tmp_dir, 'manifest.yml')) as f:
            manifest = yaml.safe_load(f)

        if not manifest.get('name', ''):
            raise ValidationError({'error': 'Missing name in manifest.yml'})
        return manifest, tmp_dir

    @action(detail=False, methods=['post'], serializer_class=AppletUploadSerializer)
    def upload(self, request, *args, **kwargs):
        manifest, tmp_dir = self.extract_and_check_file(request)
        name = manifest['name']
        update = request.query_params.get('update')

        instance = models.Applet.objects.filter(name=name).first()
        if instance and not update:
            return Response({'error': 'Applet already exists: {}'.format(name)}, status=400)

        serializer = serializers.AppletSerializer(data=manifest, instance=instance)
        serializer.is_valid(raise_exception=True)
        save_to = default_storage.path('applets/{}'.format(name))
        if os.path.exists(save_to):
            shutil.rmtree(save_to)
        shutil.move(tmp_dir, save_to)
        serializer.save()
        return Response(serializer.data, status=201)


class AppletPublicationViewSet(viewsets.ModelViewSet):
    queryset = models.AppletPublication.objects.all()
    serializer_class = serializers.AppletPublicationSerializer
