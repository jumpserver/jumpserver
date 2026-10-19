import os
import shutil
import stat

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from rest_framework import status

from common.api.generic import JMSBulkModelViewSet
from common.exceptions import JMSException
from common.permissions import IsOwnerOrAdminWritable
from common.utils.http import is_true
from common.utils.yml import atomic_dump_text
from common.utils.zip import safe_extract_zip
from ops.filters import PlaybookFilterSet
from rbac.permissions import RBACPermission
from ..const import Scope
from ..exception import PlaybookNoValidEntry
from ..models import Playbook
from ..serializers.playbook import PlaybookSerializer, PlaybookFileCreateSerializer, PlaybookFileUpdateSerializer

__all__ = ["PlaybookViewSet", "PlaybookFileBrowserAPIView"]

from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils._os import safe_join
from django.utils.translation import gettext, gettext_lazy as _


def unzip_playbook(src, dest):
    safe_extract_zip(src, dest)


@extend_schema_view(
    create=extend_schema(parameters=[OpenApiParameter(
        'clone_from', OpenApiTypes.UUID,
        description='Clone a visible Playbook; inherit its scope when scope is omitted.',
    )]),
    list=extend_schema(parameters=[OpenApiParameter('only_mine', OpenApiTypes.BOOL)]),
)
class PlaybookViewSet(JMSBulkModelViewSet):
    serializer_class = PlaybookSerializer
    permission_classes = (RBACPermission, IsOwnerOrAdminWritable)
    queryset = Playbook.objects.all()
    search_fields = ('name', 'comment')
    filterset_class = PlaybookFilterSet
    ordering_fields = (
        'name', 'scope', 'create_method', 'created_by', 'date_created',
        'date_updated',
    )

    def allow_bulk_destroy(self, qs, filtered):
        for obj in filtered:
            self.check_object_permissions(self.request, obj)
        return True

    def perform_destroy(self, instance):
        if instance.job_set.exists():
            raise JMSException(code='playbook_has_job', detail={"msg": _("Currently playbook is being used in a job")})
        instance_id = instance.id
        super().perform_destroy(instance)
        dest_path = safe_join(settings.DATA_DIR, "ops", "playbook", instance_id.__str__())
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if is_true(self.request.query_params.get('only_mine')):
            queryset = queryset.filter(creator=user)
        else:
            queryset = queryset.filter(Q(creator=user) | Q(scope=Scope.public))
        return queryset

    def perform_create(self, serializer):
        base_path = safe_join(settings.DATA_DIR, "ops", "playbook")
        clone_id = self.request.query_params.get('clone_from')

        if clone_id:
            queryset = self.get_queryset()
            clone_from = queryset.filter(id=clone_id).first()
            if not clone_from:
                raise JMSException(code='invalid_clone_id', detail={"msg": gettext("Invalid clone_from id")})
            clone_options = {} if 'scope' in self.request.data else {'scope': clone_from.scope}
            instance = serializer.save(**clone_options)
            src_path = safe_join(base_path, str(clone_from.id))
            dest_path = safe_join(base_path, str(instance.id))
            if not os.path.exists(src_path):
                raise JMSException(code='invalid_playbook_id', detail={"msg": gettext("clone playbook file not found")})

            def reject_symlinks(directory, names):
                if os.path.islink(directory) or any(
                    os.path.islink(os.path.join(directory, name)) for name in names
                ):
                    raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})
                return []

            destination_exists = os.path.lexists(dest_path)
            try:
                shutil.copytree(src_path, dest_path, ignore=reject_symlinks)
            except Exception:
                if not destination_exists and os.path.isdir(dest_path):
                    shutil.rmtree(dest_path)
                raise
            return

        instance = serializer.save()
        if 'multipart/form-data' in self.request.headers['Content-Type']:
            src_path = safe_join(settings.MEDIA_ROOT, instance.path.name)
            dest_path = safe_join(base_path, str(instance.id))

            try:
                try:
                    unzip_playbook(src_path, dest_path)
                except RuntimeError:
                    raise JMSException(code='invalid_playbook_file', detail={"msg": gettext("Unzip failed")})

                if 'main.yml' not in os.listdir(dest_path):
                    raise PlaybookNoValidEntry
            except Exception:
                # The request transaction rolls back the model, but not files.
                try:
                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)
                finally:
                    instance.path.delete(save=False)
                raise

        elif instance.create_method == 'blank':
            dest_path = safe_join(base_path, str(instance.id))
            os.makedirs(dest_path)
            with open(safe_join(dest_path, 'main.yml'), 'w') as f:
                f.write('## write your playbook here')


@extend_schema_view(
    get=extend_schema(parameters=[OpenApiParameter('key', str), OpenApiParameter('expand', str)]),
    post=extend_schema(request=PlaybookFileCreateSerializer),
    patch=extend_schema(request=PlaybookFileUpdateSerializer),
    delete=extend_schema(parameters=[OpenApiParameter('key', str, required=True)]),
)
class PlaybookFileBrowserAPIView(APIView):
    permission_classes = (RBACPermission,)
    rbac_perms = {
        'GET': 'ops.view_playbook',
        'POST': 'ops.change_playbook',
        'DELETE': 'ops.change_playbook',
        'PATCH': 'ops.change_playbook',
    }
    protected_files = {'main.yml', 'main.yaml', 'main'}

    @staticmethod
    def resolve_file_path(work_path, key, allow_root=False):
        if not isinstance(key, str) or '\x00' in key or '\\' in key or os.path.isabs(key):
            raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})
        if key == 'root':
            key = ''
        elif key.startswith('root/'):
            key = key[5:]

        try:
            root_path = os.path.abspath(work_path)
            file_path = safe_join(root_path, key)
        except (SuspiciousFileOperation, ValueError):
            raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})

        relative_path = os.path.relpath(file_path, root_path)
        if relative_path == '.' and not allow_root:
            raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})

        # Check each component because safe_join only checks the lexical path.
        current = root_path
        if os.path.islink(current):
            raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})
        for part in relative_path.split(os.sep):
            current = os.path.join(current, part)
            if os.path.islink(current):
                raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})
        real_root = os.path.realpath(root_path)
        if os.path.commonpath((real_root, os.path.realpath(file_path))) != real_root:
            raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})
        return file_path

    @staticmethod
    def validate_file_name(name):
        if name in {'.', '..', 'root'} or any(char in name for char in ('/', '\\', '\x00')):
            raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})

    def get_playbook(self, playbook_id):
        playbook = get_object_or_404(Playbook, id=playbook_id, creator=self.request.user)
        return playbook

    def get(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        user = self.request.user
        playbook = get_object_or_404(Playbook, Q(creator=user) | Q(scope=Scope.public), id=playbook_id)
        work_path = playbook.work_dir
        file_key = request.query_params.get('key', '')
        if file_key:
            try:
                file_path = self.resolve_file_path(work_path, file_key)
                with open(file_path, 'r') as f:
                    content = f.read()
            except UnicodeDecodeError:
                content = _('Unsupported file content')
            except (SuspiciousFileOperation, FileNotFoundError):
                raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})
            return Response({'content': content})
        else:
            self.resolve_file_path(work_path, '', allow_root=True)
            expand_key = request.query_params.get('expand', '')
            nodes = self.generate_tree(playbook, work_path, expand_key)
            return Response(nodes)

    def post(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        playbook = self.get_playbook(playbook_id)
        work_path = playbook.work_dir

        serializer = PlaybookFileCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        full_path = self.resolve_file_path(work_path, data.get('key', ''), allow_root=True)

        is_directory = data.get('is_directory', False)
        content = data.get('content', '')
        name = data.get('name', '')
        self.validate_file_name(name)

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
                self.resolve_file_path(work_path, os.path.relpath(new_file_path, work_path))
                with open(new_file_path, 'x') as f:
                    f.write(content)
        except FileExistsError:
            raise JMSException(code='file_already_exists', detail={"msg": _("File already exists")})
        except SuspiciousFileOperation:
            raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})

        relative_path = os.path.relpath(os.path.dirname(new_file_path), work_path)
        new_node = {
            "name": os.path.basename(new_file_path),
            "title": os.path.basename(new_file_path),
            "id": os.path.relpath(new_file_path, work_path),
            "isParent": is_directory,
            "pId": relative_path if relative_path != '.' else 'root',
            "open": True,
        }
        if not is_directory:
            new_node['iconSkin'] = 'file'
        return Response(new_node)

    def patch(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        playbook = self.get_playbook(playbook_id)
        work_path = playbook.work_dir

        serializer = PlaybookFileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        file_path = self.resolve_file_path(work_path, data['key'])
        file_key = os.path.relpath(file_path, work_path)
        new_name = data.get('new_name', '')
        self.validate_file_name(new_name)

        if file_key.casefold() in self.protected_files and new_name:
            raise JMSException(code='this_file_can_not_be_rename', detail={"msg": _("This file can not be rename")})

        content = data.get('content', '')
        is_directory = data.get('is_directory', False)

        # rename
        if new_name:
            try:
                new_file_path = safe_join(os.path.dirname(file_path), new_name)
                if new_file_path == file_path:
                    return Response(status=status.HTTP_200_OK)
                self.resolve_file_path(work_path, os.path.relpath(new_file_path, work_path))
                if os.path.lexists(new_file_path):
                    raise JMSException(code='file_already exists', detail={"msg": _("File already exists")})
                os.rename(file_path, new_file_path)
            except SuspiciousFileOperation:
                raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})

        # edit content
        else:
            if not is_directory:
                file_mode = None
                if os.path.exists(file_path):
                    file_mode = stat.S_IMODE(os.stat(file_path, follow_symlinks=False).st_mode)

                def write_content(stream):
                    stream.write(content)
                    if file_mode is not None:
                        os.fchmod(stream.fileno(), file_mode)

                atomic_dump_text(file_path, write_content)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        playbook = self.get_playbook(playbook_id)
        work_path = playbook.work_dir
        file_key = request.query_params.get('key', '')
        if not file_key:
            raise JMSException(code='file_key_is_required', detail={"msg": _("File key is required")})

        file_path = self.resolve_file_path(work_path, file_key)
        file_key = os.path.relpath(file_path, work_path)
        if file_key.casefold() in self.protected_files:
            raise JMSException(code='This file can not be delete', detail={"msg": _("This file can not be delete")})
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
