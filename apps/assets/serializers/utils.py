from io import StringIO

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.utils import ssh_private_key_gen, validate_ssh_private_key


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


def validate_ssh_key(ssh_key, passphrase=None):
    valid = validate_ssh_private_key(ssh_key, password=passphrase)
    if not valid:
        raise serializers.ValidationError(_("private key invalid or passphrase error"))

    ssh_key = ssh_private_key_gen(ssh_key, password=passphrase)
    string_io = StringIO()
    ssh_key.write_private_key(string_io)
    ssh_key = string_io.getvalue()
    return ssh_key
