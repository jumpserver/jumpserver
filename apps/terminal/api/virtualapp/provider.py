import uuid

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from common.api import JMSBulkModelViewSet
from common.drf.filters import BaseFilterSet
from common.permissions import IsServiceAccount
from orgs.utils import tmp_to_builtin_org
from terminal.models import AppProvider, AppProviderDeployment
from terminal.serializers import (
    AppProviderSerializer, AppProviderContainerSerializer,
    AppProviderDeploymentSerializer,
)
from terminal.tasks import run_app_provider_deployment, run_app_provider_deployments

__all__ = ['AppProviderViewSet', 'AppProviderDeploymentViewSet']


class AppProviderFilterSet(BaseFilterSet):
    address = filters.CharFilter(field_name='host__address', label=_('Address'))

    class Meta:
        model = AppProvider
        fields = ['name', 'address']


class AppProviderViewSet(JMSBulkModelViewSet):
    serializer_class = AppProviderSerializer
    queryset = AppProvider.objects.select_related('host')
    filterset_class = AppProviderFilterSet
    search_fields = ['name', 'host__address']
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

    def get_object(self):
        # Existing Panda versions discover their provider using the service
        # account UUID before switching to the provider UUID in the response.
        user = self.request.user
        if (
            self.action == 'retrieve'
            and getattr(user, 'is_service_account', False)
            and str(self.kwargs.get(self.lookup_field)) == str(user.id)
        ):
            provider = self.get_queryset().filter(terminal__user=user).first()
            if provider:
                self.check_object_permissions(self.request, provider)
                return provider
        return super().get_object()

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
        data['deploy_options'] = {}
        serializer.save(**data)

    @transaction.atomic
    def perform_destroy(self, instance):
        instance = AppProvider.objects.select_for_update().get(pk=instance.pk)
        if instance.deployments.filter(status__in=('pending', 'running')).exists():
            raise ValidationError(_('Wait for the current deployment to finish before deleting the provider'))
        super().perform_destroy(instance)

    @transaction.atomic
    def perform_bulk_destroy(self, objects):
        for instance in objects.order_by('pk'):
            self.perform_destroy(instance)

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
        provider.publications.update(status='pending', app_version='', date_updated=timezone.now())
        if not provider.host_id:
            return Response({'task': None, 'count': len(publications)}, status=200)
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
    filterset_fields = {'provider': ['exact'], 'status': ['exact'], 'publication': ['isnull']}
    http_method_names = ['get', 'post', 'head', 'options']

    def dispatch(self, request, *args, **kwargs):
        with tmp_to_builtin_org(system=1):
            return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def start_deploy(instance):
        try:
            run_app_provider_deployment.apply_async(
                (instance.id,), task_id=str(instance.id)
            )
        except Exception:
            AppProviderDeployment.objects.filter(pk=instance.pk, status='pending').update(
                status='error', date_finished=timezone.now(), date_updated=timezone.now(),
            )
            raise

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = AppProvider.objects.select_for_update().get(pk=serializer.validated_data['provider'].pk)
        if provider.deployments.filter(publication__isnull=True, status__in=('pending', 'running')).exists():
            raise ValidationError({'provider': _('A deployment is already pending or running for this provider')})
        provider.validate_deployment()
        instance = serializer.save(provider=provider)
        instance.save_task(instance.id)
        transaction.on_commit(lambda: self.start_deploy(instance))
        return Response(self.get_serializer(instance).data, status=201)
