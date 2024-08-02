# -*- coding: utf-8 -*-
#
from celery import shared_task
from django.conf import settings
from django.contrib.auth.signals import user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django_auth_ldap.backend import populate_user
from django_cas_ng.signals import cas_user_authenticated

from audits.models import UserSession
from authentication.backends.oauth2.signals import oauth2_create_or_update_user
from authentication.backends.oidc.signals import openid_create_or_update_user
from authentication.backends.radius.signals import radius_create_user
from authentication.backends.saml2.signals import saml2_create_or_update_user
from common.const.crontab import CRONTAB_AT_AM_TWO
from common.decorators import on_transaction_commit
from common.sessions.cache import user_session_manager
from common.signals import django_ready
from common.utils import get_logger
from jumpserver.utils import get_current_request
from ops.celery.decorator import register_as_period_task
from rbac.builtin import BuiltinRole
from rbac.const import Scope
from rbac.models import RoleBinding
from settings.signals import setting_changed
from .models import User, UserPasswordHistory
from .signals import post_user_create

logger = get_logger(__file__)


def check_only_allow_exist_user_auth(created):
    if created and settings.ONLY_ALLOW_EXIST_USER_AUTH:
        request = get_current_request()
        request.user_need_delete = True
        request.error_message = _(
            '''The administrator has enabled "Only allow existing users to log in", 
            and the current user is not in the user list. Please contact the administrator.'''
        )
        return False
    return True


def user_authenticated_handle(user, created, source, attrs=None, **kwargs):
    if not check_only_allow_exist_user_auth(created):
        return

    if created:
        user.source = source
        user.save()
        bind_user_to_org_role(user)

    if not attrs:
        return

    always_update = getattr(settings, 'AUTH_%s_ALWAYS_UPDATE_USER' % source.upper(), False)
    if not created and always_update:
        attr_whitelist = ('user', 'username', 'email', 'phone', 'comment')
        logger.debug(
            "Receive {} user updated signal: {}, "
            "Update user info: {},"
            "(Update only properties in the whitelist. [{}])"
            "".format(source, user, str(attrs), ','.join(attr_whitelist))
        )
        for key, value in attrs.items():
            if key in attr_whitelist and value:
                setattr(user, key, value)
        user.save()


@receiver(post_save, sender=User)
def save_passwd_change(sender, instance: User, **kwargs):
    if instance.source != User.Source.local.value or not instance.password:
        return

    passwords = UserPasswordHistory.objects \
                    .filter(user=instance) \
                    .order_by('-date_created') \
                    .values_list('password', flat=True)[:settings.OLD_PASSWORD_HISTORY_LIMIT_COUNT]

    if instance.password not in list(passwords):
        UserPasswordHistory.objects.create(
            user=instance, password=instance.password,
            date_created=instance.date_password_last_updated
        )


def update_role_superuser_if_need(user):
    if not user._update_superuser:
        return
    value = user._is_superuser
    if value:
        user.system_roles.add_role_system_admin()
    else:
        user.system_roles.remove_role_system_admin()


@receiver(post_save, sender=User)
@on_transaction_commit
def on_user_create_set_default_system_role(sender, instance, created, **kwargs):
    update_role_superuser_if_need(instance)
    if not created:
        return
    has_system_role = instance.system_roles.all().exists()
    if not has_system_role:
        logger.debug("Receive user create signal, set default role")
        instance.system_roles.add_role_system_user()


@receiver(post_user_create)
def on_user_create(sender, user=None, **kwargs):
    logger.debug("Receive user `{}` create signal".format(user.name))
    from .utils import send_user_created_mail
    logger.info("   - Sending welcome mail ...".format(user.name))
    request = get_current_request()
    password_strategy = getattr(request, 'password_strategy', '')
    if user.can_send_created_mail() and password_strategy == 'email':
        send_user_created_mail(user)


@receiver(cas_user_authenticated)
def on_cas_user_authenticated(sender, user, created, **kwargs):
    source = user.Source.cas.value
    user_authenticated_handle(user, created, source)


@receiver(saml2_create_or_update_user)
def on_saml2_create_or_update_user(sender, user, created, attrs, **kwargs):
    source = user.Source.saml2.value
    user_authenticated_handle(user, created, source, attrs, **kwargs)


@receiver(oauth2_create_or_update_user)
def on_oauth2_create_or_update_user(sender, user, created, attrs, **kwargs):
    source = user.Source.oauth2.value
    user_authenticated_handle(user, created, source, attrs, **kwargs)


@receiver(radius_create_user)
def radius_create_user(sender, user, **kwargs):
    user.source = user.Source.radius.value
    user.save()
    bind_user_to_org_role(user)


@receiver(openid_create_or_update_user)
def on_openid_create_or_update_user(sender, request, user, created, name, username, email, **kwargs):
    if not check_only_allow_exist_user_auth(created):
        return

    if created:
        logger.debug(
            "Receive OpenID user created signal: {}, "
            "Set user source is: {}".format(user, User.Source.openid.value)
        )
        user.source = User.Source.openid.value
        user.save()
        bind_user_to_org_role(user)

    if not created and settings.AUTH_OPENID_ALWAYS_UPDATE_USER:
        logger.debug(
            "Receive OpenID user updated signal: {}, "
            "Update user info: {}"
            "".format(user, "name: {}|username: {}|email: {}".format(name, username, email))
        )
        user.name = name
        user.username = username
        user.email = email
        user.save()


@receiver(populate_user)
def on_ldap_create_user(sender, user, ldap_user, **kwargs):
    if user and user.username not in ['admin']:
        exists = User.objects.filter(username=user.username).exists()
        if not exists:
            user.source = user.Source.ldap.value
            user.save()


@shared_task(verbose_name=_('Clean up expired user sessions'))
@register_as_period_task(crontab=CRONTAB_AT_AM_TWO)
def clean_expired_user_session_period():
    UserSession.clear_expired_sessions()


@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    session_key = request.session.session_key
    user_session_manager.remove(session_key)
    UserSession.objects.filter(key=session_key).delete()


@receiver(setting_changed)
@on_transaction_commit
def on_auth_setting_changed_clear_source_choice(sender, name='', **kwargs):
    if name.startswith('AUTH_'):
        User._source_choices = []


@receiver(django_ready)
def on_django_ready_refresh_source(sender, **kwargs):
    User._source_choices = []


def bind_user_to_org_role(user):
    source = user.source.upper()
    org_ids = getattr(settings, f"{source}_ORG_IDS", None)

    if not org_ids:
        logger.error(f"User {user} has no {source} orgs")
        return

    org_role_ids = [BuiltinRole.org_user.id]

    bindings = [
        RoleBinding(
            user=user, org_id=org_id, scope=Scope.org,
            role_id=role_id,
        )
        for role_id in org_role_ids
        for org_id in org_ids
    ]

    RoleBinding.objects.bulk_create(bindings, ignore_conflicts=True)
