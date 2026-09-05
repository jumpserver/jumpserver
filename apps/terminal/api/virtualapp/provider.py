import uuid

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.api import JMSBulkModelViewSet
from common.permissions import IsServiceAccount
from orgs.utils import tmp_to_builtin_org
from terminal.models import AppProvider, AppProviderDeployment
from terminal.serializers import (
    AppProviderSerializer, AppProviderContainerSerializer,
    AppProviderDeploymentSerializer,
)
from terminal.tasks import run_app_provider_deployment, run_app_provider_deployments

__all__ = ['AppProviderViewSet', 'AppProviderDeploymentViewSet']


class AppProviderViewSet(JMSBulkModelViewSet):
    serializer_class = AppProviderSerializer
    queryset = AppProvider.objects.all()
    filterset_fields = ['name', 'hostname']
    search_fields = ['name', 'hostname', ]
    rbac_perms = {
        'startup': 'terminal.change_appprovider',
        'containers': 'terminal.view_appprovider',
        'status': 'terminal.view_appprovider',
        'publish_apps': 'terminal.change_virtualapppublication',
    }

    cache_status_key_prefix = AppProvider.cache_status_key_prefix

    def dispatch(self, request, *args, **kwargs):
        with tmp_to_builtin_org(system=1):
            return super().dispatch(request, *args, **kwargs)

    def get_permissions(self):
        if self.action in ('create', 'startup') and getattr(
            self.request.user, 'is_service_account', False
        ):
            return [IsServiceAccount()]
        return super().get_permissions()

    def perform_create(self, serializer):
        request_terminal = getattr(self.request.user, 'terminal', None)
        if not request_terminal:
            serializer.save(terminal=None)
            return
        data = dict()
        data['terminal'] = request_terminal
        data['id'] = self.request.user.id
        # Registration is performed by the provider service account. Runtime
        # routing and host binding remain administrator-controlled settings.
        data['host'] = None
        data['runtime_type'] = AppProvider.RuntimeType.docker
        data['connection_mode'] = AppProvider.ConnectionMode.direct
        data['service_url'] = ''
        data['deploy_options'] = {}
        serializer.save(**data)

    @action(detail=True, methods=['post'])
    def startup(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.check_terminal_binding(request)
        return Response({'msg': 'ok'})

    @action(detail=True, methods=['get'], serializer_class=AppProviderContainerSerializer)
    def containers(self, request, *args, **kwargs):
        instance = self.get_object()
        key = self.cache_status_key_prefix.format(instance.id)
        data = cache.get(key)
        if not data:
            data = []
        return self.get_paginated_response_from_queryset(data)

    @action(detail=True, methods=['post'], serializer_class=AppProviderContainerSerializer)
    def status(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        key = self.cache_status_key_prefix.format(instance.id)
        cache.set(key, validated_data, 60 * 3)
        return Response({'msg': 'ok'})

    @action(detail=True, methods=['post'], url_path='publish-apps')
    def publish_apps(self, request, *args, **kwargs):
        provider = self.get_object()
        publications = list(provider.publications.all())
        if not publications:
            return Response({'task': None, 'count': 0}, status=200)

        task_id = uuid.uuid4()
        provider.publications.update(status='pending', date_updated=timezone.now())
        deployments = AppProviderDeployment.objects.bulk_create([
            AppProviderDeployment(
                provider=provider, publication=publication, task=task_id,
            )
            for publication in publications
        ])
        deployment_ids = [str(item.id) for item in deployments]
        transaction.on_commit(
            lambda: run_app_provider_deployments.apply_async(
                (deployment_ids,), task_id=str(task_id)
            )
        )
        return Response(
            {'task': str(task_id), 'count': len(deployment_ids)}, status=201
        )


class AppProviderDeploymentViewSet(viewsets.ModelViewSet):
    serializer_class = AppProviderDeploymentSerializer
    queryset = AppProviderDeployment.objects.all()
    filterset_fields = ['provider', 'status']

    @staticmethod
    def start_deploy(instance):
        run_app_provider_deployment.apply_async(
            (instance.id,), task_id=str(instance.id)
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance.save_task(instance.id)
        transaction.on_commit(lambda: self.start_deploy(instance))
        return Response({'task': str(instance.id)}, status=201)
