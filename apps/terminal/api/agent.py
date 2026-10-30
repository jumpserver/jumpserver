from django.db import transaction
from django.db.models import CharField, F
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import BasePermission
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from common.permissions import IsValidUser
from common.drf.filters import DatetimeRangeFilterBackend, RewriteOrderingFilter, SearchFilter
from orgs.utils import tmp_to_org, tmp_to_root_org
from terminal import agent_service as service
from terminal.const import LoginFrom
from terminal.models import AgentAction, AgentSession, Session
from terminal.filters import AgentAuditFilterBackend, AgentActionAuditFilterSet, AgentSessionAuditFilterSet
from terminal.serializers.agent import AgentActionAuditSerializer, AgentSessionAuditSerializer


class IsAgentComponent(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        terminal = getattr(user, 'terminal', None)
        return bool(
            user and user.is_authenticated and user.is_valid and user.is_service_account
            and terminal and terminal.type == 'koko' and not terminal.is_deleted
            and user.has_perm('authentication.add_superconnectiontoken')
        )


class AgentComponentAPI(APIView):
    permission_classes = [IsAgentComponent]
    operation = ''

    def post(self, request, session_id=None, action_id=None):
        if not isinstance(request.data, dict):
            raise ValidationError('Expected an object')
        node, data = request.user.terminal, request.data
        if self.operation == 'introspect':
            result = service.introspect(node, data)
        elif self.operation == 'assets':
            result = self.assets(node, data)
        elif self.operation == 'sessions':
            result = service.create_session(node, data)
        elif self.operation == 'actions':
            result = service.create_action(node, data)
        elif session_id:
            result = self.session_operation(node, session_id, data)
        elif action_id:
            result = self.action_operation(node, action_id, data)
        else:
            raise ValidationError('Invalid operation')
        response = Response(result)
        response['Cache-Control'] = 'no-store'
        return response

    @staticmethod
    def assets(node, data):
        from perms.utils import UserPermAssetUtil, PermAssetDetailUtil

        service.require_keys(data, ('context_token', 'search', 'limit', 'offset', 'asset_id', 'account_offset'), ('context_token',))
        context, user = service.context_identity(node, data['context_token'])
        limit = service.integer(data.get('limit', 20), 'limit', 1, 100)
        offset = service.integer(data.get('offset', 0), 'offset', 0, 100000)
        search = service.text_field(data.get('search', ''), 'search', 128, empty=True)
        account_offset = service.integer(data.get('account_offset', 0), 'account_offset', 0, 100000)
        with tmp_to_org(context['org_id']):
            from django.db.models import Q
            assets = UserPermAssetUtil(user).get_all_assets().filter(
                is_active=True, org_id__in=service.authorized_agent_org_ids(user, context['org_id']),
            )
            if data.get('asset_id'):
                assets = assets.filter(pk=service.identifier(data['asset_id']))
            if search:
                assets = assets.filter(Q(name__icontains=search) | Q(address__icontains=search))
            results = []
            page = list(assets.order_by('id')[offset:offset + limit + 1])
            for asset in page[:limit]:
                with tmp_to_org(asset.org_id):
                    util = PermAssetDetailUtil(user, asset)
                    protocols = sorted({item.name for item in util.get_permed_protocols_for_user()} & service.context_protocols(context).keys())
                    if not protocols:
                        continue
                    accounts, account_next = AgentComponentAPI.account_page(user, asset, util, protocols, account_offset)
                    if accounts or account_next is not None:
                        results.append({
                            'id': str(asset.id), 'name': asset.name, 'address': asset.address,
                            'org_id': asset.org_id, 'org_name': asset.org.name, 'protocols': protocols, 'accounts': accounts,
                            'accounts_next_offset': account_next,
                        })
            return {'results': results[:limit], 'next_offset': offset + limit if len(page) > limit else None}

    @staticmethod
    def account_page(user, asset, util, protocols, offset):
        from copy import copy
        # Restrict real account rows before using the existing permission
        # resolver. That resolver expands @ALL, exclusions and same-name
        # accounts correctly but normally loads every account on an asset.
        rules = [rule for rule in util.user_asset_perms if 'all' in rule.protocols or set(protocols).intersection(rule.protocols)]
        aliases = {alias for rule in rules for alias in rule.accounts}
        candidates = asset.all_valid_accounts
        same_name_exists = candidates.filter(username=user.username).exists() if '@USER' in aliases else False
        virtual = {'@INPUT', '@USER'} & aliases
        if same_name_exists:
            virtual.discard('@USER')
        if '@ALL' not in aliases:
            usernames = {alias for alias in aliases if not alias.startswith(('@', '!'))}
            if '@USER' in aliases:
                usernames.add(user.username)
            candidates = candidates.filter(username__in=usernames)
        page_size = 100 - len(virtual) if offset == 0 else 100
        ids = list(candidates.order_by('username', 'id').values_list('id', flat=True)[offset:offset + page_size + 1])
        has_more = len(ids) > page_size
        limited_asset = copy(asset)
        limited_asset.all_valid_accounts = asset.all_valid_accounts.filter(pk__in=ids[:page_size]).only(
            'id', 'name', 'username', 'asset_id', 'secret_type',
        )
        by_alias = {}
        for protocol in protocols:
            protocol_rules = [rule for rule in rules if 'all' in rule.protocols or protocol in rule.protocols]
            for account in util.get_permed_accounts_from_perms(protocol_rules, user, limited_asset):
                alias = str(account.alias)
                if account.date_expired <= timezone.now():
                    continue
                if alias.startswith('@') and (offset or alias not in virtual):
                    continue
                if alias not in by_alias:
                    by_alias[alias] = {'id': alias, 'name': account.name, 'username': account.username, 'protocols': []}
                by_alias[alias]['protocols'].append(protocol)
        accounts = sorted(by_alias.values(), key=lambda value: (value['username'], value['id']))
        return accounts, offset + page_size if has_more else None

    @transaction.atomic
    def session_operation(self, node, session_id, data):
        allowed = {
            'credentials': ('session_token', 'public_key'),
            'check': ('session_token',), 'close': ('session_token',),
            'bind': ('session_token', 'terminal_session_id'),
        }
        service.require_keys(data, allowed[self.operation], ('session_token',))
        session = service.owned_session(node, session_id, data['session_token'], lock=True, check=False)
        with tmp_to_org(session.org_id):
            if self.operation == 'close':
                actions = list(session.actions.exclude(status__in=service.FINAL_STATES).select_for_update())
                if any(action.status in ('dispatching', 'running') for action in actions):
                    raise service.Conflict('Drain or terminate running actions before closing the session')
                for action in actions:
                    action.status, action.cancel_requested, action.date_finished = 'cancelled', True, timezone.now()
                    action.save(update_fields=['status', 'cancel_requested', 'date_finished'])
                    service.finish_action_controls(action)
                service.cancel_connection_controls(session.connection_token)
                if not session.date_closed:
                    session.status, session.date_closed = 'closed', timezone.now()
                    session.save(update_fields=['status', 'date_closed'])
                if session.terminal_session_id:
                    from terminal.serializers import SessionSerializer
                    terminal = Session.objects.select_for_update().filter(pk=session.terminal_session_id).first()
                    if terminal and not terminal.is_finished:
                        SessionSerializer().update(terminal, {'is_finished': True, 'date_end': session.date_closed})
            elif self.operation == 'bind':
                service.check_session_authority(session)
                terminal_session = get_object_or_404(
                    Session, pk=service.identifier(data.get('terminal_session_id')), terminal=node,
                    user_id=str(session.user_id), asset_id=str(session.connection_token.asset_id),
                    protocol=session.requested['protocol'], is_finished=False,
                )
                from terminal.serializers import SessionSerializer
                SessionSerializer.get_connection_reason(
                    session.connection_token_id, {
                        'org_id': session.org_id, 'protocol': terminal_session.protocol,
                        'account_id': terminal_session.account_id, 'account': terminal_session.account,
                    }, session.user, session.connection_token.asset, verify_account=True,
                )
                if session.terminal_session_id and session.terminal_session_id != terminal_session.id:
                    raise service.Conflict('Agent session is already bound to another terminal session')
                Session.objects.filter(pk=terminal_session.pk).update(login_from=LoginFrom.AG)
                session.terminal_session = terminal_session
                session.save(update_fields=['terminal_session'])
            elif self.operation == 'credentials':
                from authentication.services.connection_token import get_connection_token_secret
                from authentication.serializers import ConnectionTokenSecretSerializer

                service.check_session_authority(session, connection=False)
                if session.credentials_released:
                    raise service.Conflict('Connection credentials have already been consumed')
                action = session.actions.select_for_update().get(kind='connect_asset')
                if action.cancel_requested or action.status in service.FINAL_STATES:
                    raise service.Conflict('The connection action was cancelled or completed')
                service.check_session_authority(session)
                public_key = service.text_field(data.get('public_key', ''), 'public_key', 16384, empty=True)
                result = get_connection_token_secret(
                    session.connection_token, ConnectionTokenSecretSerializer,
                    public_key=public_key, expire_now=True,
                )
                session.credentials_released, session.status = True, 'ready'
                session.save(update_fields=['credentials_released', 'status'])
                action.status, action.date_started = 'dispatching', timezone.now()
                action.save(update_fields=['status', 'date_started'])
                return result
            else:
                service.check_session_authority(session, connection=False)
                service.refresh_connection_status(session)
            result = service.session_data(session)
            result['cancel_requested_actions'] = [str(pk) for pk in session.actions.filter(
                cancel_requested=True, status__in=('dispatching', 'running'),
            ).values_list('pk', flat=True)[:32]]
            return result

    @transaction.atomic
    def action_operation(self, node, action_id, data):
        with tmp_to_root_org():
            action = get_object_or_404(
                AgentAction.objects.select_for_update(), pk=service.identifier(action_id), session__terminal=node,
            )
        with tmp_to_org(action.org_id):
            if self.operation in ('get', 'cancel'):
                service.require_keys(data, ('context_token', 'offset', 'limit'), ('context_token',))
                context, _ = service.context_identity(node, data['context_token'])
                service.same_principal(context, action.session)
                if self.operation == 'cancel' and action.status not in service.FINAL_STATES:
                    action.cancel_requested = True
                    if action.status not in ('dispatching', 'running'):
                        action.status, action.date_finished = 'cancelled', timezone.now()
                    action.save(update_fields=['cancel_requested', 'status', 'date_finished'])
                    service.finish_action_controls(action)
            else:
                session = service.owned_session(
                    node, action.session_id, data.get('session_token'), check=False,
                )
                action.session = session
                if self.operation == 'events':
                    # Evidence remains receivable after grant revocation, token
                    # expiry, session closure and execution-node restart.
                    service.append_event(action, data)
                else:
                    service.require_keys(data, ('session_token',), ('session_token',))
                    service.authorize_action(action)
                    if self.operation == 'claim':
                        claimed = action.status == 'queued' and not action.cancel_requested
                        if claimed:
                            action.status, action.date_started = 'dispatching', timezone.now()
                            action.save(update_fields=['status', 'date_started'])
                            service.notify_action_warning(action)
                        return {**service.action_data(action), 'claimed': claimed}
            result = service.action_data(action)
            if self.operation == 'get':
                offset = service.integer(data.get('offset', 0), 'offset', 0, 1000000)
                limit = service.integer(data.get('limit', 16), 'limit', 1, 32)
                # offset is the last received sequence, not a mutable row offset.
                events = list(action.events.filter(sequence__gt=offset).values(
                    'event_id', 'sequence', 'state', 'payload', 'date_received',
                )[:limit + 1])
                result['events'] = [self.event_data(action, item) for item in events[:limit]]
                result['next_offset'] = events[limit - 1]['sequence'] if len(events) > limit else None
            return result


    @staticmethod
    def event_data(action, item):
        return {**item, 'action_id': str(action.id),
                'occurred_at': item['payload'].get('_executor_occurred_at') or item['date_received'].isoformat()}


class AgentAuditAPI(GenericAPIView):
    permission_classes = [IsValidUser]
    kind = 'sessions'
    filter_backends = [AgentAuditFilterBackend, SearchFilter, RewriteOrderingFilter, DatetimeRangeFilterBackend]
    date_range_filter_fields = [('date_created', ('date_from', 'date_to'))]
    page_default_limit = 100
    page_max_limit = 100
    ordering = ('-date_created', '-id')

    @property
    def filterset_class(self):
        return AgentSessionAuditFilterSet if self.kind == 'sessions' else AgentActionAuditFilterSet

    @property
    def search_fields(self):
        fields = ['id', 'user_display', 'client_id', 'asset_id', 'account', 'protocol', 'status']
        return fields if self.kind == 'sessions' else fields + ['kind']

    @property
    def ordering_fields(self):
        fields = ['id', 'user_display', 'client_id', 'asset_id', 'account', 'protocol', 'status', 'date_created']
        return fields if self.kind == 'sessions' else fields + ['kind', 'date_started', 'date_finished']

    def get_serializer_class(self):
        return AgentSessionAuditSerializer if self.kind == 'sessions' else AgentActionAuditSerializer

    def get_queryset(self):
        model = AgentSession if self.kind == 'sessions' else AgentAction
        path = 'requested' if self.kind == 'sessions' else 'session__requested'
        queryset = service.audit_queryset(self.request.user, model).select_related('application')
        if self.kind == 'actions':
            queryset = queryset.select_related('session')
        return queryset.annotate(
            client_id=F('application__client_id'),
            **{field: Cast(KeyTextTransform(field, path), CharField())
               for field in ('asset_id', 'account', 'protocol')},
        ).order_by(*self.ordering)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        ordering = queryset.query.order_by
        if not any(field.lstrip('-') == 'id' for field in ordering):
            queryset = queryset.order_by(*ordering, '-id')
        return queryset

    def get(self, request, object_id=None):
        self.request = request
        queryset = self.get_queryset()
        try:
            offset = service.integer(int(request.query_params.get('offset', 0)), 'offset', 0, 10000000)
        except (ValueError, TypeError):
            raise ValidationError('Invalid audit offset')
        if object_id:
            item = get_object_or_404(queryset, pk=object_id)
            service.record_audit_read(item)
            result = self.serialize(item)
            if isinstance(item, AgentAction):
                result['request'] = item.request
                try:
                    after = service.integer(int(request.query_params.get('after', 0)), 'after', 0, 1000000)
                except (TypeError, ValueError):
                    raise ValidationError('Invalid evidence cursor')
                events = list(item.events.filter(sequence__gt=after).values(
                    'event_id', 'sequence', 'state', 'payload', 'date_received',
                )[:33])
                result['events'] = [AgentComponentAPI.event_data(item, event) for event in events[:32]]
                result['next_offset'] = events[31]['sequence'] if len(events) > 32 else None
            else:
                page = list(item.actions.order_by('-date_created', '-id')[offset:offset + 101])
                result['actions'] = [service.action_data(action) for action in page[:100]]
                result['next_offset'] = offset + 100 if len(page) > 100 else None
        else:
            queryset = self.filter_queryset(queryset)
            page = self.paginate_queryset(queryset)
            response = self.get_paginated_response([self.serialize(item) for item in page])
            response.data['next_offset'] = (
                self.paginator.offset + self.paginator.limit if response.data['next'] else None
            )
            response['Cache-Control'] = 'no-store'
            return response
        response = Response(result)
        response['Cache-Control'] = 'no-store'
        return response

    @staticmethod
    def serialize(item):
        parent = item if isinstance(item, AgentSession) else item.session
        context = {
            'client_id': item.application.client_id,
            'asset_id': parent.requested.get('asset_id'),
            'account': parent.requested.get('account'),
            'protocol': parent.requested.get('protocol'),
        }
        if isinstance(item, AgentAction):
            return {
                **service.action_data(item), **context, 'user_display': item.user_display,
                'user_id': str(item.user_id) if item.user_id else None, 'org_id': item.org_id,
            }
        # Never include a session capability or a connection credential in a
        # user-facing audit response.
        return {
            'id': str(item.id), 'user_id': str(item.user_id) if item.user_id else None,
            'user_display': item.user_display, 'org_id': item.org_id,
            **context,
            'status': item.status, 'terminal_session_id': item.terminal_session_id,
            'date_created': item.date_created, 'date_expires': item.date_expires,
        }
