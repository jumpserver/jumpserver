# coding:utf-8
from rest_framework_bulk.routes import BulkRouter

from .. import api

app_name = 'rbac'


router = BulkRouter()
router.register(r'roles', api.RoleViewSet, 'role')
router.register(r'role-bindings', api.RoleBindingViewSet, 'role-binding')

urlpatterns = []

urlpatterns += router.urls
