"""Authoritative UKey snapshots; authentication never relies on pub/sub timing."""
from contextlib import contextmanager
from types import MappingProxyType
from uuid import uuid4

from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from .exceptions import UKeyAuthError
from .providers import get_provider, get_provider_classes


REVISION = 'AUTH_UKEY_CONFIG_REVISION'
SECRET_FIELDS = frozenset(name for provider in get_provider_classes() for name in provider.secret_fields)


def get_snapshot():
    from jumpserver.conf import Config
    from settings.models import Setting
    # A single SELECT obtains a coherent committed group, including revision.
    values = {key: getattr(settings, key, default) for key, default in Config.defaults.items()
              if key.startswith('AUTH_UKEY')}
    values.update({item.name: item.cleaned_value
                   for item in Setting.objects.filter(name__in=values)})
    return MappingProxyType(values)


def get_revision_snapshot():
    """Read SDK identity and revision in one SELECT, without loading secrets."""
    from jumpserver.conf import Config
    from settings.models import Setting
    names = ('AUTH_UKEY_CA_PROVIDER', 'AUTH_UKEY_VENDOR', REVISION)
    values = {name: getattr(settings, name, Config.defaults[name]) for name in names}
    values.update({item.name: item.cleaned_value for item in
                   Setting.objects.filter(name__in=names).only('name', 'value', 'encrypted')})
    return MappingProxyType(values)


def ensure_enabled(snapshot, provider=None):
    if not snapshot['AUTH_UKEY'] or (provider and snapshot['AUTH_UKEY_CA_PROVIDER'] != provider):
        raise UKeyAuthError('UKey provider is disabled or changed; refresh and retry')
    return get_provider(snapshot)


@contextmanager
def locked_snapshot(expected_revision, *, check_revision=True):
    """Serialize saves and final bind/login decisions (not slow network I/O)."""
    from settings.models import Setting
    with transaction.atomic():
        if not Setting.objects.filter(name=REVISION).exists():
            try:
                with transaction.atomic():
                    row = Setting(name=REVISION, value='"0"', category='ukey', comment='')
                    row._skip_settings_refresh_notification = True
                    row.save(force_insert=True)
            except IntegrityError:
                # Another request initialized the unique revision row first.
                pass
        Setting.objects.select_for_update().get(name=REVISION)
        snapshot = get_snapshot()
        if check_revision and snapshot[REVISION] != expected_revision:
            raise UKeyAuthError('UKey configuration changed; refresh and retry')
        yield snapshot


def save_settings(data, serializer_class):
    from settings.models import Setting
    try:
        with locked_snapshot(data.get(REVISION), check_revision=REVISION in data) as snapshot:
            # Legacy builtin clients do not send revisions. Permit only an
            # unchanged builtin provider/vendor, checked against the locked state.
            if REVISION not in data and (
                snapshot['AUTH_UKEY_CA_PROVIDER'] != 'builtin'
                or data.get('AUTH_UKEY_CA_PROVIDER', 'builtin') != 'builtin'
                or data.get('AUTH_UKEY_VENDOR', snapshot['AUTH_UKEY_VENDOR']) != snapshot['AUTH_UKEY_VENDOR']
            ):
                raise ValidationError({REVISION: 'Reload UKey settings before saving'})
            serializer = serializer_class(data=data, partial=True, context={'snapshot': snapshot})
            serializer.is_valid(raise_exception=True)
            changed = False
            for name, value in serializer.validated_data.items():
                if name == REVISION or (name in SECRET_FIELDS and value in ('', None)):
                    continue
                if snapshot.get(name) == value:
                    continue
                Setting.update_or_create(name, value, name in SECRET_FIELDS, 'ukey', notify=False)
                changed = True
            if changed:
                Setting.update_or_create(REVISION, uuid4().hex, False, 'ukey', notify=False)
                transaction.on_commit(publish_config_changed, robust=True)
            result = serializer_class(instance=get_snapshot()).data
    except UKeyAuthError as exc:
        raise ValidationError({REVISION: str(exc)}) from None
    return result


def publish_config_changed():
    from settings.signal_handlers import setting_pub_sub
    refresh_config()
    # No keys, PINs, certificates, passwords, or connection parameters in pub/sub.
    setting_pub_sub.publish({'event': 'UKEY_CONFIG_UPDATED'})


def refresh_config():
    from settings.signals import setting_changed
    for name, value in get_snapshot().items():
        setattr(settings, name, value)
    setting_changed.send(sender=None, name='AUTH_UKEY_CONFIG')
