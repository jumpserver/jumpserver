from ..exceptions import UKeyAuthError
from .builtin import BuiltinCAProvider
from .xjca import XJCACAProvider

__all__ = ['get_provider', 'get_provider_classes']

# Only reviewed, shipped code may be registered. Settings never contain Python paths.
PROVIDERS = {
    'builtin': BuiltinCAProvider,
    'xjca': XJCACAProvider,
}


def get_provider_classes():
    return tuple(PROVIDERS.values())


def get_provider(snapshot):
    provider_class = PROVIDERS.get(snapshot['AUTH_UKEY_CA_PROVIDER'])
    if provider_class is None:
        raise UKeyAuthError('Unsupported CA provider')
    provider = provider_class(snapshot)
    if provider.id != snapshot['AUTH_UKEY_CA_PROVIDER'] or provider.binding_mode not in ('user_sn', 'certificate'):
        raise UKeyAuthError('Invalid CA provider registration')
    provider.validate_vendor()
    return provider
