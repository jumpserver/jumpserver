# -*- coding: utf-8 -*-
#
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView

from common.utils import get_logger

from .. import serializers, errors
from ..mixins import AuthMixin


logger = get_logger(__name__)

__all__ = ['TokenCreateApi']


class TokenCreateApi(AuthMixin, CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.BearerTokenSerializer

    def create_session_if_need(self):
        if self.request.session.is_empty():
            self.request.session.create()
            self.request.session.set_expiry(600)

    def create(self, request, *args, **kwargs):
        self.create_session_if_need()
        # 如果认证没有过，检查账号密码
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = self.get_user_or_auth(serializer.validated_data)
            self.check_user_mfa_if_need(user)
            self.check_user_login_confirm_if_need(user)
            self.send_auth_signal(success=True, user=user)
            resp = super().create(request, *args, **kwargs)
            self.clear_auth_mark()
            return resp
        except errors.AuthFailedError as e:
            return Response(e.as_data(), status=400)
        except errors.NeedMoreInfoError as e:
            return Response(e.as_data(), status=200)
        except errors.MFAUnsetError:
            return Response({'error': 'MFA unset, please set first'}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
