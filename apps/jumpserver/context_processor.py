# -*- coding: utf-8 -*-
#
import datetime

from django.conf import settings
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _

from jumpserver.vendor import get_vendor_value, is_default_vendor

default_interface = dict((
    ('logo_logout', get_vendor_value('logo_logout')),
    ('logo_index', get_vendor_value('logo_index')),
    ('login_image', get_vendor_value('login_image')),
    ('favicon', get_vendor_value('favicon')),
    ('login_title', get_vendor_value('login_title', default=_('JumpServer - An open-source PAM'))),
    ('theme', get_vendor_value('theme', default='classic_green')),
    ('theme_info', {}),
    ('footer_content', get_vendor_value('footer_content', default='')),
))

if not is_default_vendor():
    default_interface['theme_info'] = get_vendor_value('theme_info', default={})

current_year = datetime.datetime.now().year

default_context = {
    'DEFAULT_PK': '00000000-0000-0000-0000-000000000000',
    'LOGIN_CAS_logo_logout': static('img/login_cas_logo.png'),
    'LOGIN_WECOM_logo_logout': static('img/login_wecom_logo.png'),
    'LOGIN_DINGTALK_logo_logout': static('img/login_dingtalk_logo.png'),
    'LOGIN_FEISHU_logo_logout': static('img/login_feishu_logo.png'),
    'COPYRIGHT': f'{_("FIT2CLOUD")} © 2014-{current_year}',
    'INTERFACE': default_interface,
}


def jumpserver_processor(request):
    # Setting default pk
    context = {**default_context}
    context.update({
        'VERSION': settings.VERSION,
        'SECURITY_COMMAND_EXECUTION': settings.SECURITY_COMMAND_EXECUTION,
        'SECURITY_MFA_VERIFY_TTL': settings.SECURITY_MFA_VERIFY_TTL,
        'FORCE_SCRIPT_NAME': settings.FORCE_SCRIPT_NAME,
        'SECURITY_VIEW_AUTH_NEED_MFA': settings.SECURITY_VIEW_AUTH_NEED_MFA,
    })
    return context
