# ~*~ coding: utf-8 ~*~


from rest_framework import generics
from rest_framework.response import Response

from ops.ansible import runner
from common.utils import get_object_or_none
from assets.models import *
from .models import *
from users.permissions import IsValidUser


class TemplateTaskView(generics.UpdateAPIView):
    queryset = Template.objects.all()
    permission_classes = (IsValidUser,)

    def patch(self, request, *args, **kwargs):
        #: 拿到当前view对应的template
        template = self.get_object()
        if not template:
            return Response('Invalid Template', status=502)

        #: 拿到当前表单提交的asset
        asset_ids = self.request.data['assets']
        group_ids = self.request.data['groups']

        #: 聚合所有的asset
        assets = []
        for asset_id in asset_ids:
            assets.append(get_object_or_none(Asset, id=asset_id))
        for group_id in group_ids:
            assets.extend(Asset.objects.filter(groups__id=group_id))
        print(assets)

        runner.test_playbook()
        #: 执行ansible task
        # task = push_users.delay([asset._to_secret_json() for asset in assets],
        #                         system_user._to_secret_json())
        return Response('Success')
