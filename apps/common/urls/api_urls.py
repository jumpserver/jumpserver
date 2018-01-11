from __future__ import absolute_import

from django.conf.urls import url

from .. import api

app_name = 'common'

urlpatterns = [
    url(r'^v1/mail/testing/$', api.MailTestingAPI.as_view(), name='mail-testing'),
]
