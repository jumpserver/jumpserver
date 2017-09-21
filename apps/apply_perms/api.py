# ~*~ coding: utf-8 ~*~
#

from rest_framework import viewsets
from rest_framework.views import APIView, Response
from users.permissions import IsValidUser
from .models import ApplyPermission
from . import serializers
from users.permissions import IsValidUser, IsSuperUser, IsAppUser
from django.shortcuts import get_object_or_404
from django.utils import timezone

class ApplyPermissionViewSet(viewsets.ModelViewSet):
    queryset = ApplyPermission.objects.all()
    serializer_class = serializers.ApplyPermissionSerializer
    permission_classes = (IsValidUser,)

class ApproveApplyPermission(APIView):
    permission_classes = (IsValidUser,)
    def put(self, request, *args, **kwargs):
        apply_permission_id = str(request.data.get('id', ''))
        status = str(request.data.get('status', ''))
        if apply_permission_id and  apply_permission_id.isdigit() and status:
            apply_permission = get_object_or_404(ApplyPermission, id=int(apply_permission_id))

            if apply_permission:
                apply_permission.status = status
                apply_permission.date_approved = timezone.localtime()
                apply_permission.save()
                return Response({'msg': 'success'})
        return Response({'msg': 'failed'}, status=404)