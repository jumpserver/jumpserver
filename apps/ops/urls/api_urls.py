# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from rest_framework.routers import DefaultRouter
from .. import api


router = DefaultRouter()
router.register(r'v1/tasks', api.TaskViewSet, 'task')
router.register(r'v1/adhoc', api.AdHocViewSet, 'adhoc')
router.register(r'v1/history', api.AdHocRunHistorySet, 'history')

urlpatterns = []

urlpatterns += router.urls
