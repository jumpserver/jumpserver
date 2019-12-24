# -*- coding: utf-8 -*-
# @Time    : 2019/11/22 1:49 下午
# @Author  : Alex
# @Email   : 1374462869@qq.com
# @Project : jumpserver
# @File    : signals.py
from django.dispatch import Signal

post_create_openid_user = Signal(providing_args=('user',))
post_openid_login_success = Signal(providing_args=('user', 'request'))