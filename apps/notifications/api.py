from rest_framework.mixins import ListModelMixin, UpdateModelMixin
from rest_framework.views import APIView
from rest_framework.response import Response

from common.drf.api import JmsGenericViewSet
from .notifications import system_msgs, CATEGORY
from .models import BACKEND, SystemMsgSubscription
from .serializers import (
    SystemMsgSubscriptionSerializer, SystemMsgSubscriptionByCategorySerializer
)


class BackendListView(APIView):
    def get(self, request):
        data = [
            {
                'name': name,
                'name_display': name_display
            }
            for name, name_display in BACKEND.choices
            if BACKEND.is_backend_enable(name)
        ]
        return Response(data=data)


class SystemMsgSubscriptionViewSet(ListModelMixin, UpdateModelMixin, JmsGenericViewSet):
    queryset = SystemMsgSubscription.objects.all()
    serializer_classes = {
        'list': SystemMsgSubscriptionByCategorySerializer
    }

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

        msgs = self.get_queryset()

        for msg in msgs:
            msg_info = system_msgs[msg.message_type]
            msg.message_type_label = msg_info['message_type_label']

            category_children_mapper[msg_info['category']].append(msg)

        serializer = self.get_serializer(data, many=True)
        return Response(data=serializer.data)
