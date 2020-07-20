
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers

from users.models.user import User
from common.serializers import AdaptedBulkListSerializer
from .models import Organization, OrganizationMembers
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

    def _new_relations_by_role(self, instance, users, role):
        return (OrganizationMembers(org=instance, user=user, role=role) for user in users)

    def _create_relations(self, instance, users, admins, auditors):
        relations = []
        relations.extend(self._new_relations_by_role(instance, users, OrganizationMembers.ROLE_USER))
        relations.extend(self._new_relations_by_role(instance, admins, OrganizationMembers.ROLE_ADMIN))
        relations.extend(self._new_relations_by_role(instance, auditors, OrganizationMembers.ROLE_AUDITOR))
        OrganizationMembers.objects.bulk_create(relations)

    def _clear_relations(self, org, role):
        OrganizationMembers.objects.filter(org=org, role=role).delete()

    def create(self, validated_data):
        users = validated_data.pop('users', [])
        admins = validated_data.pop('admins', [])
        auditors = validated_data.pop('auditors', [])

        instance = Organization.objects.create(**validated_data)
        self._create_relations(instance, users, admins, auditors)

        return instance

    def _update_relations(self, instance, users_with_role):
        relations = []
        for users, role in users_with_role:
            if users is not None:
                self._clear_relations(instance, role)
                relations.extend(self._new_relations_by_role(instance, users, role))
        OrganizationMembers.objects.bulk_create(relations)

    def update(self, instance, validated_data):
        users = validated_data.pop('users', None)
        admins = validated_data.pop('admins', None)
        auditors = validated_data.pop('auditors', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        users_with_role = (
            (users, OrganizationMembers.ROLE_USER),
            (admins, OrganizationMembers.ROLE_ADMIN),
            (auditors, OrganizationMembers.ROLE_AUDITOR)
        )
        self._update_relations(instance, users_with_role)
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
