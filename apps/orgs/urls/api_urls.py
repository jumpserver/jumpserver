# -*- coding: utf-8 -*-
#

from django.urls import path
from rest_framework.routers import DefaultRouter
from .. import api


app_name = 'orgs'
router = DefaultRouter()
router.register(r'orgs', api.OrgViewSet, 'org')


urlpatterns = [
    path('orgs/<uuid:pk>/admins/', api.OrgUpdateAdminsApi.as_view(), name='update-admins'),
    path('orgs/<uuid:pk>/users/', api.OrgUpdateUsersApi.as_view(), name='update-users'),
]

urlpatterns += router.urls
