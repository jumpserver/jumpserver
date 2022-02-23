# -*- coding: utf-8 -*-
#
import logging
from rest_framework.views import APIView, Response
from rest_framework_bulk import BulkModelViewSet
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from common.utils import get_object_or_none
from ..models import Session, Task
from .. import serializers
from terminal.utils import is_session_approver
from orgs.utils import tmp_to_root_org

__all__ = ['TaskViewSet', 'KillSessionAPI', 'KillSessionForTicketAPI']
logger = logging.getLogger(__file__)


class TaskViewSet(BulkModelViewSet):
    queryset = Task.objects.all()
    serializer_class = serializers.TaskSerializer
    filterset_fields = ('is_finished',)


def kill_sessions(session_ids, user):
    validated_session = []

    for session_id in session_ids:
        session = get_object_or_none(Session, id=session_id)
        if session and not session.is_finished:
            validated_session.append(session_id)
            Task.objects.create(
                name="kill_session", args=session.id, terminal=session.terminal,
                kwargs={
                    'terminated_by': str(user)
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
        validated_session = kill_sessions(session_ids, request.user)
        return Response({"ok": validated_session})


class KillSessionForTicketAPI(APIView):
    permission_classes = (IsAuthenticated, )

    def post(self, request, *args, **kwargs):
        session_ids = request.data
        user_id = request.user.id

        for session_id in session_ids:
            if not is_session_approver(session_id, user_id):
                return Response({}, status=status.HTTP_403_FORBIDDEN)

        with tmp_to_root_org():
            validated_session = kill_sessions(session_ids, request.user)

        return Response({"ok": validated_session})
