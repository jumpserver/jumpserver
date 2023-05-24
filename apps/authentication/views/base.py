from functools import lru_cache

from rest_framework.request import Request
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string
from django.conf import settings
from django.db.utils import IntegrityError
from django.views import View

from authentication import errors
from authentication.mixins import AuthMixin
from users.models import User
from common.utils.django import reverse, get_object_or_none
from common.utils import get_logger

from .mixins import FlashMessageMixin


logger = get_logger(__file__)


class BaseLoginCallbackView(AuthMixin, FlashMessageMixin, View):

    client_type_path = ''
    client_auth_params = {}
    user_type = ''
    auth_backend = None
    # 提示信息
    msg_client_err = _('Error')
    msg_user_not_bound_err = _('Error')
    msg_not_found_user_from_client_err = _('Error')

    def verify_state(self):
        raise NotImplementedError

    def get_verify_state_failed_response(self, redirect_uri):
        raise NotImplementedError

    @property
    @lru_cache(maxsize=1)
    def client(self):
        if not all([self.client_type_path, self.client_auth_params]):
            raise NotImplementedError
        client_init = {k: getattr(settings, v) for k, v in self.client_auth_params.items()}
        client_type = import_string(self.client_type_path)
        return client_type(**client_init)

    def create_user_if_not_exist(self, user_id, **kwargs):
        user = None
        user_attr = self.client.get_user_detail(user_id, **kwargs)
        try:
            user, create = User.objects.get_or_create(
                username=user_attr['username'], defaults=user_attr
            )
            setattr(user, f'{self.user_type}_id', user_id)
            if create:
                setattr(user, 'source', self.user_type)
            user.save()
        except IntegrityError as err:
            logger.error(f'{self.msg_client_err}: create user error: {err}')

        if user is None:
            title = self.msg_client_err
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
            err = self.msg_not_found_user_from_client_err
            response = self.get_failed_response(login_url, title=err, msg=err)
            return response

        user = get_object_or_none(User, **{f'{self.user_type}_id': user_id})
        if user is None:
            user, err = self.create_user_if_not_exist(user_id, other_info=other_info)
            if err is not None:
                response = self.get_failed_response(login_url, title=err[0], msg=err[1])
                return response

        try:
            self.check_oauth2_auth(user, getattr(settings, self.auth_backend))
        except errors.AuthFailedError as e:
            self.set_login_failed_mark()
            msg = e.msg
            response = self.get_failed_response(login_url, title=msg, msg=msg)
            return response
        return self.redirect_to_guard_view()
