# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from rest_framework.routers import DefaultRouter
from .. import api

app_name = 'ops'

router = DefaultRouter()
router.register(r'v1/tasks', api.TaskViewSet, 'task')

urlpatterns = []

urlpatterns += router.urls
