# -*- coding: utf-8 -*-
#
import logging
from rest_framework.views import APIView, Response
from rest_framework_bulk import BulkModelViewSet

from common.utils import get_object_or_none
from common.permissions import IsOrgAdminOrAppUser
from ..models import Session, Task
from .. import serializers


__all__ = ['TaskViewSet', 'KillSessionAPI']
logger = logging.getLogger(__file__)


class TaskViewSet(BulkModelViewSet):
    queryset = Task.objects.all()
    serializer_class = serializers.TaskSerializer
    permission_classes = (IsOrgAdminOrAppUser,)


class KillSessionAPI(APIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    model = Task

    def post(self, request, *args, **kwargs):
        validated_session = []
        for session_id in request.data:
            session = get_object_or_none(Session, id=session_id)
            if session and not session.is_finished:
                validated_session.append(session_id)
                self.model.objects.create(
                    name="kill_session", args=session.id,
                    terminal=session.terminal,
                )
        return Response({"ok": validated_session})
