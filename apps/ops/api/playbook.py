import os
import shutil
import zipfile

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import status

from common.exceptions import JMSException
from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission
from ..exception import PlaybookNoValidEntry
from ..models import Playbook
from ..serializers.playbook import PlaybookSerializer

__all__ = ["PlaybookViewSet", "PlaybookFileBrowserAPIView"]

from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils._os import safe_join


def unzip_playbook(src, dist):
    fz = zipfile.ZipFile(src, 'r')
    for file in fz.namelist():
        fz.extract(file, dist)


class PlaybookViewSet(OrgBulkModelViewSet):
    serializer_class = PlaybookSerializer
    permission_classes = (RBACPermission,)
    model = Playbook
    search_fields = ('name', 'comment')

    def perform_destroy(self, instance):
        if instance.job_set.exists():
            raise JMSException(code='playbook_has_job', detail={"msg": _("Currently playbook is being used in a job")})
        instance_id = instance.id
        super().perform_destroy(instance)
        dest_path = safe_join(settings.DATA_DIR, "ops", "playbook", instance_id.__str__())
        shutil.rmtree(dest_path)

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(creator=self.request.user)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        if 'multipart/form-data' in self.request.headers['Content-Type']:
            src_path = safe_join(settings.MEDIA_ROOT, instance.path.name)
            dest_path = safe_join(settings.DATA_DIR, "ops", "playbook", instance.id.__str__())
            try:
                unzip_playbook(src_path, dest_path)
            except RuntimeError as e:
                raise JMSException(code='invalid_playbook_file', detail={"msg": "Unzip failed"})

            if 'main.yml' not in os.listdir(dest_path):
                raise PlaybookNoValidEntry

        else:
            if instance.create_method == 'blank':
                dest_path = safe_join(settings.DATA_DIR, "ops", "playbook", instance.id.__str__())
                os.makedirs(dest_path)
                with open(safe_join(dest_path, 'main.yml'), 'w') as f:
                    f.write('## write your playbook here')


class PlaybookFileBrowserAPIView(APIView):
    rbac_perms = ()
    permission_classes = (RBACPermission,)
    rbac_perms = {
        'GET': 'ops.change_playbook',
        'POST': 'ops.change_playbook',
        'DELETE': 'ops.change_playbook',
        'PATCH': 'ops.change_playbook',
    }
    protected_files = ['root', 'main.yml']

    def get_playbook(self, playbook_id):
        playbook = get_object_or_404(Playbook, id=playbook_id, creator=self.request.user)
        return playbook

    def get(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        playbook = self.get_playbook(playbook_id)
        work_path = playbook.work_dir
        file_key = request.query_params.get('key', '')
        if file_key:
            try:
                file_path = safe_join(work_path, file_key)
                with open(file_path, 'r') as f:
                    content = f.read()
            except UnicodeDecodeError:
                content = _('Unsupported file content')
            except SuspiciousFileOperation:
                raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})
            return Response({'content': content})
        else:
            expand_key = request.query_params.get('expand', '')
            nodes = self.generate_tree(playbook, work_path, expand_key)
            return Response(nodes)

    def post(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        playbook = self.get_playbook(playbook_id)
        work_path = playbook.work_dir

        parent_key = request.data.get('key', '')
        if parent_key == 'root':
            parent_key = ''
        if os.path.dirname(parent_key) == 'root':
            parent_key = os.path.basename(parent_key)

        full_path = safe_join(work_path, parent_key)

        is_directory = request.data.get('is_directory', False)
        content = request.data.get('content', '')
        name = request.data.get('name', '')

        def find_new_name(p, is_file=False):
            if not p:
                if is_file:
                    p = 'new_file.yml'
                else:
                    p = 'new_dir'
            np = safe_join(full_path, p)
            n = 0
            while os.path.exists(np):
                n += 1
                np = safe_join(full_path, '{}({})'.format(p, n))
            return np

        try:
            if is_directory:
                new_file_path = find_new_name(name)
                os.makedirs(new_file_path)
            else:
                new_file_path = find_new_name(name, True)
                with open(new_file_path, 'w') as f:
                    f.write(content)
        except SuspiciousFileOperation:
            raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})

        relative_path = os.path.relpath(os.path.dirname(new_file_path), work_path)
        new_node = {
            "name": os.path.basename(new_file_path),
            "title": os.path.basename(new_file_path),
            "id": safe_join(relative_path, os.path.basename(new_file_path))
            if not safe_join(relative_path, os.path.basename(new_file_path)).startswith('.')
            else os.path.basename(new_file_path),
            "isParent": is_directory,
            "pId": relative_path if not relative_path.startswith('.') else 'root',
            "open": True,
        }
        if not is_directory:
            new_node['iconSkin'] = 'file'
        return Response(new_node)

    def patch(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        playbook = self.get_playbook(playbook_id)
        work_path = playbook.work_dir

        file_key = request.data.get('key', '')
        new_name = request.data.get('new_name', '')

        if file_key in self.protected_files and new_name:
            raise JMSException(code='this_file_can_not_be_rename', detail={"msg": _("This file can not be rename")})

        if os.path.dirname(file_key) == 'root':
            file_key = os.path.basename(file_key)

        content = request.data.get('content', '')
        is_directory = request.data.get('is_directory', False)

        if not file_key or file_key == 'root':
            return Response(status=status.HTTP_400_BAD_REQUEST)
        file_path = safe_join(work_path, file_key)

        # rename
        if new_name:
            try:
                new_file_path = safe_join(os.path.dirname(file_path), new_name)
                if new_file_path == file_path:
                    return Response(status=status.HTTP_200_OK)
                if os.path.exists(new_file_path):
                    raise JMSException(code='file_already exists', detail={"msg": _("File already exists")})
                os.rename(file_path, new_file_path)
            except SuspiciousFileOperation:
                raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})

        # edit content
        else:
            if not is_directory:
                with open(file_path, 'w') as f:
                    f.write(content)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        playbook = self.get_playbook(playbook_id)
        work_path = playbook.work_dir
        file_key = request.query_params.get('key', '')
        if not file_key:
            raise JMSException(code='file_key_is_required', detail={"msg": _("File key is required")})

        if file_key in self.protected_files:
            raise JMSException(code='This file can not be delete', detail={"msg": _("This file can not be delete")})
        file_path = safe_join(work_path, file_key)
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)
        return Response({'msg': 'ok'})

    @staticmethod
    def generate_tree(playbook, root_path, expand_key=None):
        nodes = [{
            "name": playbook.name,
            "title": playbook.name,
            "id": 'root',
            "isParent": True,
            "open": True,
            "pId": '',
            "temp": False
        }]
        for path, dirs, files in os.walk(root_path):
            dirs.sort()
            files.sort()

            relative_path = os.path.relpath(path, root_path)
            for d in dirs:
                dir_id = os.path.relpath(safe_join(path, d), root_path)

                node = {
                    "name": d,
                    "title": d,
                    "id": dir_id,
                    "isParent": True,
                    "open": True,
                    "pId": relative_path if not relative_path.startswith('.') else 'root',
                    "temp": False
                }
                if expand_key == node['id']:
                    node['open'] = True
                nodes.append(node)
            for f in files:
                file_id = os.path.relpath(safe_join(path, f), root_path)
                node = {
                    "name": f,
                    "title": f,
                    "iconSkin": 'file',
                    "id": file_id,
                    "isParent": False,
                    "open": False,
                    "pId": relative_path if not relative_path.startswith('.') else 'root',
                    "temp": False
                }
                nodes.append(node)
        return nodes
