from rest_framework.mixins import ListModelMixin, UpdateModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api import JMSGenericViewSet
from common.permissions import IsValidUser
from notifications.backends import BACKEND
from notifications.models import SystemMsgSubscription, UserMsgSubscription
from notifications.notifications import system_msgs
from notifications.serializers import (
    SystemMsgSubscriptionSerializer, SystemMsgSubscriptionByCategorySerializer,
    UserMsgSubscriptionSerializer,
)

__all__ = (
    'BackendListView', 'SystemMsgSubscriptionViewSet',
    'UserMsgSubscriptionViewSet', 'get_all_test_messages'
)


class BackendListView(APIView):
    permission_classes = [IsValidUser]

    def get(self, request):
        data = [
            {
                'name': backend,
                'name_display': backend.label
            }
            for backend in BACKEND if backend.is_enable
        ]
        return Response(data=data)


class SystemMsgSubscriptionViewSet(
    ListModelMixin, UpdateModelMixin, JMSGenericViewSet
):
    lookup_field = 'message_type'
    queryset = SystemMsgSubscription.objects.all()
    serializer_classes = {
        'list': SystemMsgSubscriptionByCategorySerializer,
        'update': SystemMsgSubscriptionSerializer,
        'partial_update': SystemMsgSubscriptionSerializer
    }
    rbac_perms = {
        '*': 'settings.change_systemmsgsubscription'
    }

    def list(self, request, *args, **kwargs):
        data = []
        category_children_mapper = {}

        subscriptions = self.get_queryset()
        msgtype_sub_mapper = {}
        for sub in subscriptions:
            msgtype_sub_mapper[sub.message_type] = sub

        for msg in system_msgs:
            message_type = msg['message_type']
            message_type_label = msg['message_type_label']
            category = msg['category']
            category_label = msg['category_label']

            if category not in category_children_mapper:
                children = []

                data.append({
                    'category': category,
                    'category_label': category_label,
                    'children': children
                })
                category_children_mapper[category] = children

            sub = msgtype_sub_mapper[message_type]
            sub.message_type_label = message_type_label
            category_children_mapper[category].append(sub)

        serializer = self.get_serializer(data, many=True)
        return Response(data=serializer.data)


class UserMsgSubscriptionViewSet(ListModelMixin,
                                 RetrieveModelMixin,
                                 UpdateModelMixin,
                                 JMSGenericViewSet):
    lookup_field = 'user_id'
    serializer_class = UserMsgSubscriptionSerializer
    permission_classes = (IsValidUser,)

    def get_queryset(self):
        queryset = UserMsgSubscription.objects.filter(user=self.request.user)
        return queryset


def get_all_test_messages(request):
    import textwrap
    from ..notifications import Message
    from django.shortcuts import HttpResponse
    if not request.user.is_superuser:
        return HttpResponse('没有权限', status=401)

    msgs_cls = Message.get_all_sub_messages()
    html_data = '<h3>HTML 格式 </h3>'
    text_data = '<h3>Text 格式</h3>'

    for msg_cls in msgs_cls:
        try:
            msg = msg_cls.gen_test_msg()
            if not msg:
                continue
            msg_html = msg.html_msg_with_sign['message']
            msg_text = msg.text_msg_with_sign['message']
        except NotImplementedError:
            msg_html = msg_text = '没有实现方法'
        except Exception as e:
            msg_html = msg_text = 'Error: ' + str(e)

        html_data += """
        <h3>{}</h3>
        {}
        <hr />
        """.format(msg_cls.__name__, msg_html)

        text_data += textwrap.dedent("""
        <h3>{}</h3>
        <pre>
        {}
        </pre>
        <br/>
        <hr />
        """).format(msg_cls.__name__, msg_text)
    return HttpResponse(html_data + text_data)
