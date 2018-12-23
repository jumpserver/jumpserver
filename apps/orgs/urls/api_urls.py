# -*- coding: utf-8 -*-
#

from django.urls import path
from rest_framework.routers import DefaultRouter
from .. import api


app_name = 'orgs'
router = DefaultRouter()

router.register(r'org/(?P<org_id>[0-9a-zA-Z\-]{36})/membership/admins',
                api.OrgMembershipAdminsViewSet, 'membership-admins')

router.register(r'org/(?P<org_id>[0-9a-zA-Z\-]{36})/membership/users',
                api.OrgMembershipUsersViewSet, 'membership-users'),

router.register(r'orgs', api.OrgViewSet, 'org')


urlpatterns = [
]

urlpatterns += router.urls
