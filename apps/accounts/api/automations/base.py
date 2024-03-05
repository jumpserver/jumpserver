from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import status, mixins, viewsets
from rest_framework.response import Response

from accounts.models import AutomationExecution
from accounts.tasks import execute_account_automation_task
from assets import serializers
from assets.models import BaseAutomation
from common.const.choices import Trigger
from orgs.mixins import generics

__all__ = [
    'AutomationAssetsListApi', 'AutomationRemoveAssetApi',
    'AutomationAddAssetApi', 'AutomationNodeAddRemoveApi',
    'AutomationExecutionViewSet',
]


class AutomationAssetsListApi(generics.ListAPIView):
    model = BaseAutomation
    serializer_class = serializers.AutomationAssetsSerializer
    filterset_fields = ("name", "address")
    search_fields = filterset_fields

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(self.model, pk=pk)

    def get_queryset(self):
        instance = self.get_object()
        assets = instance.get_all_assets().only(
            *self.serializer_class.Meta.only_fields
        )
        return assets


class AutomationRemoveAssetApi(generics.RetrieveUpdateAPIView):
    model = BaseAutomation
    serializer_class = serializers.UpdateAssetSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response({'error': serializer.errors})

        assets = serializer.validated_data.get('assets')
        if assets:
            instance.assets.remove(*tuple(assets))
        return Response({'msg': 'ok'})


class AutomationAddAssetApi(generics.RetrieveUpdateAPIView):
    model = BaseAutomation
    serializer_class = serializers.UpdateAssetSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data.get('assets')
            if assets:
                instance.assets.add(*tuple(assets))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AutomationNodeAddRemoveApi(generics.RetrieveUpdateAPIView):
    model = BaseAutomation
    serializer_class = serializers.UpdateNodeSerializer

    def update(self, request, *args, **kwargs):
        action_params = ['add', 'remove']
        action = request.query_params.get('action')
        if action not in action_params:
            err_info = _("The parameter 'action' must be [{}]".format(','.join(action_params)))
            return Response({"error": err_info})

        instance = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            nodes = serializer.validated_data.get('nodes')
            if nodes:
                # eg: plan.nodes.add(*tuple(assets))
                getattr(instance.nodes, action)(*tuple(nodes))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AutomationExecutionViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin,
    mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    search_fields = ('trigger', 'automation__name')
    filterset_fields = ('trigger', 'automation_id', 'automation__name')
    serializer_class = serializers.AutomationExecutionSerializer

    tp: str

    def get_queryset(self):
        queryset = AutomationExecution.objects.all()
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        automation = serializer.validated_data.get('automation')
        task = execute_account_automation_task.delay(
            pid=str(automation.pk), trigger=Trigger.manual, tp=self.tp
        )
        return Response({'task': task.id}, status=status.HTTP_201_CREATED)
