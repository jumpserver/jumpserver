# -*- coding: utf-8 -*-
#

from django.urls import path
from rest_framework.routers import DefaultRouter
from .. import api


app_name = 'orgs'
router = DefaultRouter()

# 将会删除
router.register(r'org/(?P<org_id>[0-9a-zA-Z\-]{36})/membership/admins',
                api.OrgMembershipAdminsViewSet, 'membership-admins')
router.register(r'org/(?P<org_id>[0-9a-zA-Z\-]{36})/membership/users',
                api.OrgMembershipUsersViewSet, 'membership-users'),
# 替换为这个
router.register(r'orgs/(?P<org_id>[0-9a-zA-Z\-]{36})/membership/admins',
                api.OrgMembershipAdminsViewSet, 'membership-admins-2')
router.register(r'orgs/(?P<org_id>[0-9a-zA-Z\-]{36})/membership/users',
                api.OrgMembershipUsersViewSet, 'membership-users-2'),

router.register(r'orgs', api.OrgViewSet, 'org')


urlpatterns = [
]

urlpatterns += router.urls
