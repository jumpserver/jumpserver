# -*- coding: utf-8 -*-
#
import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView, Response

from common.api import JMSBulkModelViewSet
from common.const.http import POST
from common.utils import get_object_or_none
from orgs.utils import tmp_to_root_org
from terminal import serializers
from terminal.const import TaskNameType
from terminal.models import Session, Task
from terminal.utils import is_session_approver

__all__ = ['TaskViewSet', 'KillSessionAPI', 'KillSessionForTicketAPI', ]
logger = logging.getLogger(__file__)


class TaskViewSet(JMSBulkModelViewSet):
    queryset = Task.objects.all()
    serializer_class = serializers.TaskSerializer
    filterset_fields = ('is_finished',)
    serializer_classes = {
        'create_toggle_task': serializers.LockTaskSessionSerializer,
        'handle_ticket_task': serializers.LockTaskSessionSerializer,
        'default': serializers.TaskSerializer
    }
    rbac_perms = {
        "create_toggle_task": "terminal.terminate_session",
    }

    @action(methods=[POST], detail=False, url_path='toggle-lock-session')
    def create_toggle_task(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data['session_id']
        task_name = serializer.validated_data['task_name']
        session_ids = [session_id, ]
        validated_session = create_sessions_tasks(session_ids, request.user, task_name=task_name)
        return Response({"ok": validated_session})

    @action(methods=[POST], detail=False, permission_classes=[IsAuthenticated, ],
            url_path='toggle-lock-session-for-ticket', )
    def handle_ticket_task(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data['session_id']
        task_name = serializer.validated_data['task_name']
        user_id = request.user.id

        if not is_session_approver(session_id, user_id):
            return Response({}, status=status.HTTP_403_FORBIDDEN)

        with tmp_to_root_org():
            validated_session = create_sessions_tasks([session_id], request.user, task_name=task_name)
        return Response({"ok": validated_session})


def create_sessions_tasks(session_ids, user, task_name=TaskNameType.kill_session):
    validated_session = []

    for session_id in session_ids:
        session = get_object_or_none(Session, id=session_id)
        if session and not session.is_finished:
            validated_session.append(session_id)
            Task.objects.create(
                name=task_name, args=session.id, terminal=session.terminal,
                kwargs={
                    'terminated_by': str(user),
                    'created_by': str(user)
                }
            )
    return validated_session


class KillSessionAPI(APIView):
    model = Task
    rbac_perms = {
        'POST': 'terminal.terminate_session'
    }

    def post(self, request, *args, **kwargs):
        session_ids = request.data
        validated_session = create_sessions_tasks(session_ids, request.user)
        return Response({"ok": validated_session})


class KillSessionForTicketAPI(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        session_ids = request.data
        user_id = request.user.id

        for session_id in session_ids:
            if not is_session_approver(session_id, user_id):
                return Response({}, status=status.HTTP_403_FORBIDDEN)

        with tmp_to_root_org():
            validated_session = create_sessions_tasks(session_ids, request.user)

        return Response({"ok": validated_session})
