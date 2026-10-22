import os
import shutil

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils._os import safe_join
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response

from common.api.generic import JMSBulkModelViewSet, JMSGenericViewSet
from common.exceptions import JMSException
from common.permissions import IsOwnerOrAdminWritable
from common.serializers import EmptySerializer
from common.utils.http import is_true
from common.utils.zip import safe_extract_zip
from ops.filters import PlaybookFilterSet
from rbac.permissions import RBACPermission

from ..const import Scope
from ..exception import PlaybookNoValidEntry
from ..models import Playbook
from ..playbook_files import (
    generate_playbook_tree,
    resolve_playbook_path,
    validate_playbook_file_name,
    write_playbook_file,
)
from ..serializers.playbook import (
    PlaybookFileCreateSerializer,
    PlaybookFileUpdateSerializer,
    PlaybookSerializer,
)

__all__ = ["PlaybookFileViewSet", "PlaybookViewSet"]


def unzip_playbook(src, dest):
    safe_extract_zip(src, dest)


class PlaybookViewSet(JMSBulkModelViewSet):
    serializer_class = PlaybookSerializer
    permission_classes = (RBACPermission, IsOwnerOrAdminWritable)
    queryset = Playbook.objects.all()
    search_fields = ('name', 'comment')
    filterset_class = PlaybookFilterSet
    custom_filter_fields = [
        {'name': 'only_mine', 'type': 'boolean', 'methods': ['GET']},
        {'name': 'clone_from', 'schema': {'type': 'string', 'format': 'uuid'}, 'methods': ['POST']},
    ]
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
        instance = serializer.save()
        base_path = safe_join(settings.DATA_DIR, "ops", "playbook")
        clone_id = self.request.query_params.get('clone_from')

        if clone_id:
            queryset = self.get_queryset()
            clone_from = queryset.filter(id=clone_id).first()
            if not clone_from:
                raise JMSException(code='invalid_clone_id', detail={"msg": gettext("Invalid clone_from id")})
            src_path = safe_join(base_path, clone_id)
            dest_path = safe_join(base_path, str(instance.id))
            if not os.path.exists(src_path):
                raise JMSException(code='invalid_playbook_id', detail={"msg": gettext("clone playbook file not found")})
            shutil.copytree(src_path, dest_path)
            return

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


class PlaybookFileViewSet(JMSGenericViewSet):
    permission_classes = (RBACPermission,)
    serializer_classes = {
        'default': EmptySerializer,
        'create': PlaybookFileCreateSerializer,
        'partial_update': PlaybookFileUpdateSerializer,
    }
    custom_filter_fields = [
        {'name': 'key', 'methods': ['GET']},
        {'name': 'expand', 'methods': ['GET']},
        {'name': 'key', 'required': True, 'methods': ['DELETE']},
    ]
    rbac_perms = {
        'retrieve': 'ops.view_playbook',
        'create': 'ops.change_playbook',
        'destroy': 'ops.change_playbook',
        'partial_update': 'ops.change_playbook',
    }
    protected_files = Playbook.entry_filenames

    def get_response_serializer(self):
        if self.action == 'create':
            return {200: self.get_serializer()}
        if self.action == 'partial_update':
            return None
        return self.get_serializer()

    def get_playbook(self, playbook_id):
        playbook = get_object_or_404(Playbook, id=playbook_id, creator=self.request.user)
        return playbook

    def retrieve(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        user = self.request.user
        playbook = get_object_or_404(Playbook, Q(creator=user) | Q(scope=Scope.public), id=playbook_id)
        work_path = playbook.work_dir
        file_key = request.query_params.get('key', '')
        if file_key:
            try:
                file_path = resolve_playbook_path(work_path, file_key)
                with open(file_path, 'r') as f:
                    content = f.read()
            except UnicodeDecodeError:
                content = _('Unsupported file content')
            except (SuspiciousFileOperation, FileNotFoundError):
                raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})
            return Response({'content': content})
        else:
            resolve_playbook_path(work_path, '', allow_root=True)
            expand_key = request.query_params.get('expand', '')
            nodes = generate_playbook_tree(playbook, work_path, expand_key)
            return Response(nodes)

    def create(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        playbook = self.get_playbook(playbook_id)
        work_path = playbook.work_dir

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        full_path = resolve_playbook_path(work_path, data.get('key', ''), allow_root=True)

        is_directory = data.get('is_directory', False)
        content = data.get('content', '')
        name = data.get('name', '')
        validate_playbook_file_name(name)

        def find_new_name(p, is_file=False):
            if not p:
                if is_file:
                    p = 'new_file.yml'
                else:
                    p = 'new_dir'
            np = safe_join(full_path, p)
            n = 0
            while os.path.lexists(np):
                n += 1
                np = safe_join(full_path, f'{p}({n})')
            return np

        try:
            if is_directory:
                new_file_path = find_new_name(name)
                os.mkdir(new_file_path)
            else:
                new_file_path = find_new_name(name, True)
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
        return Response(self.get_serializer(new_node).data)

    def partial_update(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        playbook = self.get_playbook(playbook_id)
        work_path = playbook.work_dir

        file_key = request.data.get('key', '')
        if not file_key:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        file_path = resolve_playbook_path(work_path, data['key'])
        file_key = os.path.relpath(file_path, work_path)
        new_name = data.get('new_name', '')
        validate_playbook_file_name(new_name)

        if file_key.casefold() in self.protected_files and new_name:
            raise JMSException(code='this_file_can_not_be_rename', detail={"msg": _("This file can not be rename")})

        content = data.get('content', '')
        is_directory = data.get('is_directory', False)
        if new_name:
            try:
                new_file_path = safe_join(os.path.dirname(file_path), new_name)
                new_file_path = resolve_playbook_path(work_path, os.path.relpath(new_file_path, work_path))
                if new_file_path == file_path:
                    return Response(status=status.HTTP_200_OK)
                if os.path.lexists(new_file_path):
                    raise JMSException(code='file_already exists', detail={"msg": _("File already exists")})
                os.rename(file_path, new_file_path)
            except SuspiciousFileOperation:
                raise JMSException(code='invalid_file_path', detail={"msg": _("Invalid file path")})

        elif not is_directory:
            write_playbook_file(file_path, content)
        return Response(status=status.HTTP_200_OK)

    def destroy(self, request, **kwargs):
        playbook_id = kwargs.get('pk')
        playbook = self.get_playbook(playbook_id)
        work_path = playbook.work_dir
        file_key = request.query_params.get('key', '')
        if not file_key:
            raise JMSException(code='file_key_is_required', detail={"msg": _("File key is required")})

        file_path = resolve_playbook_path(work_path, file_key)
        file_key = os.path.relpath(file_path, work_path)
        if file_key.casefold() in self.protected_files:
            raise JMSException(code='This file can not be delete', detail={"msg": _("This file can not be delete")})
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)
        return Response({'msg': 'ok'})
