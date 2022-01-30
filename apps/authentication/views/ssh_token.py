from django.views.generic import RedirectView
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic.base import TemplateView
from django.contrib.auth import get_user_model

from common.utils import reverse
from common.utils import get_object_or_none
from common.utils.random import random_string

from ..utils import get_sso_url
from ..const import ENTRY_TOKEN_KEY


__all__ = ['SSHSSORedirectApi', 'SSHSSOTokenMsgView']


class SSHSSORedirectApi(RedirectView):

    @staticmethod
    def mark_from_ssh(username, userid):
        who_use_entry_token = '%s_%s' % (ENTRY_TOKEN_KEY, username)
        cache.set(who_use_entry_token, userid, 300)

    def get_redirect_url(self, *args, **kwargs):
        url = None
        token = self.request.GET.get('ssh_token', '')
        entry_token_key = '%s_%s' % (ENTRY_TOKEN_KEY, token)
        userinfo = cache.get(entry_token_key)
        if isinstance(userinfo, dict) and userinfo.get('sso_type'):
            url = get_sso_url(userinfo['sso_type'], next_url=reverse('authentication:ssh-sso-token', external=True))
            url += '?next_url=%s' % reverse('authentication:ssh-sso-token', external=True)
            self.mark_from_ssh(userinfo['username'], userinfo['userid'])
        return url


@method_decorator(never_cache, name='dispatch')
class SSHSSOTokenMsgView(TemplateView):
    template_name = 'flash_ssh_token.html'

    @staticmethod
    def get_token(request, user_id):
        if request:
            remote_addr = request.META.get('REMOTE_ADDR', '')
        else:
            remote_addr = '0.0.0.0'
        cache_key = '%s_%s' % (user_id, remote_addr)
        token = cache.get(cache_key)
        return token

    @staticmethod
    def set_token(request, user_id, auth_key):
        cache.set(auth_key, user_id, 300)
        if request:
            remote_addr = request.META.get('REMOTE_ADDR', '')
        else:
            remote_addr = '0.0.0.0'
        cache_key = '%s_%s' % (user_id, remote_addr)
        cache.set(cache_key, auth_key)

    def get(self, request, *args, **kwargs):
        context = {
            'title': _('SSH - Login temporary password'),
            'confirm_button': _('copy'),
        }
        error_message = {
            'error': _('You have not obtained the temporary password'
                       ' or the temporary password has expired')
        }
        username = getattr(request.user, 'username', '')
        key = '%s_%s' % (ENTRY_TOKEN_KEY, username)
        user_id = cache.get(key)
        if not user_id:
            context.update(error_message)
        else:
            user_model = get_user_model()
            user = get_object_or_none(user_model, id=user_id)
            if not user:
                context.update(error_message)
            else:
                auth_key = self.get_token(request, user_id)
                if not auth_key:
                    auth_key = random_string(48)
                    self.set_token(request, user_id, auth_key)
                context.update({'user': f"username: {username}", 'message': auth_key})
        return self.render_to_response(context)
