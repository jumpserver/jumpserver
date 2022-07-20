# -*- coding: utf-8 -*-
#
from django.templatetags.static import static
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

default_interface = dict((
    ('logo_logout', static('img/logo.png')),
    ('logo_index', static('img/logo_text.png')),
    ('login_image', static('img/login_image.jpg')),
    ('favicon', static('img/facio.ico')),
    ('login_title', _('JumpServer Open Source Bastion Host')),
    ('theme', 'classic_green'),
    ('theme_info', {}),
))

default_context = {
    'DEFAULT_PK': '00000000-0000-0000-0000-000000000000',
    'LOGIN_CAS_logo_logout': static('img/login_cas_logo.png'),
    'LOGIN_WECOM_logo_logout': static('img/login_wecom_logo.png'),
    'LOGIN_DINGTALK_logo_logout': static('img/login_dingtalk_logo.png'),
    'LOGIN_FEISHU_logo_logout': static('img/login_feishu_logo.png'),
    'COPYRIGHT': 'FIT2CLOUD 飞致云' + ' © 2014-2022',
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



