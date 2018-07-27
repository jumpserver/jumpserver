# -*- coding: utf-8 -*-
#

from rest_framework.routers import DefaultRouter
from .. import api


app_name = 'orgs'
router = DefaultRouter()
router.register(r'orgs', api.OrgViewSet, 'org')


urlpatterns = [
]

urlpatterns += router.urls
