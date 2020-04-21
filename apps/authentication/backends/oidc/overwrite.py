from django.contrib.auth import get_user_model

from oidc_rp import backends as oidc_rp_backends
from oidc_rp.models import OIDCUser


def overwrite_get_or_create_user(username, email):
    user, created = get_user_model().objects.get_or_create(username=username)
    return user


def overwrite_create_oidc_user_from_claims(claims):
    """
    Creates an ``OIDCUser`` instance using the claims extracted
    from an id_token.
    """
    sub = claims['sub']
    email = claims.get('email')
    username = claims.get('preferred_username')
    user = overwrite_get_or_create_user(username, email)
    oidc_user = OIDCUser.objects.create(user=user, sub=sub, userinfo=claims)

    return oidc_user


def overwrite_update_oidc_user_from_claims(oidc_user, claims):
    """
    Updates an ``OIDCUser`` instance using the claims extracted
    from an id_token.
    """
    oidc_user.userinfo = claims
    oidc_user.save()


# Overwrite the oidc object to fit Jumpserver


overwrite_infos = {
    oidc_rp_backends: {
        'create_oidc_user_from_claims': overwrite_create_oidc_user_from_claims,
        'update_oidc_user_from_claims': overwrite_update_oidc_user_from_claims
    },
}


def perform_overwrite():
    for overwrite_object, attrs in overwrite_infos.items():
        for attr_name, attr_value in attrs.items():
            setattr(overwrite_object, attr_name, attr_value)
