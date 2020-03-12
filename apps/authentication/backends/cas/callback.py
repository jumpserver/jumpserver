# -*- coding: utf-8 -*-
#
from django.contrib.auth import get_user_model


User = get_user_model()


def cas_callback(response):
    username = response['username']
    user, user_created = User.objects.get_or_create(username=username)
    profile, created = user.get_profile()

    profile.role = response['attributes']['role']
    profile.birth_date = response['attributes']['birth_date']
    profile.save()
