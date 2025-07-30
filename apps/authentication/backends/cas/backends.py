# -*- coding: utf-8 -*-
#

from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group
from django.http import HttpRequest
from django.http import (
    HttpResponseRedirect,
)
from django_cas_ng.backends import CASBackend as _CASBackend
from django_cas_ng.signals import cas_user_authenticated
from django_cas_ng.utils import get_cas_client

from common.utils import get_logger
from ..base import JMSBaseAuthBackend

__all__ = ['CASBackend', 'CASUserDoesNotExist']
logger = get_logger(__name__)


class CASUserDoesNotExist(Exception):
    """Exception raised when a CAS user does not exist."""
    pass


class CASBackend(JMSBaseAuthBackend, _CASBackend):
    @staticmethod
    def is_enabled():
        return settings.AUTH_CAS

    def authenticate(self, request: HttpRequest, ticket: str, service: str) -> None | HttpResponseRedirect | User | Any:
        """
                Verifies CAS ticket and gets or creates User object

                :returns: [User] Authenticated User object or None if authenticate failed.
                """
        client = get_cas_client(service_url=service, request=request)
        username, attributes, pgtiou = client.verify_ticket(ticket)
        if attributes and request:
            request.session['attributes'] = attributes

        if settings.CAS_USERNAME_ATTRIBUTE != 'cas:user' and settings.CAS_VERSION != 'CAS_2_SAML_1_0':
            if attributes:
                username = attributes.get(settings.CAS_USERNAME_ATTRIBUTE)
            else:
                return None

        if not username:
            return None
        user = None
        username = self.clean_username(username)

        if attributes:
            reject = self.bad_attributes_reject(request, username, attributes)
            if reject:
                return None

            # If we can, we rename the attributes as described in the settings file
            # Existing attributes will be overwritten
            for cas_attr_name, req_attr_name in settings.CAS_RENAME_ATTRIBUTES.items():
                if cas_attr_name in attributes and cas_attr_name is not req_attr_name:
                    attributes[req_attr_name] = attributes[cas_attr_name]
                    attributes.pop(cas_attr_name)
        UserModel = get_user_model()

        # Note that this could be accomplished in one try-except clause, but
        # instead we use get_or_create when creating unknown users since it has
        # built-in safeguards for multiple threads.
        if settings.CAS_CREATE_USER:
            user_kwargs = {
                UserModel.USERNAME_FIELD: username
            }
            if settings.CAS_CREATE_USER_WITH_ID:
                user_kwargs['id'] = self.get_user_id(attributes)
            user, created = UserModel._default_manager.get_or_create(**user_kwargs)
            if created:
                user = self.configure_user(user)
        else:
            created = False
            try:
                if settings.CAS_LOCAL_NAME_FIELD:
                    user_kwargs = {
                        settings.CAS_LOCAL_NAME_FIELD: username

                    }
                    user = UserModel._default_manager.get(**user_kwargs)
                else:
                    user = UserModel._default_manager.get_by_natural_key(username)
            except UserModel.DoesNotExist:
                raise CASUserDoesNotExist(username)

        if not self.user_can_authenticate(user):
            return None

        if pgtiou and settings.CAS_PROXY_CALLBACK and request:
            request.session['pgtiou'] = pgtiou

        # Map CAS affiliations to Django groups
        if settings.CAS_MAP_AFFILIATIONS and user and attributes:
            affils = attributes.get('affiliation', [])
            for affil in affils:
                if affil:
                    g, created = Group.objects.get_or_create(name=affil)
                    user.groups.add(g)

        if settings.CAS_AFFILIATIONS_HANDLERS and user and attributes:
            affils = attributes.get('affiliation', [])
            for handler in settings.CAS_AFFILIATIONS_HANDLERS:
                if (callable(handler)):
                    handler(user, affils)

        if settings.CAS_APPLY_ATTRIBUTES_TO_USER and attributes:
            # If we are receiving None for any values which cannot be NULL
            # in the User model, set them to an empty string instead.
            # Possibly it would be desirable to let these throw an error
            # and push the responsibility to the CAS provider or remove
            # them from the dictionary entirely instead. Handling these
            # is a little ambiguous.
            user_model_fields = UserModel._meta.fields
            for field in user_model_fields:
                # Handle null -> '' conversions mentioned above
                if not field.null:
                    try:
                        if attributes[field.name] is None:
                            attributes[field.name] = ''
                    except KeyError:
                        continue
                # Coerce boolean strings into true booleans
                if field.get_internal_type() == 'BooleanField':
                    try:
                        boolean_value = attributes[field.name] == 'True'
                        attributes[field.name] = boolean_value
                    except KeyError:
                        continue
            user.__dict__.update(attributes)

            # If we are keeping a local copy of the user model we
            # should save these attributes which have a corresponding
            # instance in the DB.
            if settings.CAS_CREATE_USER:
                user.save()

        # send the `cas_user_authenticated` signal
        cas_user_authenticated.send(
            sender=self,
            user=user,
            created=created,
            username=username,
            attributes=attributes,
            pgtiou=pgtiou,
            ticket=ticket,
            service=service,
            request=request
        )
        return user
