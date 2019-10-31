# -*- coding: utf-8 -*-
#
from rest_framework.generics import UpdateAPIView
from django.shortcuts import get_object_or_404

from common.permissions import IsOrgAdmin
from ..models import LoginConfirmSetting
from ..serializers import LoginConfirmSettingSerializer

__all__ = ['LoginConfirmSettingUpdateApi']


class LoginConfirmSettingUpdateApi(UpdateAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = LoginConfirmSettingSerializer

    def get_object(self):
        from users.models import User
        user_id = self.kwargs.get('user_id')
        user = get_object_or_404(User, pk=user_id)
        defaults = {'user': user}
        s, created = LoginConfirmSetting.objects.get_or_create(
            defaults, user=user,
        )
        return s
