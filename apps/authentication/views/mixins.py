# -*- coding: utf-8 -*-
#
from functools import lru_cache

from rest_framework.request import Request
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db.utils import IntegrityError

from authentication import errors
from users.models import User
from common.utils.django import reverse, get_object_or_none
from common.utils import get_logger


logger = get_logger(__file__)


class METAMixin:
    def get_next_url_from_meta(self):
        request_meta = self.request.META or {}
        next_url = None
        referer = request_meta.get('HTTP_REFERER', '')
        next_url_item = referer.rsplit('next=', 1)
        if len(next_url_item) > 1:
            next_url = next_url_item[-1]
        return next_url


class Client:
    get_user_id_by_code: callable
    get_user_detail: callable


class QRLoginCallbackMixin:
    verify_state: callable
    get_verify_state_failed_response: callable
    get_failed_response: callable
    check_oauth2_auth: callable
    set_login_failed_mark: callable
    redirect_to_guard_view: callable
    # 属性
    _client: Client
    CLIENT_INFO: tuple
    USER_TYPE: str
    AUTH_BACKEND: str
    CREATE_USER_IF_NOT_EXIST: str
    # 提示信息
    MSG_CLIENT_ERR: str
    MSG_USER_NOT_BOUND_ERR: str
    MSG_USER_NEED_BOUND_WARNING: str
    MSG_NOT_FOUND_USER_FROM_CLIENT_ERR: str

    @property
    @lru_cache(maxsize=1)
    def client(self):
        client_type, client_init = self.CLIENT_INFO
        client_init = {k: getattr(settings, v) for k, v in client_init.items()}
        return client_type(**client_init)

    def create_user_if_not_exist(self, user_id, **kwargs):
        user = None
        if not getattr(settings, self.CREATE_USER_IF_NOT_EXIST):
            title = self.MSG_CLIENT_ERR
            msg = self.MSG_USER_NEED_BOUND_WARNING
            return user, (title, msg)

        user_attr = self.client.get_user_detail(user_id, **kwargs)
        try:
            user, create = User.objects.get_or_create(
                username=user_attr['username'], defaults=user_attr
            )
            setattr(user, f'{self.USER_TYPE}_id', user_id)
            if create:
                setattr(user, 'source', self.USER_TYPE)
            user.save()
        except IntegrityError as err:
            logger.error(f'{self.MSG_CLIENT_ERR}: create user error: {err}')

        if user is None:
            title = self.MSG_CLIENT_ERR
            msg = _('If you have any question, please contact the administrator')
            return user, (title, msg)

        return user, None

    def get(self, request: Request):
        code = request.GET.get('code')
        redirect_url = request.GET.get('redirect_url')
        login_url = reverse('authentication:login')

        if not self.verify_state():
            return self.get_verify_state_failed_response(redirect_url)

        user_id, other_info = self.client.get_user_id_by_code(code)
        if not user_id:
            # 正常流程不会出这个错误，hack 行为
            err = self.MSG_NOT_FOUND_USER_FROM_CLIENT_ERR
            response = self.get_failed_response(login_url, title=err, msg=err)
            return response

        user = get_object_or_none(User, **{f'{self.USER_TYPE}_id': user_id})
        if user is None:
            user, err = self.create_user_if_not_exist(user_id, other_info=other_info)
            if err is not None:
                response = self.get_failed_response(login_url, title=err[0], msg=err[1])
                return response

        try:
            self.check_oauth2_auth(user, getattr(settings, self.AUTH_BACKEND))
        except errors.AuthFailedError as e:
            self.set_login_failed_mark()
            msg = e.msg
            response = self.get_failed_response(login_url, title=msg, msg=msg)
            return response
        return self.redirect_to_guard_view()
