import os
import shutil
import zipfile

from django.conf import settings
from django.shortcuts import get_object_or_404

from orgs.mixins.api import OrgBulkModelViewSet
from ..exception import PlaybookNoValidEntry
from ..models import Playbook
from ..serializers.playbook import PlaybookSerializer

__all__ = ["PlaybookViewSet", "PlaybookFileBrowserAPIView"]

from rest_framework.views import APIView
from rest_framework.response import Response


def unzip_playbook(src, dist):
    fz = zipfile.ZipFile(src, 'r')
    for file in fz.namelist():
        fz.extract(file, dist)


class PlaybookViewSet(OrgBulkModelViewSet):
    serializer_class = PlaybookSerializer
    permission_classes = ()
    model = Playbook

    def allow_bulk_destroy(self, qs, filtered):
        return True

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(creator=self.request.user)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        if instance.create_method == 'blank':
            dest_path = os.path.join(settings.DATA_DIR, "ops", "playbook", instance.id.__str__())
            os.makedirs(dest_path)
            with open(os.path.join(dest_path, 'main.yml'), 'w') as f:
                f.write('## write your playbook here')

        if instance.create_method == 'upload':
            src_path = os.path.join(settings.MEDIA_ROOT, instance.path.name)
            dest_path = os.path.join(settings.DATA_DIR, "ops", "playbook", instance.id.__str__())
            unzip_playbook(src_path, dest_path)
            valid_entry = ('main.yml', 'main.yaml', 'main')
            for f in os.listdir(dest_path):
                if f in valid_entry:
                    return
            os.remove(dest_path)
            raise PlaybookNoValidEntry


class PlaybookFileBrowserAPIView(APIView):
    rbac_perms = ()
    permission_classes = ()

    def get(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        playbook = get_object_or_404(Playbook, id=playbook_id)
        work_path = playbook.work_dir
        file_key = request.query_params.get('key', '')
        if file_key:
            file_path = os.path.join(work_path, file_key)
            with open(file_path, 'r') as f:
                content = f.read()
                return Response({'content': content})
        else:
            expand_key = request.query_params.get('expand', '')
            nodes = self.generate_tree(playbook, work_path, expand_key)
            return Response(nodes)

    def post(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        playbook = get_object_or_404(Playbook, id=playbook_id)
        work_path = playbook.work_dir

        parent_key = request.data.get('key', '')
        if parent_key == 'root':
            parent_key = ''
        if os.path.dirname(parent_key) == 'root':
            parent_key = os.path.basename(parent_key)
        full_path = os.path.join(work_path, parent_key)

        is_directory = request.data.get('is_directory', False)
        content = request.data.get('content', '')

        if is_directory:
            new_file_path = os.path.join(full_path, 'new_dir')
            i = 0
            while os.path.exists(new_file_path):
                i += 1
                new_file_path = os.path.join(full_path, 'new_dir({})'.format(i))
            os.makedirs(new_file_path)
        else:
            new_file_path = os.path.join(full_path, 'new_file.yml')
            i = 0
            while os.path.exists(new_file_path):
                i += 1
                new_file_path = os.path.join(full_path, 'new_file({}).yml'.format(i))
            with open(new_file_path, 'w') as f:
                f.write(content)

        relative_path = os.path.relpath(os.path.dirname(new_file_path), work_path)
        new_node = {
            "name": os.path.basename(new_file_path),
            "title": os.path.basename(new_file_path),
            "id": os.path.join(relative_path, os.path.basename(new_file_path))
            if not os.path.join(relative_path, os.path.basename(new_file_path)).startswith('.')
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
        playbook = get_object_or_404(Playbook, id=playbook_id)
        work_path = playbook.work_dir

        file_key = request.data.get('key', '')
        if os.path.dirname(file_key) == 'root':
            file_key = os.path.basename(file_key)

        new_name = request.data.get('new_name', '')
        content = request.data.get('content', '')
        is_directory = request.data.get('is_directory', False)

        if not file_key or file_key == 'root':
            return Response(status=400)
        file_path = os.path.join(work_path, file_key)

        if new_name:
            new_file_path = os.path.join(os.path.dirname(file_path), new_name)
            os.rename(file_path, new_file_path)
            file_path = new_file_path

        if not is_directory and content:
            with open(file_path, 'w') as f:
                f.write(content)
        return Response({'msg': 'ok'})

    def delete(self, request, **kwargs):
        not_delete_allowed = ['root', 'main.yml']
        playbook_id = kwargs.get('pk')
        playbook = get_object_or_404(Playbook, id=playbook_id)
        work_path = playbook.work_dir
        file_key = request.query_params.get('key', '')
        if not file_key:
            return Response(status=400)
        if file_key in not_delete_allowed:
            return Response(status=400)
        file_path = os.path.join(work_path, file_key)
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
                node = {
                    "name": d,
                    "title": d,
                    "id": os.path.join(relative_path, d) if not os.path.join(relative_path, d).startswith(
                        '.') else d,
                    "isParent": True,
                    "open": False,
                    "pId": relative_path if not relative_path.startswith('.') else 'root',
                    "temp": False
                }
                if expand_key == node['id']:
                    node['open'] = True
                nodes.append(node)
            for f in files:
                node = {
                    "name": f,
                    "title": f,
                    "iconSkin": 'file',
                    "id": os.path.join(relative_path, f) if not os.path.join(relative_path, f).startswith(
                        '.') else f,
                    "isParent": False,
                    "open": False,
                    "pId": relative_path if not relative_path.startswith('.') else 'root',
                    "temp": False
                }
                nodes.append(node)
        return nodes
