import json
import os
from types import SimpleNamespace

from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.template.loader import render_to_string
from rest_framework.mixins import ListModelMixin, UpdateModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api import JMSGenericViewSet
from common.permissions import IsValidUser
from common.views.template import _get_data_template_path
from notifications.backends import BACKEND
from notifications.models import SystemMsgSubscription, UserMsgSubscription
from notifications.notifications import system_msgs
from notifications.serializers import (
    SystemMsgSubscriptionSerializer, SystemMsgSubscriptionByCategorySerializer,
    UserMsgSubscriptionSerializer,
)

__all__ = (
    'BackendListView', 'SystemMsgSubscriptionViewSet',
    'UserMsgSubscriptionViewSet', 'get_all_test_messages',
    'get_templates_list', 'edit_template'
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


TEMPLATE_META = [
    {
        "template_name": "authentication/_msg_different_city.html",
        "label": "异地登录提醒邮件模板",
        "context": ["subject", "name", "username", "ip", "time", "city"],
        "context_example": [
            {"key": "subject", "label": "邮件主题", "example": "异地登录提醒"},
            {"key": "name", "label": "用户显示名", "example": "zhangsan"},
            {"key": "username", "label": "登录用户名", "example": "zhangsan"},
            {"key": "ip", "label": "登录 IP", "example": "8.8.8.8"},
            {"key": "time", "label": "发生时间", "example": "2025-09-04 10:00:00"},
            {"key": "city", "label": "城市", "example": "洛杉矶"},
        ]
    },
    {
        "template_name": "authentication/_msg_oauth_bind.html",
        "label": "第三方账号绑定提醒邮件模板",
        "context": ["subject", "name", "username", "ip", "time", "oauth_name", "oauth_id"],
        "context_example": [
            {"key": "subject", "label": "邮件主题", "example": "WeCom 绑定提醒"},
            {"key": "name", "label": "用户显示名", "example": "zhangsan"},
            {"key": "username", "label": "登录用户名", "example": "zhangsan"},
            {"key": "ip", "label": "请求 IP", "example": "8.8.8.8"},
            {"key": "time", "label": "发生时间", "example": "2025-09-04 10:00:00"},
            {"key": "oauth_name", "label": "第三方服务名", "example": "WeCom"},
            {"key": "oauth_id", "label": "第三方账号 ID", "example": "000000"},
        ]
    },
    {
        "template_name": "authentication/_msg_reset_password_code.html",
        "label": "重置密码验证码邮件模板",
        "context": ["user", "title", "code"],
        "context_example": [
            {"key": "user", "label": "用户对象（可为用户名字符串或 user 实例）", "example": "zhangsan"},
            {"key": "title", "label": "邮件标题", "example": "Jumpserver: 忘记密码"},
            {"key": "code", "label": "验证码", "example": "123456"},
        ]
    },
    {
        "template_name": "authentication/_msg_mfa_email_code.html",
        "label": "Email MFA 验证码邮件模板",
        "context": ["user", "title", "code"],
        "context_example": [
            {"key": "user", "label": "用户对象（可为用户名字符串或 user 实例）", "example": "zhangsan"},
            {"key": "title", "label": "邮件标题", "example": "Jumpserver: MFA code"},
            {"key": "code", "label": "验证码", "example": "654321"},
        ]
    },
    {
        "template_name": "ops/_msg_terminal_performance.html",
        "label": "组件性能告警邮件模板",
        "context": ["terms_with_errors"],
        "context_example": [
            {"key": "terms_with_errors", "label": "检测项与错误信息列表",
             "example": "[[\"server1\", [\"CPU 过高\", \"内存不足\"]], [\"server2\", [\"磁盘空间不足\"]]]"}
        ]
    },
    {
        "template_name": "users/_msg_user_created.html",
        "label": "用户创建通知邮件模板",
        "context": ["subject", "honorific", "content", "user", "rest_password_url", "rest_password_token",
                    "forget_password_url", "login_url"],
        "context_example": [
            {"key": "subject", "label": "邮件主题", "example": "欢迎注册"},
            {"key": "honorific", "label": "称呼", "example": "尊敬的用户"},
            {"key": "content", "label": "邮件正文模板内容", "example": "您的账号已创建"},
            {"key": "user", "label": "用户对象或用户名", "example": "zhangsan"},
            {"key": "rest_password_url", "label": "重置密码链接", "example": "https://jumpserver/reset-password"},
            {"key": "rest_password_token", "label": "重置密码 token", "example": "token123"},
            {"key": "forget_password_url", "label": "忘记密码页面链接",
             "example": "https://jumpserver/forgot-password"},
            {"key": "login_url", "label": "登录链接", "example": "https://jumpserver/login"},
        ]
    },
    {
        "template_name": "authentication/_msg_reset_password.html",
        "label": "重置密码邮件模板（含链接）",
        "context": ["user", "rest_password_url", "rest_password_token", "forget_password_url", "login_url"],
        "context_example": [
            {"key": "user", "label": "用户对象或用户名", "example": "zhangsan"},
            {"key": "rest_password_url", "label": "重置密码链接", "example": "https://jumpserver/reset-password"},
            {"key": "rest_password_token", "label": "重置密码 token", "example": "token123"},
            {"key": "forget_password_url", "label": "忘记密码页面链接",
             "example": "https://jumpserver/forgot-password"},
            {"key": "login_url", "label": "登录链接", "example": "https://jumpserver/login"},
        ]
    },
    {
        "template_name": "authentication/_msg_rest_password_success.html",
        "label": "密码重置成功通知邮件模板",
        "context": ["name", "ip_address", "browser"],
        "context_example": [
            {"key": "name", "label": "用户名或显示名", "example": "zhangsan"},
            {"key": "ip_address", "label": "请求 IP", "example": "192.168.1.1"},
            {"key": "browser", "label": "浏览器 UA", "example": "Chrome"},
        ]
    },
    {
        "template_name": "authentication/_msg_rest_public_key_success.html",
        "label": "公钥重置成功通知邮件模板",
        "context": ["name", "ip_address", "browser"],
        "context_example": [
            {"key": "name", "label": "用户名或显示名", "example": "zhangsan"},
            {"key": "ip_address", "label": "请求 IP", "example": "192.168.1.1"},
            {"key": "browser", "label": "浏览器 UA", "example": "Chrome"},
        ]
    },
    {
        "template_name": "users/_msg_password_expire_reminder.html",
        "label": "密码即将过期提醒邮件模板",
        "context": ["name", "date_password_expired", "update_password_url", "forget_password_url", "email",
                    "login_url"],
        "context_example": [
            {"key": "name", "label": "用户名或显示名", "example": "zhangsan"},
            {"key": "date_password_expired", "label": "密码过期时间（本地时区）", "example": "2025-09-30 23:59:59"},
            {"key": "update_password_url", "label": "修改密码页面链接",
             "example": "https://jumpserver/ui/#/profile/index"},
            {"key": "forget_password_url", "label": "忘记密码页面链接",
             "example": "https://jumpserver/forgot-password"},
            {"key": "email", "label": "用户邮箱", "example": "zhangsan@example.com"},
            {"key": "login_url", "label": "登录链接", "example": "https://jumpserver/login"},
        ]
    },
    {
        "template_name": "users/_msg_account_expire_reminder.html",
        "label": "账号即将过期提醒邮件模板",
        "context": ["name", "date_expired"],
        "context_example": [
            {"key": "name", "label": "用户名或显示名", "example": "zhangsan"},
            {"key": "date_expired", "label": "账号过期时间", "example": "2025-09-30 23:59:59"},
        ]
    },
    {
        "template_name": "users/_msg_reset_ssh_key.html",
        "label": "SSH Key 重置通知邮件模板",
        "context": ["name", "url"],
        "context_example": [
            {"key": "name", "label": "用户名或显示名", "example": "zhangsan"},
            {"key": "url", "label": "修改 SSH Key 链接",
             "example": "https://jumpserver/ui/#/profile/password-and-ssh-key/?tab=SSHKey"},
        ]
    },
    {
        "template_name": "users/_msg_reset_mfa.html",
        "label": "MFA 重置通知邮件模板",
        "context": ["name", "url"],
        "context_example": [
            {"key": "name", "label": "用户名或显示名", "example": "zhangsan"},
            {"key": "url", "label": "启用 MFA 链接", "example": "https://jumpserver/user-otp-enable-start"},
        ]
    }
]


def _build_render_context(example: dict):
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


def get_templates_list(request):
    """返回模板元信息和渲染后的内容。如果 data/template 中存在则读取该文件，否则使用项目中原模板渲染返回"""
    if not request.user.is_superuser:
        return HttpResponse('没有权限', status=401)

    result = []
    for meta in TEMPLATE_META:
        item = {
            'template_name': meta['template_name'],
            'label': meta.get('label', ''),
            'context': {k: '' for k in meta.get('context', [])},
            # 保持返回给前端的是 list（便于展示 key/label/example），渲染时会转换为 dict
            'context_example': meta.get('context_example', []),
            'content': None,
            'content_error': None,
            'source': None,
        }

        data_path = _get_data_template_path(meta['template_name'])
        try:
            if os.path.exists(data_path):
                # 读取已编辑的模板
                with open(data_path, 'r', encoding='utf-8') as f:
                    item['content'] = f.read()
                item['source'] = 'data'
            else:
                # 使用 render_to_string 渲染原模板
                # context_example 现在是 list of {key,label,example}，需要转换为 dict
                raw_example = meta.get('context_example', [])
                if isinstance(raw_example, list):
                    example_map = {x.get('key'): x.get('example') for x in raw_example if
                                   isinstance(x, dict) and 'key' in x}
                else:
                    example_map = raw_example or {}
                ctx = _build_render_context(example_map)
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

    return JsonResponse(result, safe=False)


def edit_template(request):
    """保存前端编辑的模板内容到 data/template/<template_name> 目录
    POST body: {"template_name": "users/_msg_x.html", "content": "<html>...</html>"}
    """
    if not request.user.is_superuser:
        return HttpResponse('没有权限', status=401)

    if request.method != 'PATCH':
        return HttpResponseBadRequest('only PATCH')

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('invalid json')

    template_name = body.get('EMAIL_TEMPLATE_NAME')
    content = body.get('EMAIL_TEMPLATE_CONTENT')
    if not template_name or content is None:
        return HttpResponseBadRequest('template_name and content required')

    data_path = _get_data_template_path(template_name)
    data_dir = os.path.dirname(data_path)
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(data_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})

    return JsonResponse({'ok': True, 'path': data_path})
