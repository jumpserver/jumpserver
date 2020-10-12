
from django.db import transaction
from rest_framework import serializers

from .models import Account, AccountType, PropField


class AccountSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='type.name', read_only=True)
    namespace_display = serializers.CharField(source='namespace.name', read_only=True)

    class Meta:
        model = Account
        fields = (
            'id', 'name', 'username', 'address', 'secret', 'secret_type',
            'type', 'type_display', 'extra_props', 'namespace', 'namespace_display',
            'comment', 'created_by', 'date_created', 'date_updated',
        )
        read_only_fields = ('id', 'type_display', 'namespace_display', 'created_by')
        extra_kwargs = {
            'secret': {'write_only': True}
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        account_type = ''
        request = self.context.get('request')
        if request:
            account_type = request.query_params.get('account_type')
        if hasattr(self, 'initial_data'):
            account_type = self.initial_data.get('type')
        if not account_type:
            return
        tp = AccountType.objects.filter(id=account_type).first()
        if not tp:
            return
        self.fields['extra_props'] = tp.generate_serializer()()

    def create(self, validated_data):
        extra_props = validated_data.pop('extra_props', {})
        with transaction.atomic():
            instance = super(AccountSerializer, self).create(validated_data)
            instance.create_secret(validated_data['secret'])
            instance.save_extra_props(extra_props)
        return instance

    def update(self, instance, validated_data):
        secret = validated_data.get('secret')
        extra_props = validated_data.pop('extra_props', None)
        with transaction.atomic():
            instance = super(AccountSerializer, self).update(instance, validated_data)
            if secret:
                instance.update_secret(secret)
            if extra_props:
                instance.save_extra_props(extra_props)
        return instance


class AccountWithSecretSerializer(AccountSerializer):

    class Meta:
        model = Account
        fields = (
            'id', 'name', 'username', 'address', 'secret', 'secret_type',
            'type', 'type_display', 'extra_props', 'namespace', 'namespace_display',
            'comment', 'created_by', 'date_created', 'date_updated',
        )

    def to_representation(self, instance):
        data = super(AccountWithSecretSerializer, self).to_representation(instance)
        data['secret'] = instance.get_secret()
        return data


class PropFieldSerializer(serializers.ModelSerializer):

    class Meta:
        model = PropField
        fields = (
            'id', 'name', 'type', 'default', 'choices', 'required',
        )
        read_only_fields = ('id',)


class AccountTypeSerializer(serializers.ModelSerializer):
    new_prop_fields = PropFieldSerializer(many=True, required=False, write_only=True)
    prop_fields_info = serializers.SerializerMethodField()

    class Meta:
        model = AccountType
        fields = (
            'id', 'name', 'category', 'base_type', 'protocol', 'prop_fields',
            'prop_fields_info', 'new_prop_fields', 'created_by', 'date_created', 'date_updated',
        )
        read_only_fields = ('id', 'created_by')
        extra_kwargs = {'prop_fields': {'allow_empty': True}}

    @staticmethod
    def get_prop_fields_info(obj):
        prop_fields = obj.prop_fields.all()
        serializer = PropFieldSerializer(prop_fields, many=True)
        return serializer.data

    def save(self, **kwargs):
        new_prop_fields = self.validated_data.pop('new_prop_fields', [])
        with transaction.atomic():
            instance = super(AccountTypeSerializer, self).save(**kwargs)
            for field in new_prop_fields:
                field_obj = PropField.objects.create(**field)
                instance.prop_fields.add(field_obj)
        return instance
