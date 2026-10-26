from hashlib import sha256

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from acls.models import LoginAssetACL
from common.utils import get_request_ip_or_data
from orgs.utils import tmp_to_org

ACL_STEPS = ('reason', 'mfa', 'face', 'review', 'push_account', 'face_online')


def validate_connection_policy(token, account, *, require_complete=True):
    """Recheck the effective policy before advancing or releasing credentials."""
    context = token.acl_context or {}
    states = context.get('requirements', {})
    kwargs = {'user': token.user, 'asset': token.asset, 'account': account}
    if getattr(account, 'alias', None) == '@INPUT':
        kwargs['account_username'] = token.input_username
    policy = LoginAssetACL.get_match_rule_acls(
        token.user, token.remote_addr, LoginAssetACL.filter_queryset(**kwargs),
    )
    if policy and policy.action == 'reject':
        raise PermissionDenied(_('ACL changed; start a new connection'))
    if not policy:
        return
    controls = {
        'reason': policy.enabled('reason_enabled'),
        'mfa': policy.enabled('mfa_enabled'),
        'face': policy.enabled('face_verify_enabled') or policy.enabled('face_online_enabled'),
    }
    for control, enabled in controls.items():
        if enabled and (control not in states or (require_complete and states[control] != 'passed')):
            raise PermissionDenied(_('ACL changed; start a new connection'))
    reviews = policy.pending_reviews(token.user, token.asset, context.get('username') or getattr(account, 'username', ''))
    if reviews:
        current_ids = {str(rule.pk) for rule in reviews}
        if not current_ids.issubset(set(context.get('review_acls', []))) or 'review' not in states:
            raise PermissionDenied(_('ACL changed; start a new connection'))
    if states.get('review') == 'passed':
        get_pending_review_assignees(token)
        ticket = token.from_ticket
        if not ticket or ticket.state != 'approved' or not ticket_matches_connection(ticket, token):
            raise PermissionDenied(_('Connection approval is no longer valid'))
    if policy.enabled('face_online_enabled'):
        from authentication.api.face import FaceMonitorContext
        monitor = FaceMonitorContext.get(token.face_monitor_token) if token.face_monitor_token else None
        if not context.get('face_online') or not monitor or str(monitor.user_id) != str(token.user_id):
            raise PermissionDenied(_('Online face monitoring context is no longer available'))


def face_result(token):
    from authentication.const import FACE_CONTEXT_CACHE_KEY_PREFIX
    face_token = (token.acl_context or {}).get('face_token')
    if not face_token:
        return None
    result = cache.get(f'{FACE_CONTEXT_CACHE_KEY_PREFIX}_{face_token}')
    ids = (result or {}).get('connection_token_ids') or [str((result or {}).get('connection_token_id'))]
    if not result or str(result.get('user_id')) != str(token.user_id) or str(token.pk) not in ids:
        return None
    return result


def ticket_matches_connection(ticket, token):
    if str(ticket.apply_login_user_id) != str(token.user_id) or str(ticket.org_id) != str(token.org_id):
        return False
    connections = ticket.meta.get('login_asset_connections')
    if connections is not None:
        return any(
            (entry.get('token_id') == str(token.pk) or (
                not entry.get('token_id') and len(connections) == 1
                and str(token.from_ticket_id) == str(ticket.pk)
            )) and entry.get('asset_id') == str(token.asset_id)
            and entry.get('account') == token.acl_context.get('username')
            for entry in connections
        )
    return (str(ticket.apply_login_asset_id) == str(token.asset_id)
            and ticket.apply_login_account == token.acl_context.get('username'))


def acl_state(token):
    context = token.acl_context or {}
    error = context.get('error', '')
    reviewers = []
    review_group = ''
    review_status = ''
    if 'review' in context.get('requirements', {}):
        try:
            with tmp_to_org(token.org_id):
                rules, assignees = get_pending_review_assignees(token)
                if token.from_ticket_id:
                    review_status = token.from_ticket.state
                    assigned_ids = {user.pk for user in token.from_ticket.current_assignees}
                    assignees = [user for user in assignees if user.pk in assigned_ids]
                if assignees:
                    review_group = get_review_group_key(token.org_id, assignees)
            reviewers = [
                {'id': str(user.pk), 'name': user.name, 'username': user.username}
                for user in sorted(assignees, key=lambda user: (user.name, user.username, str(user.pk)))
            ]
        except APIException:
            # Presentation must not prevent cancelling an invalidated policy.
            # The advance/credential paths still enforce reviewer availability.
            pass
    if context.get('requirements', {}).get('face') == 'pending' and context.get('face_token'):
        result = face_result(token)
        if not result:
            error = str(_('Face verification session expired; retry verification'))
        elif result.get('is_finished') and not result.get('success'):
            error = result.get('error_message') or str(_('Face verification failed'))
    return {
        'requirements': context.get('requirements', {}),
        'reviewers': reviewers,
        'review_group': review_group,
        'review_status': review_status,
        'steps': [step for step in ACL_STEPS if step in context.get('requirements', {}) or (
            step == 'face_online' and context.get('face_online')
        )],
        'face_online': context.get('face_online', False),
        'face_online_acknowledged': context.get('face_online_acknowledged', False),
        'face_token': context.get('face_token', ''),
        'mfa_methods': [
            {'value': backend.name, 'label': str(backend.display_name), 'challenge_required': bool(backend.challenge_required())}
            for backend in token.user.active_mfa_backends if backend.has_code
        ] if 'mfa' in context.get('requirements', {}) else [],
        'cancelled': context.get('cancelled', False),
        'error': error,
        'preparation': context.get('preparation'),
    }


def check_mfa(user, request, method, code):
    from authentication import errors
    from authentication.mixins import MFAMixin
    ip = get_request_ip_or_data(request)
    mixin = MFAMixin()
    mixin.request = request
    try:
        mixin.check_mfa_is_block(user.username, ip)
        backend = user.active_mfa_backends_mapper.get(method)
        if not backend or not backend.has_code:
            raise ValidationError({'mfa_type': _('Select an active MFA method; enroll MFA first if none are available.')})
        backend.set_request(request)
        ok, message = backend.check_code(code)
        if not ok:
            raise errors.MFAFailedError(
                username=user.username, request=request, ip=ip,
                mfa_type=method, error=message,
            )

    except errors.AuthFailedError as error:
        raise ValidationError({'mfa_code': str(error)}) from error

    from users.utils import MFABlockUtils
    MFABlockUtils(user.username, ip).clean_failed_count()


def close_pending_review(ticket):
    from tickets.errors import AlreadyClosed
    try:
        ticket.close()
    except AlreadyClosed:
        # Approval and cancellation can reach the same ticket concurrently.
        pass


def close_cancelled_review(ticket):
    # Shared tickets stay open while any connection still needs approval.
    if not any(not token.acl_context.get('cancelled') and not token.is_expired
               for token in ticket.connection_tokens.all()):
        close_pending_review(ticket)


def get_review_group_key(org_id, assignees):
    """Use the same final assignee set for preview and ticket creation."""
    reviewer_ids = sorted({str(user.pk) for user in assignees})
    return sha256(f'{org_id}:{",".join(reviewer_ids)}'.encode()).hexdigest()


def get_pending_review_assignees(token):
    from tickets.models import ApplyLoginAssetTicket

    review_ids = set((token.acl_context or {}).get('review_acls', []))
    rules = list(LoginAssetACL.objects.filter(
        id__in=review_ids, is_active=True, review_enabled=True, action='accept',
    ).prefetch_related('reviewers'))
    if not rules or {str(rule.pk) for rule in rules} != review_ids:
        raise PermissionDenied(_('ACL changed; start a new connection'))
    # Apply the ticket's existing applicant rule before previewing or grouping.
    # A sole applicant remains eligible, as in ordinary ticket creation.
    assignees = ApplyLoginAssetTicket(applicant=token.user).exclude_applicant(
        LoginAssetACL.get_review_assignees(rules),
    )
    if token.from_ticket_id:
        ticket = token.from_ticket
        if not ticket_matches_connection(ticket, token):
            raise PermissionDenied(_('Connection approval is no longer valid'))
        if ticket.state == 'approved':
            processor = ticket.processor
            ticket_ids = {processor.pk} if processor else set()
        else:
            ticket_ids = {user.pk for user in ticket.current_assignees}
        if not ticket_ids.intersection(user.pk for user in assignees):
            raise PermissionDenied(_('ACL changed; start a new connection'))
    return rules, assignees


def validate_acl_step(token, step):
    context = token.acl_context or {}
    states = context.get('requirements', {})
    if context.get('cancelled') or token.is_expired or not token.user or not token.user.is_valid or not token.asset or not token.asset.is_active:
        raise PermissionDenied(_('Connection is no longer available'), code='connection_unavailable')
    account = token.get_permed_account()
    if not token.has_account_permission(account, token.protocol) or account.date_expired <= timezone.now():
        raise PermissionDenied(_('Account permission is no longer available'))
    from acls.models import ConnectMethodACL
    if not ConnectMethodACL.is_method_allowed(token.user, token.asset, token.connect_method, token.protocol):
        raise PermissionDenied(_('Connect method is not allowed for this asset'))
    validate_connection_policy(token, account, require_complete=False)
    if step:
        if step not in states and not (step == 'face_online' and context.get('face_online')):
            raise ValidationError({'step': _('This connection does not require this step')})
        if any(states.get(key, 'passed') != 'passed' for key in ACL_STEPS[:ACL_STEPS.index(step)]):
            raise ValidationError({'step': _('Complete the current connection step first')})


def advance_acl(token, request, *, mfa_verified=False, data_override=None):
    """Advance one existing connection; never recreate tokens between controls."""
    with transaction.atomic(), tmp_to_org(token.asset.org_id):
        token = type(token).objects.select_for_update().get(pk=token.pk)
        context = token.acl_context or {}
        states = context.get('requirements', {})
        from authentication.serializers.connection_token import ConnectionACLInputSerializer
        payload = request.data if data_override is None else data_override
        serializer = ConnectionACLInputSerializer(data=payload if request.method == 'POST' else {})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get('cancel'):
            context['cancelled'] = True
        if context.get('cancelled'):
            if token.from_ticket_id and token.from_ticket.status == 'open':
                ticket = token.from_ticket
                transaction.on_commit(lambda: close_cancelled_review(ticket))
            token.is_active = False
            token.acl_context = context
            token.save(update_fields=['acl_context', 'is_active'])
            return token
        step = data.get('step')
        validate_acl_step(token, step)
        if not context:
            # Older inactive tokens must still wait for their original callback.
            return token
        if step == 'face_online':
            context['face_online_acknowledged'] = True
        if states.get('reason') == 'pending' and 'reason' in data and step in (None, 'reason'):
            reason = str(data['reason']).strip()
            if not reason or len(reason) > 4096:
                raise ValidationError({'reason': _('Enter a connection reason (up to 4096 characters).')})
            context['reason'] = reason
            states['reason'] = 'passed'
        if states.get('reason') == 'passed' and context.get('reason'):
            token.comment = context['reason']
        if states.get('mfa') == 'pending' and data.get('mfa_send') and step in (None, 'mfa'):
            backend = token.user.active_mfa_backends_mapper.get(data.get('mfa_type', ''))
            if not backend or not backend.has_code or not backend.challenge_required():
                raise ValidationError({'mfa_type': _('This MFA method does not send a verification code')})
            backend.set_request(request)
            backend.send_challenge()
        if states.get('mfa') == 'pending' and 'mfa_code' in data and step in (None, 'mfa'):
            if not mfa_verified:
                check_mfa(token.user, request, data.get('mfa_type', ''), data['mfa_code'])
            states['mfa'] = 'passed'
        if states.get('face') == 'pending' and step in (None, 'face'):
            result = face_result(token)
            if result and result.get('is_finished') and result.get('success'):
                states['face'] = 'passed'
        human_ready = all(states.get(key, 'passed') == 'passed' for key in ('reason', 'mfa', 'face'))
        if states.get('review') == 'pending':
            rules, assignees = get_pending_review_assignees(token)
        if human_ready and states.get('review') == 'pending' and not token.from_ticket_id and step in (None, 'review'):
            ticket = rules[0].create_login_asset_review_ticket(
                token.user, token.asset, context['username'], assignees, token.org_id,
                review_acls=rules, reason=context.get('reason', ''),
                connections=[(token, rules)],
            )
            token.from_ticket = ticket
        if token.from_ticket_id:
            ticket = token.from_ticket
            if ticket.state == 'approved':
                states['review'] = 'passed'
            elif ticket.status == 'closed':
                states['review'] = 'failed'
                context['error'] = str(_('Connection review was rejected or closed'))
        if human_ready and states.get('review', 'passed') == 'passed' and step in (None, 'push_account') and states.get('push_account') in ('pending', 'running'):
            from accounts.provisioning import advance_account_push
            advance_account_push(token, context)
        context['requirements'] = states
        token.acl_context = context
        token.is_active = token.acl_ready
        token.save(update_fields=['acl_context', 'is_active', 'from_ticket', 'comment'])
        return token
