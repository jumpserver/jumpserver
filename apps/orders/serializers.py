# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from .models import LoginConfirmOrder, Comment


class LoginConfirmOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginConfirmOrder
        fields = [
            'id', 'user', 'user_display', 'title', 'body',
            'ip', 'city', 'assignees', 'assignees_display',
            'type', 'status', 'date_created', 'date_updated',
        ]


class LoginConfirmOrderActionSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('accept', _('Accept')),
        ('reject', _('Reject')),
        ('comment', _('Comment'))
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    comment = serializers.CharField(allow_blank=True)

    def update(self, instance, validated_data):
        pass

    def create_comments(self, order, user, validated_data):
        comment_data = validated_data.get('comment')
        action = validated_data.get('action')
        comments_data = []
        if comment_data:
            comments_data.append(comment_data)
            Comment.objects.create(
                order_id=order.id, body=comment_data, user=user,
                user_display=str(user)
            )
        if action != "comment":
            action_display = dict(self.ACTION_CHOICES).get(action)
            comment_data = '{} {} {}'.format(user, action_display, _("this order"))
            comments_data.append(comment_data)
        comments = [
            Comment(order_id=order.id, body=data, user=user, user_display=str(user))
            for data in comments_data
        ]
        Comment.objects.bulk_create(comments)

    @staticmethod
    def perform_action(order, user, validated_data):
        action = validated_data.get('action')
        if action == "accept":
            status = "accepted"
        elif action == "reject":
            status = "rejected"
        else:
            status = None

        if status:
            order.status = status
            order.assignee = user
            order.assignee_display = str(user)
            order.save()

    def create(self, validated_data):
        order = self.context['order']
        user = self.context['request'].user
        self.create_comments(order, user, validated_data)
        self.perform_action(order, user, validated_data)
        return validated_data
