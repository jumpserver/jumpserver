# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer, OrgResourceSerializerMixin
from common.drf.serializers import SecretReadableMixin, WritableNestedModelSerializer
from common.drf.fields import ObjectRelatedField, EncryptedField
from assets.models import Platform, Node
from assets.const import SecretType, GATEWAY_NAME
from ..serializers import AssetProtocolsSerializer
from ..models import Domain, Asset, Account, Host
from .utils import validate_password_for_ansible, validate_ssh_key


class DomainSerializer(BulkOrgResourceModelSerializer):
    asset_count = serializers.SerializerMethodField(label=_('Assets amount'))
    gateway_count = serializers.SerializerMethodField(label=_('Gateways count'))
    assets = ObjectRelatedField(
        many=True, required=False, queryset=Asset.objects, label=_('Asset')
    )

    class Meta:
        model = Domain
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['comment']
        fields_m2m = ['assets']
        read_only_fields = ['asset_count', 'gateway_count', 'date_created']
        fields = fields_small + fields_m2m + read_only_fields

        extra_kwargs = {
            'assets': {'required': False, 'label': _('Assets')},
        }

    @staticmethod
    def get_asset_count(obj):
        return obj.assets.count()

    @staticmethod
    def get_gateway_count(obj):
        return obj.gateways.count()


class GatewaySerializer(BulkOrgResourceModelSerializer, WritableNestedModelSerializer):
    password = EncryptedField(
        label=_('Password'), required=False, allow_blank=True, allow_null=True, max_length=1024,
        validators=[validate_password_for_ansible], write_only=True
    )
    private_key = EncryptedField(
        label=_('SSH private key'), required=False, allow_blank=True, allow_null=True,
        max_length=16384, write_only=True
    )
    passphrase = serializers.CharField(
        label=_('Key password'), allow_blank=True, allow_null=True, required=False, write_only=True,
        max_length=512,
    )
    username = serializers.CharField(
        label=_('Username'), allow_blank=True, max_length=128, required=True, write_only=True
    )
    username_display = serializers.SerializerMethodField(label=_('Username'))
    protocols = AssetProtocolsSerializer(many=True, required=False, label=_('Protocols'))

    class Meta:
        model = Host
        fields_mini = ['id', 'name', 'address']
        fields_small = fields_mini + ['is_active', 'comment']
        fields = fields_small + ['domain', 'protocols'] + [
            'username', 'password', 'private_key', 'passphrase', 'username_display'
        ]
        extra_kwargs = {
            'name': {'label': _("Name")},
            'address': {'label': _('Address')},
        }

    @staticmethod
    def get_username_display(obj):
        account = obj.accounts.order_by('-privileged').first()
        return account.username if account else ''

    def validate_private_key(self, secret):
        if not secret:
            return
        passphrase = self.initial_data.get('passphrase')
        passphrase = passphrase if passphrase else None
        validate_ssh_key(secret, passphrase)
        return secret

    @staticmethod
    def clean_auth_fields(validated_data):
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        private_key = validated_data.pop('private_key', None)
        validated_data.pop('passphrase', None)
        return username, password, private_key

    @staticmethod
    def generate_default_data():
        platform = Platform.objects.get(name=GATEWAY_NAME, internal=True)
        # node = Node.objects.all().order_by('date_created').first()
        data = {
            'platform': platform,
        }
        return data

    @staticmethod
    def create_accounts(instance, username, password, private_key):
        account_name = f'{instance.name}-{_("Gateway")}'
        account_data = {
            'privileged': True,
            'name': account_name,
            'username': username,
            'asset_id': instance.id,
            'created_by': instance.created_by
        }
        if password:
            Account.objects.create(
                **account_data, secret=password, secret_type=SecretType.PASSWORD
            )
        if private_key:
            Account.objects.create(
                **account_data, secret=private_key, secret_type=SecretType.SSH_KEY
            )

    @staticmethod
    def update_accounts(instance, username, password, private_key):
        accounts = instance.accounts.filter(username=username)
        if password:
            account = get_object_or_404(accounts, SecretType.PASSWORD)
            account.secret = password
            account.save()
        if private_key:
            account = get_object_or_404(accounts, SecretType.SSH_KEY)
            account.secret = private_key
            account.save()

    def create(self, validated_data):
        auth_fields = self.clean_auth_fields(validated_data)
        validated_data.update(self.generate_default_data())
        instance = super().create(validated_data)
        self.create_accounts(instance, *auth_fields)
        return instance

    def update(self, instance, validated_data):
        auth_fields = self.clean_auth_fields(validated_data)
        instance = super().update(instance, validated_data)
        self.update_accounts(instance, *auth_fields)
        return instance


class GatewayWithAuthSerializer(SecretReadableMixin, GatewaySerializer):
    class Meta(GatewaySerializer.Meta):
        extra_kwargs = {
            'password': {'write_only': False},
            'private_key': {"write_only": False},
            'public_key': {"write_only": False},
        }


class DomainWithGatewaySerializer(BulkOrgResourceModelSerializer):
    gateways = GatewayWithAuthSerializer(many=True, read_only=True)

    class Meta:
        model = Domain
        fields = '__all__'
