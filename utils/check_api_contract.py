#!/usr/bin/env python3
"""Check account/risk/secret OpenAPI operations against handlers and RBAC actions.

This metadata check does not send API requests, mutate records, or require a
database/Redis service. It covers the risk and secret viewsets plus the account
and template viewsets from which their actions are inherited.
"""
import ast
import inspect
import os
import sys
import textwrap
import warnings
from pathlib import Path


def setup_django():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jumpserver.settings')
    os.environ.setdefault('XPACK_ENABLED', '0')
    os.environ.setdefault('SECRET_KEY', 'api-contract-check-metadata-only-not-for-production')
    os.environ.setdefault('BOOTSTRAP_TOKEN', 'api-contract-check-metadata-only')
    # Use CommonConfig's existing metadata-command path to skip service startup.
    sys.argv = [sys.argv[0], 'check']
    from django.conf import settings
    settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
    settings.DEBUG = False
    settings.DEBUG_DEV = False
    settings.LOGGING = {'version': 1, 'disable_existing_loggers': True}
    warnings.filterwarnings('ignore', message='Accessing the database during app initialization')
    import django
    django.setup()
    from django.test.utils import override_settings
    override_settings(CACHES={
        'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
    }).enable()


def rejects_method(view, action, seen=None):
    """Recognize explicit 405 handlers and DRF's partial-update delegates."""
    seen = set() if seen is None else seen
    if action in seen:
        return False
    seen.add(action)
    handler = inspect.unwrap(getattr(view, action))
    function = ast.parse(textwrap.dedent(inspect.getsource(handler))).body[0]
    body = [statement for statement in function.body if not (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )]
    if not body:
        return False
    first = body[0]
    if isinstance(first, ast.Raise) and isinstance(first.exc, ast.Call):
        exception = first.exc.func
        return isinstance(exception, ast.Name) and exception.id == 'MethodNotAllowed'

    # Only follow straight-line delegates, not conditional business rules.
    if all(isinstance(statement, ast.Assign) for statement in body[:-1]):
        last = body[-1]
        if isinstance(last, ast.Return) and isinstance(last.value, ast.Call):
            target = last.value.func
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == 'self'
                and target.attr in ('update', 'bulk_update')
            ):
                return rejects_method(view, target.attr, seen)
    return False


def check_contracts():
    from django.urls import include, path
    from drf_spectacular.generators import SchemaGenerator
    from drf_spectacular.settings import spectacular_settings
    from rest_framework.exceptions import PermissionDenied
    from rest_framework_bulk.routes import BulkRouter

    from accounts.api.account.account import AccountSecretsViewSet, AccountViewSet
    from accounts.api.account.template import AccountTemplateSecretsViewSet, AccountTemplateViewSet
    from accounts.api.automations.check_account import AccountRiskViewSet
    from accounts.urls import router as account_router
    from rbac.permissions import RBACPermission

    checked_views = {
        AccountRiskViewSet, AccountSecretsViewSet, AccountTemplateSecretsViewSet,
        AccountViewSet, AccountTemplateViewSet,
    }
    router = BulkRouter()
    for prefix, viewset, basename in account_router.registry:
        if viewset in checked_views:
            router.register(prefix, viewset, basename)
    generator = SchemaGenerator(patterns=[path('api/v1/accounts/', include(router.urls))])
    schema = generator.get_schema(public=True)
    errors = []
    checked = 0
    for raw_path, _, method, callback in generator.endpoints:
        view = generator.create_view(callback, method)
        route = generator.coerce_path(raw_path, method, view)
        if method.lower() not in schema['paths'].get(route, {}):
            continue
        checked += 1
        operation = f'{method} {route} ({type(view).__name__}.{view.action})'
        if rejects_method(view, view.action):
            errors.append(f'{operation}: documented handler always rejects the method')
        view.request = spectacular_settings.GET_MOCK_REQUEST(method, route, view, None)
        model = getattr(view, 'perm_model', None) or getattr(view, 'model', None)
        for permission in view.get_permissions():
            if isinstance(permission, RBACPermission):
                try:
                    permission._get_action_perms(view.action, model, view)
                except PermissionDenied:
                    errors.append(f'{operation}: action is missing from its RBAC permission map')
    if not checked:
        errors.append('No OpenAPI operations were checked')
    return checked, errors


def main():
    setup_django()
    checked, errors = check_contracts()
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Account API contract check passed: {checked} operations across 5 viewsets.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
