# -*- coding: utf-8 -*-
#
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from common.utils import get_logger, get_object_or_none
from common.permissions import IsOrgAdmin
from ..models import LoginConfirmSetting
from ..serializers import LoginConfirmSettingSerializer
from .. import errors

__all__ = ['LoginConfirmSettingUpdateApi', 'UserOrderAcceptAuthApi']
logger = get_logger(__name__)


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


class UserOrderAcceptAuthApi(APIView):
    permission_classes = ()

    def get(self, request, *args, **kwargs):
        from orders.models import LoginConfirmOrder
        order_id = self.request.session.get("auth_order_id")
        logger.debug('Login confirm order id: {}'.format(order_id))
        if not order_id:
            order = None
        else:
            order = get_object_or_none(LoginConfirmOrder, pk=order_id)
        try:
            if not order:
                raise errors.LoginConfirmOrderNotFound(order_id)
            if order.status == order.STATUS_ACCEPTED:
                self.request.session["auth_confirm"] = "1"
                return Response({"msg": "ok"})
            elif order.status == order.STATUS_REJECTED:
                raise errors.LoginConfirmRejectedError(order_id)
            else:
                return errors.LoginConfirmWaitError(order_id)
        except errors.AuthFailedError as e:
            data = e.as_data()
            return Response(data, status=400)
