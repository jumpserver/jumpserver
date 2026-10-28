"""Shared catalogue and permissions for the audit report workflow."""
from django.utils.translation import gettext_lazy as _

CHAPTERS = {
    'conclusion': _('Management Summary and Recommendations'),
    'overview': _('Key Overview'),
    'activity': _('Operations Activity Analysis'),
    'security': _('Security Event Analysis'),
    'inventory': _('Asset and Account Overview'),
    'account': _('Account Operations Analysis'),
    'account_health': _('Account Health'),
    'remediation': _('Remediation Checklist'),
}

THEMES = {
    'audit': {
        'title': _('Comprehensive Audit Report'),
        'description': _('Summarize operations activity, security events, assets, and accounts for monthly, quarterly, or annual audits.'),
        'chapters': ['conclusion', 'overview', 'activity', 'security', 'inventory', 'account', 'account_health', 'remediation'],
        'sources': ['sessions', 'commands', 'logins', 'operations', 'files', 'assets', 'accounts', 'automation', 'password_changes', 'account_risks'],
    },
    'activity': {
        'title': _('Operations Activity Report'),
        'description': _('Review who performed sessions, commands, and file operations on each asset.'),
        'chapters': ['conclusion', 'overview', 'activity'],
        'sources': ['sessions', 'commands', 'files', 'operations', 'logins'],
    },
    'security': {
        'title': _('Security Event Report'),
        'description': _('Review high-risk commands, login anomalies, and access denials, distinguishing failures from security events.'),
        'chapters': ['conclusion', 'overview', 'security'],
        'sources': ['commands', 'logins', 'operations'],
    },
    'inventory': {
        'title': _('Asset and Account Overview'),
        'description': '',
        'chapters': ['conclusion', 'overview', 'inventory', 'account_health'],
        'sources': ['assets', 'accounts', 'account_risks'],
    },
    'account': {
        'title': _('Account Operations Report'),
        'description': _('Review the outcomes and failures of account automation tasks.'),
        'chapters': ['conclusion', 'overview', 'account', 'account_health', 'remediation'],
        'sources': ['automation', 'password_changes', 'account_risks'],
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
    'account_risks': 'accounts.view_accountrisk',
}



def can_view_theme(user, theme):
    return any(user.has_perm(SOURCE_PERMISSIONS[source]) for source in THEMES[theme]['sources'])
