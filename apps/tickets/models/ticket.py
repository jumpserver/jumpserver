# -*- coding: utf-8 -*-
#
import textwrap
import json
import uuid
from datetime import datetime
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _,  ugettext as __
from django.conf import settings

from perms.models import AssetPermission, Action
from common.mixins.models import CommonModelMixin
from assets.models import Asset, SystemUser
from orgs.mixins.models import OrgModelMixin
from orgs.utils import tmp_to_org, tmp_to_root_org
from .. import const

__all__ = ['Ticket', 'Comment']


class ModelJSONFieldEncoder(json.JSONEncoder):
    """ 解决一些类型的字段不能序列化的问题 """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime(settings.DATETIME_DISPLAY_FORMAT)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        else:
            return super().default(obj)


class Ticket(CommonModelMixin, OrgModelMixin):
    title = models.CharField(max_length=256, verbose_name=_("Title"))
    type = models.CharField(
        max_length=64, choices=const.TicketTypeChoices.choices,
        default=const.TicketTypeChoices.general.value, verbose_name=_("Type")
    )
    meta = models.JSONField(encoder=ModelJSONFieldEncoder, verbose_name=_("Meta"))
    action = models.CharField(
        choices=const.TicketActionChoices.choices, max_length=16, blank=True,
        default=const.TicketActionChoices.apply.value, verbose_name=_("Action")
    )
    status = models.CharField(
        max_length=16, choices=const.TicketStatusChoices.choices,
        default=const.TicketStatusChoices.open.value, verbose_name=_("Status")
    )
    # 申请人
    applicant = models.ForeignKey(
        'users.User', related_name='applied_tickets', on_delete=models.SET_NULL, null=True,
        verbose_name=_("Applicant")
    )
    applicant_display = models.CharField(
        max_length=128, verbose_name=_("Applicant display"), default=''
    )
    # 处理人
    processor = models.ForeignKey(
        'users.User', related_name='processed_tickets', on_delete=models.SET_NULL, null=True,
        verbose_name=_("Processor")
    )
    processor_display = models.CharField(
        max_length=128, blank=True, null=True, verbose_name=_("Processor display"), default=''
    )
    # 受理人列表
    assignees = models.ManyToManyField(
        'users.User', related_name='assigned_tickets', verbose_name=_("Assignees")
    )
    assignees_display = models.CharField(
        max_length=128, blank=True, verbose_name=_("Assignees display")
    )
    # 其他
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return '{}({})'.format(self.title, self.applicant_display)

    #: new
    # body
    def construct_general_body(self):
        pass

    def construct_login_confirm_body(self):
        pass

    def construct_apply_asset_body(self):
        pass

    @property
    def body(self):
        old_body = self.meta.get('body')
        if old_body:
            return old_body
        construct_body_method = getattr(self, f'construct_{self.type}_body')
        if construct_body_method:
            construct_body = construct_body_method()
        else:
            construct_body = 'No body'
        return construct_body

    def has_assignee(self, assignee):
        return self.assignees.filter(id=assignee.id).exists()

    def is_closed(self):
        return self.status == const.TicketStatusChoices.closed.value
    
    def is_approved(self):
        return self.action == const.TicketActionChoices.approve.value

    def is_rejected(self):
        return self.action == const.TicketActionChoices.reject.value

    # create relation permission
    def create_apply_asset_relation_permission(self):
        with tmp_to_root_org():
            asset_permission = AssetPermission.objects.filter(id=self.id).first()
            if asset_permission:
                return asset_permission
        approve_assets_id = self.meta['approve_assets']
        approve_system_users_id = self.meta['approve_system_users']
        approve_actions = self.meta['approve_actions']
        approve_date_start = self.meta['approve_date_start']
        approve_date_expired = self.meta['approve_date_expired']
        permission_name = __('Created by ticket ({})'.format(self.title))
        permission_comment = __(
            'Created by the ticket, '
            'ticket title: {}, '
            'ticket applicant: {}, '
            'ticket processor: {}, '
            'ticket ID: {}'
            ''.format(self.title, self.applicant_display, self.processor_display, str(self.id))
        )
        permission_data = {
            'id': self.id,
            'name': permission_name,
            'created_by': self.processor_display,
            'comment': permission_comment,
            'actions': approve_actions,
            'date_start': approve_date_start,
            'date_expired': approve_date_expired,
        }
        with tmp_to_org(self.org_id):
            asset_permission = AssetPermission.objects.create(**permission_data)
            asset_permission.users.add(self.applicant)
            asset_permission.assets.set(approve_assets_id)
            asset_permission.system_users.set(approve_system_users_id)
        return asset_permission

    def create_relation_permission(self):
        create_relation_permission_method = getattr(self, f'create_{self.type}_relation_permission')
        if create_relation_permission_method:
            create_relation_permission_method()

    # create relation comment
    def create_relation_comment(self, comment_body):
        comment_data = {
            'body': comment_body,
            'user': self.processor,
            'user_display': self.processor_display
        }
        return self.comments.create(**comment_data)

    def construct_apply_asset_relation_approved_comment_body(self):
        approve_assets_id = self.meta['approve_assets']
        approve_system_users_id = self.meta['approve_system_users']
        with tmp_to_org(self.org_id):
            approve_assets = Asset.objects.filter(id__in=approve_assets_id)
            approve_system_users = SystemUser.objects.filter(id__in=approve_system_users_id)
        approve_assets_display = [str(asset) for asset in approve_assets]
        approve_system_users_display = [str(system_user) for system_user in approve_system_users]
        approve_actions = self.meta['approve_actions']
        approve_actions_display = Action.value_to_choices_display(approve_actions)
        approve_actions_display = [str(action_display) for action_display in approve_actions_display]
        approve_date_start = self.meta['approve_date_start']
        approve_date_expired = self.meta['approve_date_expired']
        comment_body = textwrap.dedent('''
            {}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {}
        '''.format(
            __('Approved assets'), ', '.join(approve_assets_display),
            __('Approved system users'), ', '.join(approve_system_users_display),
            __('Approved actions'), ', '.join(approve_actions_display),
            __('Approved date start'), approve_date_start,
            __('Approved date expired'), approve_date_expired,
        ))
        return comment_body

    def create_relation_approved_comment(self):
        construct_relation_approved_comment_body_method = getattr(
            self, f'construct_{self.type}_relation_approved_comment_body'
        )
        if construct_relation_approved_comment_body_method:
            comment_body = construct_relation_approved_comment_body_method()
            self.create_relation_comment(comment_body)

    def create_relation_action_comment(self):
        comment_body = __(
            'User {} {} the ticket'.format(self.processor_display, self.get_action_display())
        )
        self.create_relation_comment(comment_body)

    #: old
    def create_status_comment(self, status, user):
        if status == self.STATUS.CLOSED:
            action = _("Close")
        else:
            action = _("Open")
        body = _('{} {} this ticket').format(self.user, action)
        self.comments.create(user=user, body=body)

    def perform_status(self, status, user, extra_comment=None):
        self.create_comment(
            self.STATUS.get(status),
            user,
            extra_comment
        )
        self.status = status
        self.assignee = user
        self.save()

    def create_comment(self, action_display, user, extra_comment=None):
        body = '{} {} {}'.format(user, action_display, _("this ticket"))
        if extra_comment is not None:
            body += extra_comment
        self.comments.create(body=body, user=user, user_display=str(user))

    def perform_action(self, action, user, extra_comment=None):
        self.create_comment(
            self.ACTION.get(action),
            user,
            extra_comment
        )
        self.action = action
        self.status = self.STATUS.CLOSED
        self.assignee = user
        self.save()

    def is_assignee(self, user):
        return self.assignees.filter(id=user.id).exists()

    def is_user(self, user):
        return self.user == user

    @classmethod
    def get_related_tickets(cls, user, queryset=None):
        if queryset is None:
            queryset = cls.objects.all()
        queryset = queryset.filter(
            Q(assignees=user) | Q(user=user)
        ).distinct()
        return queryset

    @classmethod
    def get_assigned_tickets(cls, user, queryset=None):
        if queryset is None:
            queryset = cls.objects.all()
        queryset = queryset.filter(assignees=user)
        return queryset

    @classmethod
    def get_my_tickets(cls, user, queryset=None):
        if queryset is None:
            queryset = cls.objects.all()
        queryset = queryset.filter(user=user)
        return queryset

    class Meta:
        ordering = ('-date_created',)


class Comment(CommonModelMixin):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, verbose_name=_("User"), related_name='comments')
    user_display = models.CharField(max_length=128, verbose_name=_("User display name"))
    body = models.TextField(verbose_name=_("Body"))

    class Meta:
        ordering = ('date_created', )
