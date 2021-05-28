from django.http import Http404
from rest_framework.mixins import ListModelMixin, UpdateModelMixin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from common.drf.api import JmsGenericViewSet
from .notifications import system_msgs, CATEGORY
from .models import SystemMsgSubscription
from notifications.backends import BACKEND
from .serializers import (
    SystemMsgSubscriptionSerializer, SystemMsgSubscriptionByCategorySerializer
)


class BackendListView(APIView):
    def get(self, request):
        data = [
            {
                'name': backend,
                'name_display': backend.label
            }
            for backend in BACKEND
            if backend.is_enable
        ]
        return Response(data=data)


class SystemMsgSubscriptionViewSet(ListModelMixin,
                                   UpdateModelMixin,
                                   JmsGenericViewSet):
    lookup_field = 'message_type'
    queryset = SystemMsgSubscription.objects.all()
    serializer_classes = {
        'list': SystemMsgSubscriptionByCategorySerializer,
        'update': SystemMsgSubscriptionSerializer
    }

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Http404:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(message_type=self.kwargs['message_type'])
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        data = []
        category_children_mapper = {}

        for category in CATEGORY:
            children = []

            data.append({
                'category': category,
                'category_label': category.label,
                'children': children
            })
            category_children_mapper[category] = children

        subscriptions = self.get_queryset()
        msgtype_sub_mapper = {}
        for sub in subscriptions:
            msgtype_sub_mapper[sub.message_type] = sub

        for msg in system_msgs:
            message_type = msg['message_type']
            message_type_label = msg['message_type_label']
            category = msg['category']

            if message_type not in msgtype_sub_mapper:
                sub = {
                    'message_type': message_type,
                    'message_type_label': message_type_label,
                    'users': [],
                    'groups': [],
                    'receive_backends': []
                }
            else:
                sub = msgtype_sub_mapper[message_type]
                sub.message_type_label = message_type_label

            category_children_mapper[category].append(sub)

        serializer = self.get_serializer(data, many=True)
        return Response(data=serializer.data)
