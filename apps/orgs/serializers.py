
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers

from users.models.user import User
from common.serializers import AdaptedBulkListSerializer
from .models import Organization, OrganizationMember
from .mixins.serializers import OrgMembershipSerializerMixin


class OrgSerializer(ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), write_only=True)
    admins = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), write_only=True)
    auditors = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), write_only=True)

    class Meta:
        model = Organization
        list_serializer_class = AdaptedBulkListSerializer
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'created_by', 'date_created', 'comment'
        ]
        fields_m2m = ['users', 'admins', 'auditors']
        fields = fields_small + fields_m2m
        read_only_fields = ['created_by', 'date_created']

    def create(self, validated_data):
        members = self._pop_memebers(validated_data)
        instance = Organization.objects.create(**validated_data)
        OrganizationMember.objects.add_users_by_role(instance, *members)
        return instance

    def _pop_memebers(self, validated_data):
        return (
            validated_data.pop('users', None),
            validated_data.pop('admins', None),
            validated_data.pop('auditors', None)
        )

    def update(self, instance, validated_data):
        members = self._pop_memebers(validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        OrganizationMember.objects.set_users_by_role(instance, *members)
        return instance


class OrgReadSerializer(OrgSerializer):
    pass


class OrgMembershipAdminSerializer(OrgMembershipSerializerMixin, ModelSerializer):
    class Meta:
        model = Organization.members.through
        list_serializer_class = AdaptedBulkListSerializer
        fields = '__all__'


class OrgMembershipUserSerializer(OrgMembershipSerializerMixin, ModelSerializer):
    class Meta:
        model = Organization.members.through
        list_serializer_class = AdaptedBulkListSerializer
        fields = '__all__'


class OrgAllUserSerializer(serializers.Serializer):
    user = serializers.UUIDField(read_only=True, source='id')
    user_display = serializers.SerializerMethodField()

    class Meta:
        only_fields = ['id', 'username', 'name']

    @staticmethod
    def get_user_display(obj):
        return str(obj)


class OrgRetrieveSerializer(OrgReadSerializer):
    admins = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    auditors = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    users = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta(OrgReadSerializer.Meta):
        pass
