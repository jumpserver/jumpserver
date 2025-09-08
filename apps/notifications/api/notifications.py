import os
from types import SimpleNamespace

from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, UpdateModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api import JMSGenericViewSet
from common.permissions import OnlySuperUser, IsValidUser
from common.views.template import _get_data_template_path
from notifications.backends import BACKEND
from notifications.models import SystemMsgSubscription, UserMsgSubscription
from notifications.notifications import system_msgs
from notifications.serializers import (
    SystemMsgSubscriptionSerializer, SystemMsgSubscriptionByCategorySerializer,
    UserMsgSubscriptionSerializer,
)
from notifications.serializers import TemplateEditSerializer
from notifications.template_meta import TEMPLATE_META

__all__ = (
    'BackendListView', 'SystemMsgSubscriptionViewSet',
    'UserMsgSubscriptionViewSet', 'get_all_test_messages', 'TemplateViewSet',
)


class BackendListView(APIView):
    permission_classes = [IsValidUser]

    def get(self, request):
        data = []
        # 构造一个安全的可迭代对象，兼容 BACKEND 为可迭代或单一对象的情况
        if hasattr(BACKEND, '__iter__'):
            iterator = list(BACKEND)
        else:
            iterator = [BACKEND]

        for backend in iterator:
            # 兼容静态类型检查：确保 backend 有 is_enable 属性
            if not getattr(backend, 'is_enable', False):
                continue
            data.append({
                'name': backend,
                'name_display': getattr(backend, 'label', str(backend))
            })
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


class TemplateViewSet(JMSGenericViewSet):
    permission_classes = [OnlySuperUser]

    @staticmethod
    def _build_render_context(example):
        """将示例数据转换成可用于 render_to_string 的 context，处理一些常见对象如 user"""
        ctx = {}
        for k, v in (example or {}).items():
            if k == 'user' and isinstance(v, str):
                # 构造一个简单的 user 对象，尽量兼容模板对 user.name/user.username/user.email 的调用
                user_obj = SimpleNamespace(username=v, name=v, email=f"{v}@example.com")
                ctx[k] = user_obj
            else:
                ctx[k] = v
        return ctx

    def list(self, request):
        result = []
        for meta in TEMPLATE_META:
            item = {
                'template_name': meta['template_name'],
                'label': meta.get('label', ''),
                'context': {k: '' for k in meta.get('context', [])},
                'context_example': meta.get('context_example', []),
                'content': None,
                'content_error': None,
                'source': None,
            }

            data_path = _get_data_template_path(meta['template_name'])
            try:
                if os.path.exists(data_path):
                    with open(data_path, 'r', encoding='utf-8') as f:
                        item['content'] = f.read()
                    item['source'] = 'data'
                else:
                    raw_example = meta.get('context_example', [])
                    if isinstance(raw_example, list):
                        example_map = {x.get('key'): x.get('example') for x in raw_example if
                                       isinstance(x, dict) and 'key' in x}
                    else:
                        example_map = raw_example or {}
                    ctx = self._build_render_context(example_map)
                    try:
                        rendered = render_to_string(meta['template_name'], ctx)
                        item['content'] = rendered
                        item['source'] = 'original'
                    except Exception as e:
                        item['content_error'] = str(e)
                        item['source'] = 'original_error'
            except Exception as e:
                item['content_error'] = str(e)
            result.append(item)

        return Response(result)

    @action(detail=False, methods=['patch'], url_path='edit', name='edit')
    def edit(self, request):
        """保存前端编辑的模板内容到 data/template/<template_name> 目录"""

        serializer = TemplateEditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template_name = serializer.validated_data['EMAIL_TEMPLATE_NAME']
        content = serializer.validated_data['EMAIL_TEMPLATE_CONTENT']

        data_path = _get_data_template_path(template_name)
        data_dir = os.path.dirname(data_path)
        try:
            os.makedirs(data_dir, exist_ok=True)
            with open(data_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            return Response({'ok': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'ok': True, 'path': data_path})
