from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import SecretType
from accounts.models import PersonalAssetCredential
from accounts.personal_credentials import (
    PERSONAL_CREDENTIAL_SECRET_CHOICES,
    PersonalCredentialVersionConflict,
    get_personal_credential_permission_context,
    validate_personal_credential_secret_type,
)
from accounts.utils import validate_account_username, validate_ssh_key
from assets.const import Connectivity, Protocol
from assets.models import Asset
from common.serializers import CommonModelSerializer
from common.serializers.fields import EncryptedField, LabeledChoiceField, ObjectRelatedField
from orgs.utils import current_org, tmp_to_org


class PersonalAssetCredentialSerializer(CommonModelSerializer):
    asset = ObjectRelatedField(
        queryset=Asset.objects, attrs=('id', 'name', 'address'),
        label=_('Asset'),
    )
    secret = EncryptedField(
        required=False, allow_blank=False, max_length=40960,
        write_only=True, label=_('Secret'),
    )
    secret_type = LabeledChoiceField(
        choices=PERSONAL_CREDENTIAL_SECRET_CHOICES,
        default=SecretType.PASSWORD,
        label=_('Secret type'),
    )
    protocol = LabeledChoiceField(
        choices=Protocol.choices, default=Protocol.ssh,
        label=_('Protocol'),
    )
    connectivity = LabeledChoiceField(
        choices=Connectivity.choices, read_only=True,
        label=_('Connectivity'),
    )
    has_secret = serializers.SerializerMethodField(label=_('Has secret'))
    version = serializers.IntegerField(read_only=True)
    expected_version = serializers.IntegerField(
        required=False, min_value=1, write_only=True,
        label=_('Expected version'),
    )

    class Meta:
        model = PersonalAssetCredential
        fields = [
            'id', 'asset', 'username', 'secret_type', 'secret', 'protocol',
            'comment', 'is_active', 'version', 'has_secret',
            'expected_version',
            'connectivity', 'date_verified', 'date_created', 'date_updated',
        ]
        read_only_fields = [
            'id', 'has_secret', 'connectivity', 'date_verified',
            'date_created', 'date_updated',
        ]

    @classmethod
    def setup_eager_loading(cls, queryset):
        # Generic pagination rebuilds the page queryset from the model manager.
        # Reapply both optimizations so list responses neither fetch/decrypt the
        # secret column nor issue one asset query per credential.
        return queryset.select_related('asset').defer('_secret')

    def validate_username(self, value):
        value = validate_account_username(value)
        if not value:
            raise serializers.ValidationError(_('This field may not be blank.'))
        return value

    @staticmethod
    def get_has_secret(instance):
        # A personal credential cannot be created without a secret. Avoid
        # touching the deferred encrypted column on list/retrieve responses.
        return True

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user if request else None
        instance = self.instance

        if instance:
            asset = instance.asset
            protocol = instance.protocol
            if 'asset' in attrs and attrs['asset'].id != instance.asset_id:
                raise serializers.ValidationError({'asset': _('Asset cannot be changed')})
            if 'protocol' in attrs and attrs['protocol'] != instance.protocol:
                raise serializers.ValidationError({'protocol': _('Protocol cannot be changed')})
            if 'expected_version' not in attrs:
                raise serializers.ValidationError({'expected_version': _('This field is required.')})
        else:
            asset = attrs.get('asset')
            protocol = attrs.get('protocol')
            if 'expected_version' in attrs:
                raise serializers.ValidationError({
                    'expected_version': _('This field is only valid when updating')
                })
            if not attrs.get('secret'):
                raise serializers.ValidationError({'secret': _('This field is required.')})

        if str(asset.org_id) != str(current_org.id):
            raise serializers.ValidationError({'asset': _('Asset is not in the current organization')})

        permission_context = get_personal_credential_permission_context(
            user, asset, protocol
        )
        self._personal_permission_context = permission_context
        platform_protocol, __ = permission_context
        secret_type = attrs.get(
            'secret_type', instance.secret_type if instance else SecretType.PASSWORD
        )
        if (
            instance
            and secret_type != instance.secret_type
            and 'secret' not in attrs
        ):
            raise serializers.ValidationError({
                'secret': _('A new secret is required when changing the secret type')
            })
        validate_personal_credential_secret_type(platform_protocol, secret_type)
        if secret_type == SecretType.SSH_KEY and attrs.get('secret'):
            attrs['secret'] = validate_ssh_key(attrs['secret'])
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        asset = validated_data['asset']
        protocol = validated_data['protocol']
        validated_data.pop('expected_version', None)
        validated_data.update({
            'owner': user,
            'created_by': str(user),
            'updated_by': str(user),
        })
        if str(asset.org_id) != str(current_org.id):
            raise serializers.ValidationError({
                'asset': _('Asset is not in the current organization')
            })
        try:
            with tmp_to_org(asset.org_id):
                permission_context = getattr(
                    self, '_personal_permission_context', None
                )
                if permission_context is None:
                    permission_context = (
                        get_personal_credential_permission_context(
                            user, asset, protocol
                        )
                    )
                platform_protocol, __ = permission_context
                validate_personal_credential_secret_type(
                    platform_protocol, validated_data['secret_type']
                )
                return super().create(validated_data)
        except IntegrityError as error:
            raise serializers.ValidationError({
                'username': _('A personal credential with these fields already exists')
            }) from error

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context['request']
        expected_version = validated_data.pop('expected_version')
        validated_data.pop('asset', None)
        validated_data.pop('protocol', None)

        if str(instance.org_id) != str(current_org.id):
            raise serializers.ValidationError({
                'asset': _('Asset is not in the current organization')
            })
        with tmp_to_org(instance.org_id):
            locked = PersonalAssetCredential.objects.select_for_update().filter(
                id=instance.id, owner=request.user
            ).first()
            if not locked:
                raise serializers.ValidationError(_('Personal credential not found'))
            permission_context = getattr(
                self, '_personal_permission_context', None
            )
            if permission_context is None:
                permission_context = get_personal_credential_permission_context(
                    request.user, locked.asset, locked.protocol
                )
            platform_protocol, __ = permission_context
            secret_type = validated_data.get('secret_type', locked.secret_type)
            validate_personal_credential_secret_type(
                platform_protocol, secret_type
            )
            if locked.version != expected_version:
                raise PersonalCredentialVersionConflict()
            validated_data['version'] = locked.version + 1
            validated_data['updated_by'] = str(request.user)
            validated_data['connectivity'] = Connectivity.UNKNOWN
            validated_data['date_verified'] = None
            try:
                return super().update(locked, validated_data)
            except IntegrityError as error:
                raise serializers.ValidationError({
                    'username': _('A personal credential with these fields already exists')
                }) from error
