from django.conf.urls import url
from rest_framework import routers
from .. import api

app_name = 'apply_perms'

router = routers.DefaultRouter()
router.register('v1/apply-permissions',
                api.ApplyPermissionViewSet,
                'apply-permission')

urlpatterns = []

urlpatterns += router.urls