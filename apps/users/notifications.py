from datetime import datetime

from django.utils.translation import ugettext as _

from common.utils import reverse, get_request_ip_or_data, get_request_user_agent, lazyproperty
from notifications.notifications import UserMessage


class BaseUserMessage(UserMessage):
    def get_text_msg(self) -> dict:
        raise NotImplementedError

    def get_html_msg(self) -> dict:
        raise NotImplementedError

    @lazyproperty
    def text_msg(self) -> dict:
        return self.get_text_msg()

    @lazyproperty
    def html_msg(self) -> dict:
        return self.get_html_msg()

    def get_dingtalk_msg(self) -> dict:
        return self.text_msg

    def get_wecom_msg(self) -> dict:
        return self.text_msg

    def get_feishu_msg(self) -> dict:
        return self.text_msg

    def get_email_msg(self) -> dict:
        return self.html_msg

    def get_site_msg_msg(self) -> dict:
        return self.html_msg


class ResetPasswordMsg(BaseUserMessage):
    def get_text_msg(self) -> dict:
        user = self.user
        subject = _('Reset password')
        message = _("""
Hello %(name)s:
Please click the link below to reset your password, if not your request, concern your account security

Click here reset password 👇
%(rest_password_url)s?token=%(rest_password_token)s

This link is valid for 1 hour. After it expires, 

request new one 👇
%(forget_password_url)s?email=%(email)s

-------------------

Login direct 👇
%(login_url)s

""") % {
            'name': user.name,
            'rest_password_url': reverse('authentication:reset-password', external=True),
            'rest_password_token': user.generate_reset_token(),
            'forget_password_url': reverse('authentication:forgot-password', external=True),
            'email': user.email,
            'login_url': reverse('authentication:login', external=True),
        }
        return {
            'subject': subject,
            'message': message
        }

    def get_html_msg(self) -> dict:
        user = self.user
        subject = _('Reset password')
        message = _("""
            Hello %(name)s:
            <br>
            Please click the link below to reset your password, if not your request, concern your account security
            <br>
            <a href="%(rest_password_url)s?token=%(rest_password_token)s">Click here reset password</a>
            <br>
            This link is valid for 1 hour. After it expires, <a href="%(forget_password_url)s?email=%(email)s">request new one</a>
        
            <br>
            ---
        
            <br>
            <a href="%(login_url)s">Login direct</a>
        
            <br>
            """) % {
            'name': user.name,
            'rest_password_url': reverse('authentication:reset-password', external=True),
            'rest_password_token': user.generate_reset_token(),
            'forget_password_url': reverse('authentication:forgot-password', external=True),
            'email': user.email,
            'login_url': reverse('authentication:login', external=True),
        }
        return {
            'subject': subject,
            'message': message
        }


class ResetPasswordSuccessMsg(BaseUserMessage):
    def __init__(self, user, request):
        super().__init__(user)
        self.ip_address = get_request_ip_or_data(request)
        self.browser = get_request_user_agent(request)

    def get_text_msg(self) -> dict:
        user = self.user

        subject = _('Reset password success')
        message = _("""
        
Hi %(name)s:

Your JumpServer password has just been successfully updated.

If the password update was not initiated by you, your account may have security issues. 
It is recommended that you log on to the JumpServer immediately and change your password.

If you have any questions, you can contact the administrator.

-------------------


IP Address: %(ip_address)s
<br>
<br>
Browser: %(browser)s
<br>
        
        """) % {
            'name': user.name,
            'ip_address': self.ip_address,
            'browser': self.browser,
        }
        return {
            'subject': subject,
            'message': message
        }

    def get_html_msg(self) -> dict:
        user = self.user

        subject = _('Reset password success')
        message = _("""
        
        Hi %(name)s:
        <br>
        
        
        <br>
        Your JumpServer password has just been successfully updated.
        <br>
        
        <br>
        If the password update was not initiated by you, your account may have security issues. 
        It is recommended that you log on to the JumpServer immediately and change your password.
        <br>

        <br>
        If you have any questions, you can contact the administrator.
        <br>
        <br>
        ---
        <br>
        <br>
        IP Address: %(ip_address)s
        <br>
        <br>
        Browser: %(browser)s
        <br>
        
        """) % {
            'name': user.name,
            'ip_address': self.ip_address,
            'browser': self.browser,
        }
        return {
            'subject': subject,
            'message': message
        }


class PasswordExpirationReminderMsg(BaseUserMessage):
    def get_text_msg(self) -> dict:
        user = self.user

        subject = _('Security notice')
        message = _("""
Hello %(name)s:

Your password will expire in %(date_password_expired)s,

For your account security, please click on the link below to update your password in time

Click here update password 👇
%(update_password_url)s

If your password has expired, please click 👇 to apply for a password reset email.
%(forget_password_url)s?email=%(email)s

-------------------

Login direct 👇
%(login_url)s

        """) % {
            'name': user.name,
            'date_password_expired': datetime.fromtimestamp(datetime.timestamp(
                user.date_password_expired)).strftime('%Y-%m-%d %H:%M'),
            'update_password_url': reverse('users:user-password-update', external=True),
            'forget_password_url': reverse('authentication:forgot-password', external=True),
            'email': user.email,
            'login_url': reverse('authentication:login', external=True),
        }
        return {
            'subject': subject,
            'message': message
        }

    def get_html_msg(self) -> dict:
        user = self.user

        subject = _('Security notice')
        message = _("""
        Hello %(name)s:
        <br>
        Your password will expire in %(date_password_expired)s,
        <br>
        For your account security, please click on the link below to update your password in time
        <br>
        <a href="%(update_password_url)s">Click here update password</a>
        <br>
        If your password has expired, please click 
        <a href="%(forget_password_url)s?email=%(email)s">Password expired</a> 
        to apply for a password reset email.
    
        <br>
        ---
    
        <br>
        <a href="%(login_url)s">Login direct</a>
    
        <br>
        """) % {
            'name': user.name,
            'date_password_expired': datetime.fromtimestamp(datetime.timestamp(
                user.date_password_expired)).strftime('%Y-%m-%d %H:%M'),
            'update_password_url': reverse('users:user-password-update', external=True),
            'forget_password_url': reverse('authentication:forgot-password', external=True),
            'email': user.email,
            'login_url': reverse('authentication:login', external=True),
        }
        return {
            'subject': subject,
            'message': message
        }


class UserExpirationReminderMsg(BaseUserMessage):
    def get_text_msg(self) -> dict:
        subject = _('Expiration notice')
        message = _("""
Hello %(name)s:

Your account will expire in %(date_expired)s,

In order not to affect your normal work, please contact the administrator for confirmation.

           """) % {
                'name': self.user.name,
                'date_expired': datetime.fromtimestamp(datetime.timestamp(
                    self.user.date_expired)).strftime('%Y-%m-%d %H:%M'),
        }
        return {
            'subject': subject,
            'message': message
        }

    def get_html_msg(self) -> dict:
        subject = _('Expiration notice')
        message = _("""
           Hello %(name)s:
           <br>
           Your account will expire in %(date_expired)s,
           <br>
           In order not to affect your normal work, please contact the administrator for confirmation.
           <br>
           """) % {
                'name': self.user.name,
                'date_expired': datetime.fromtimestamp(datetime.timestamp(
                    self.user.date_expired)).strftime('%Y-%m-%d %H:%M'),
        }
        return {
            'subject': subject,
            'message': message
        }


class ResetSSHKeyMsg(BaseUserMessage):
    def get_text_msg(self) -> dict:
        subject = _('SSH Key Reset')
        message = _("""
Hello %(name)s:

Your ssh public key has been reset by site administrator.
Please login and reset your ssh public key.

Login direct 👇
%(login_url)s

        """) % {
            'name': self.user.name,
            'login_url': reverse('authentication:login', external=True),
        }

        return {
            'subject': subject,
            'message': message
        }

    def get_html_msg(self) -> dict:
        subject = _('SSH Key Reset')
        message = _("""
        Hello %(name)s:
        <br>
        Your ssh public key has been reset by site administrator.
        Please login and reset your ssh public key.
        <br>
        <a href="%(login_url)s">Login direct</a>
    
        <br>
        """) % {
            'name': self.user.name,
            'login_url': reverse('authentication:login', external=True),
        }

        return {
            'subject': subject,
            'message': message
        }


class ResetMFAMsg(BaseUserMessage):
    def get_text_msg(self) -> dict:
        subject = _('MFA Reset')
        message = _("""
Hello %(name)s:

Your MFA has been reset by site administrator.
Please login and reset your MFA.

Login direct 👇 
%(login_url)s

        """) % {
            'name': self.user.name,
            'login_url': reverse('authentication:login', external=True),
        }
        return {
            'subject': subject,
            'message': message
        }

    def get_html_msg(self) -> dict:
        subject = _('MFA Reset')
        message = _("""
        Hello %(name)s:
        <br>
        Your MFA has been reset by site administrator.
        Please login and reset your MFA.
        <br>
        <a href="%(login_url)s">Login direct</a>
    
        <br>
        """) % {
            'name': self.user.name,
            'login_url': reverse('authentication:login', external=True),
        }
        return {
            'subject': subject,
            'message': message
        }
