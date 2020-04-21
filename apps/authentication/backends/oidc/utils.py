__all__ = [
    'user_details_handler',
]


def user_details_handler(oidc_user, userinfo_data):
    """
    https://django-oidc-rp.readthedocs.io/en/stable/settings.html#oidc-rp-user-details-handler
    """
    name = userinfo_data.get('name')
    username = userinfo_data.get('preferred_username')
    email = userinfo_data.get('email')
    oidc_user.user.name = name or username
    oidc_user.user.username = username
    oidc_user.user.email = email
    oidc_user.user.save()
