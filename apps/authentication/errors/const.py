from django.utils.translation import gettext_lazy as _


reason_password_failed = 'password_failed'
reason_password_decrypt_failed = 'password_decrypt_failed'
reason_mfa_failed = 'mfa_failed'
reason_mfa_unset = 'mfa_unset'
reason_user_not_exist = 'user_not_exist'
reason_password_expired = 'password_expired'
reason_user_invalid = 'user_invalid'
reason_user_inactive = 'user_inactive'
reason_user_expired = 'user_expired'
reason_backend_not_match = 'backend_not_match'
reason_acl_not_allow = 'acl_not_allow'
only_local_users_are_allowed = 'only_local_users_are_allowed'

reason_choices = {
    reason_password_failed: _('Username/password check failed'),
    reason_password_decrypt_failed: _('Password decrypt failed'),
    reason_mfa_failed: _('MFA failed'),
    reason_mfa_unset: _('MFA unset'),
    reason_user_not_exist: _("Username does not exist"),
    reason_password_expired: _("Password expired"),
    reason_user_invalid: _('Disabled or expired'),
    reason_user_inactive: _("This account is inactive."),
    reason_user_expired: _("This account is expired"),
    reason_backend_not_match: _("Auth backend not match"),
    reason_acl_not_allow: _("ACL is not allowed"),
    only_local_users_are_allowed: _("Only local users are allowed")
}
old_reason_choices = {
    '0': '-',
    '1': reason_choices[reason_password_failed],
    '2': reason_choices[reason_mfa_failed],
    '3': reason_choices[reason_user_not_exist],
    '4': reason_choices[reason_password_expired],
}

session_empty_msg = _("No session found, check your cookie")
invalid_login_msg = _(
    "The username or password you entered is incorrect, "
    "please enter it again. "
    "You can also try {times_try} times "
    "(The account will be temporarily locked for {block_time} minutes)"
)
block_user_login_msg = _(
    "The account has been locked "
    "(please contact admin to unlock it or try again after {} minutes)"
)
block_ip_login_msg = _(
    "The address has been locked "
    "(please contact admin to unlock it or try again after {} minutes)"
)
block_mfa_msg = _(
    "The account has been locked "
    "(please contact admin to unlock it or try again after {} minutes)"
)
mfa_error_msg = _(
    "{error}, "
    "You can also try {times_try} times "
    "(The account will be temporarily locked for {block_time} minutes)"
)
mfa_required_msg = _("MFA required")
mfa_unset_msg = _("MFA not set, please set it first")
login_confirm_required_msg = _("Login confirm required")
login_confirm_wait_msg = _("Wait login confirm ticket for accept")
login_confirm_error_msg = _("Login confirm ticket was {}")
