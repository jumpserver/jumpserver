# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from common.fields import ChoiceDisplayField
from ..models import CommandFilter, CommandFilterRule, SystemUser


class CommandFilterSerializer(serializers.ModelSerializer):
    rules = serializers.PrimaryKeyRelatedField(queryset=CommandFilterRule.objects.all(), many=True)
    system_users = serializers.PrimaryKeyRelatedField(queryset=SystemUser.objects.all(), many=True)

    class Meta:
        model = CommandFilter
        fields = '__all__'


class CommandFilterRuleSerializer(serializers.ModelSerializer):
    serializer_choice_field = ChoiceDisplayField

    class Meta:
        model = CommandFilterRule
        fields = '__all__'
