"""Shared catalogue and permissions for the audit report workflow.

Saved layouts reuse Report. Their types are intentionally absent from the
legacy catalogue so older clients cannot overwrite their configuration.
"""
from django.utils.translation import gettext_lazy as _

CHAPTERS = {
    'conclusion': _('Management Summary and Recommendations'),
    'scope': _('Data Definitions and Limitations'),
    'overview': _('Key Overview'),
    'activity': _('Operations Activity Analysis'),
    'security': _('Security Event Analysis'),
    'inventory': _('Asset and Account Overview'),
    'account': _('Account Operations Analysis'),
}

THEMES = {
    'audit': {
        'title': _('Comprehensive Audit Report'),
        'description': _('Summarize operations activity, security events, assets, and accounts for monthly, quarterly, or annual audits.'),
        'chapters': ['conclusion', 'overview', 'activity', 'security', 'inventory', 'account', 'scope'],
        'sources': ['sessions', 'commands', 'logins', 'operations', 'files', 'assets', 'accounts', 'automation', 'password_changes'],
        'legacy_types': ['userloginreport', 'userchangepasswordreport', 'assetactivityreport',
                         'assetstatisticsreport', 'accountstatisticsreport', 'accountautomationreport'],
    },
    'activity': {
        'title': _('Operations Activity Report'),
        'description': _('Review who performed sessions, commands, and file operations on each asset.'),
        'chapters': ['conclusion', 'overview', 'activity', 'scope'],
        'sources': ['sessions', 'commands', 'files', 'operations', 'logins'],
        'legacy_types': ['assetactivityreport'],
    },
    'security': {
        'title': _('Security Event Report'),
        'description': _('Review high-risk commands, login anomalies, and access denials, distinguishing failures from security events.'),
        'chapters': ['conclusion', 'overview', 'security', 'scope'],
        'sources': ['commands', 'logins', 'operations'],
        'legacy_types': ['userloginreport'],
    },
    'inventory': {
        'title': _('Asset and Account Overview'),
        'description': '',
        'chapters': ['conclusion', 'overview', 'inventory', 'scope'],
        'sources': ['assets', 'accounts'],
        'legacy_types': ['assetstatisticsreport', 'accountstatisticsreport'],
    },
    'account': {
        'title': _('Account Operations Report'),
        'description': _('Review the outcomes and failures of account automation tasks.'),
        'chapters': ['conclusion', 'overview', 'account', 'scope'],
        'sources': ['automation', 'password_changes'],
        'legacy_types': ['accountautomationreport', 'userchangepasswordreport'],
    },
}

SOURCE_PERMISSIONS = {
    'sessions': 'terminal.view_session',
    'commands': 'terminal.view_command',
    'logins': 'audits.view_userloginlog',
    'operations': 'audits.view_operatelog',
    'files': 'audits.view_ftplog',
    'assets': 'rbac.view_assetstatisticsreport',
    'accounts': 'rbac.view_accountstatisticsreport',
    'automation': 'rbac.view_accountautomationreport',
    'password_changes': 'audits.view_passwordchangelog',
}

TEMPLATE_TYPES = {theme: f'AuditReport:{theme}' for theme in THEMES}
TYPE_THEMES = {tp: theme for theme, tp in TEMPLATE_TYPES.items()}


def can_view_theme(user, theme):
    return any(user.has_perm(SOURCE_PERMISSIONS[source]) for source in THEMES[theme]['sources'])


def can_manage_template(user, theme, action='add'):
    return any(user.has_perm(f'rbac.{action}_{tp}') for tp in THEMES[theme]['legacy_types'])
