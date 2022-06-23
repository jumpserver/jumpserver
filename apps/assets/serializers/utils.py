from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


def validate_password_for_ansible(password):
    """ 校验 Ansible 不支持的特殊字符 """
    # validate password contains left double curly bracket
    # check password not contains `{{`
    # Ansible 推送的时候不支持
    if '{{' in password:
        raise serializers.ValidationError(_('Password can not contains `{{` '))
    # Ansible Windows 推送的时候不支持
    if "'" in password:
        raise serializers.ValidationError(_("Password can not contains `'` "))
    if '"' in password:
        raise serializers.ValidationError(_('Password can not contains `"` '))

