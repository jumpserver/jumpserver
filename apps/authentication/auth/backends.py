# -*- coding: utf-8 -*-
#


from django.contrib.auth.backends import ModelBackend
from django.conf import settings
from common.utils import get_logger

logger = get_logger(__file__)


class JMSModelBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):

        # ModelBackend auth
        if not settings.AUTH_OPENID:
            super().authenticate(
                request, username=username, password=password, **kwargs
            )

        # Api / Coco User auth
        import authentication.openid.services.oidt_profile
        try:
            oidt_profile = authentication.openid.services.oidt_profile.\
                update_or_create_from_username_password(
                    client=request.client,
                    username=username,
                    password=password,
                )

        except Exception as e:
            logger.error(e)

        else:
            user = oidt_profile.user
            return user if self.user_can_authenticate(user) else None
