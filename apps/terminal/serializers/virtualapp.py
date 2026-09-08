import re

from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction
from rest_framework import serializers

from common.const.choices import Status
from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from terminal.const import PublishStatus
from ..mixin import ManifestI18nMixin
from ..models import VirtualApp, VirtualAppPublication, AppProvider

__all__ = [
    'VirtualAppSerializer', 'VirtualAppPublicationSerializer'
]


class VirtualAppSerializer(ManifestI18nMixin, serializers.ModelSerializer):
    icon = serializers.ReadOnlyField(label=_("Icon"))
    image_protocol = serializers.CharField(max_length=16, default='vnc')
    image_port = serializers.IntegerField(default=5900)

    class Meta:
        model = VirtualApp
        fields_mini = ['id', 'display_name', 'name', 'image_name', 'is_active']
        read_only_fields = [
            'icon', 'readme', 'date_created', 'date_updated',
        ]
        fields = fields_mini + [
            'version', 'author', 'image_protocol', 'image_port',
            'protocols', 'tags', 'comment',
        ] + read_only_fields

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = VirtualApp.objects.select_for_update().get(pk=instance.pk)
        if (
            validated_data.get('image_name', instance.image_name) != instance.image_name
            and validated_data.get('version', instance.version) == instance.version
        ):
            raise serializers.ValidationError({
                'version': _('Changing the image requires a different application version')
            })
        image_changed = any(
            field in validated_data and validated_data[field] != getattr(instance, field)
            for field in ('version', 'image_name')
        )
        instance = super().update(instance, validated_data)
        if image_changed:
            instance.publications.update(status=PublishStatus.mismatch, app_version='', image_digest='')
        return instance


class VirtualAppPublicationSerializer(serializers.ModelSerializer):
    app = ObjectRelatedField(attrs=('id', 'name', 'image_name', 'version'), label=_("Virtual app"),
                             queryset=VirtualApp.objects.all())
    provider = ObjectRelatedField(queryset=AppProvider.objects.all(), label=_("App Provider"))
    status = LabeledChoiceField(choices=PublishStatus.choices, label=_("Status"), default=Status.pending)

    class Meta:
        model = VirtualAppPublication
        fields_mini = ['id', 'provider', 'app']
        read_only_fields = ['date_created', 'date_updated', 'date_synced']
        fields = fields_mini + [
            'status', 'app_version', 'image_digest', 'date_synced', 'comment'
        ] + ['date_created', 'date_updated']

    @transaction.atomic
    def update(self, instance, validated_data):
        sync_fields = {'status', 'app_version', 'image_digest'}
        if sync_fields & validated_data.keys():
            # Serialize reports with changes to the desired app version and
            # compare them against the latest confirmed publication state.
            app = VirtualApp.objects.select_for_update().get(pk=instance.app_id)
            instance.refresh_from_db(
                fields=sync_fields,
                from_queryset=VirtualAppPublication.objects.select_for_update(),
            )
            reported_version = validated_data.get('app_version')
            reports_success = validated_data.get('status', instance.status) == PublishStatus.success
            current_version_published = (
                instance.status == PublishStatus.success and instance.app_version == app.version
            )
            if (
                reported_version is not None and reported_version != app.version
                and (reports_success or current_version_published)
            ):
                raise serializers.ValidationError({
                    'app_version': _('Reported version does not match the current application version')
                })
            if instance.provider.host_id:
                reported_digest = validated_data.get('image_digest')
                confirmed = bool(instance.app_version and instance.image_digest)
                confirms_image = bool(
                    validated_data.get('status') == PublishStatus.success
                    and reported_version == app.version
                    and re.fullmatch(r'sha256:[a-f0-9]{64}', reported_digest or '')
                )
                # Panda verifies legacy RepoDigests against the local image
                # before reporting its ID. Migration is allowed only once.
                migrate_digest = (
                    confirms_image and reported_version == instance.app_version
                    and re.fullmatch(r'.+@sha256:[a-f0-9]{64}', instance.image_digest)
                )
                if confirmed and (not confirms_image or current_version_published):
                    if reported_version not in (None, '', instance.app_version):
                        raise serializers.ValidationError({
                            'app_version': _('Reported version does not match the confirmed publication')
                        })
                    if reported_digest not in (None, '', instance.image_digest) and not migrate_digest:
                        raise serializers.ValidationError({
                            'image_digest': _('Reported image does not match the confirmed publication')
                        })
                    if not reported_version or not reported_digest:
                        # Old Panda reports cannot verify image identity. Do
                        # not let them restore or invalidate a confirmed image.
                        validated_data.pop('status', None)
                if reports_success and not confirms_image:
                    if confirmed:
                        validated_data.pop('status', None)
                    else:
                        validated_data['status'] = PublishStatus.mismatch
                # A completed Panda pull can confirm or refresh an unpublished
                # image; failures and incomplete reports never erase identity.
                if not confirms_image:
                    validated_data.pop('app_version', None)
                    validated_data.pop('image_digest', None)
            validated_data['date_synced'] = timezone.now()
        return super().update(instance, validated_data)
