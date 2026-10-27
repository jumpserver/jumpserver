from collections import defaultdict

from orgs.utils import tmp_to_org
from .connection_acl import (
    advance_acl, check_mfa, get_pending_review_assignees, get_review_group_key, validate_acl_step,
)


def advance_acl_batch(tokens, request, data):
    """Share identity checks, never asset permissions or approval authority."""
    step = data['step']
    for token in tokens:
        with tmp_to_org(token.org_id):
            validate_acl_step(token, step)
    verified = step == 'mfa' and 'mfa_code' in data
    if verified and any(token.acl_context['requirements'].get('mfa') == 'pending' for token in tokens):
        check_mfa(request.user, request, data.get('mfa_type', ''), data['mfa_code'])
    if step == 'review':
        create_batch_reviews(tokens)
    payload = {key: value for key, value in request.data.items() if key != 'token_ids'}
    # A challenge belongs to the user, so send it once for the whole batch.
    for index, token in enumerate(tokens):
        current = dict(payload)
        if index:
            current.pop('mfa_send', None)
        tokens[index] = advance_acl(
            token, request, mfa_verified=verified, data_override=current,
        )
    return tokens


def create_batch_reviews(tokens):
    groups = defaultdict(list)
    for token in tokens:
        if token.from_ticket_id or token.acl_context['requirements'].get('review') != 'pending':
            continue
        with tmp_to_org(token.org_id):
            rules, assignees = get_pending_review_assignees(token)
        key = get_review_group_key(token.org_id, assignees, rules, token.user_id)
        groups[key].append((token, rules, assignees))
    for entries in groups.values():
        token, rules, assignees = entries[0]
        with tmp_to_org(token.org_id):
            ticket = rules[0].create_login_asset_review_ticket(
                token.user, token.asset, token.acl_context['username'], assignees, token.org_id,
                review_acls=rules, reason=token.acl_context.get('reason', ''),
                connections=[(item, item_rules) for item, item_rules, _ in entries],
            )
            for item, _, _ in entries:
                item.from_ticket = ticket
                item.save(update_fields=['from_ticket'])
