# -*- coding: utf-8 -*-
#
from oidc_rp.signals import oidc_user_created
from django.dispatch import receiver
from users.models import User


@receiver(oidc_user_created)
def on_oidc_user_created(sender, request, oidc_user):
    name = oidc_user.userinfo.get('name') or oidc_user.userinfo.get('username')
    oidc_user.user.name = name
    oidc_user.user.source = User.SOURCE_OPENID
    oidc_user.save()
