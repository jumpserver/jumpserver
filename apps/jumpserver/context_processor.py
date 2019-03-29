# -*- coding: utf-8 -*-
#
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.conf import settings
from django.utils.translation import gettext_lazy as _


def jumpserver_processor(request):
    # Setting default pk
    context = {
        'DEFAULT_PK': '00000000-0000-0000-0000-000000000000',
        'LOGO_URL': static('img/logo.png'),
        'LOGO_TEXT_URL': static('img/logo_text.png'),
        'LOGIN_IMAGE_URL': static('img/login_image.png'),
        'FAVICON_URL': static('img/facio.ico'),
        'JMS_TITLE': 'Jumpserver',
        'VERSION': settings.VERSION,
        'COPYRIGHT': _('Beijing Duizhan Tech, Inc.') + ' © 2014-2019'
    }
    return context



