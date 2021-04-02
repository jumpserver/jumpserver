from rbac.models import SafeRoleBinding
from .models import Safe


def get_user_binding_safes(user):
    safes_ids = SafeRoleBinding.objects.filter(user=user).values_list('safe_id', flat=True)
    safes_ids = set(list(safes_ids))
    if safes_ids:
        safes = Safe.objects.filter(id__in=safes_ids)
    else:
        safes = Safe.objects.none()
    return safes
