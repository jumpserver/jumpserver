from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


def validate_password_contains_left_double_curly_bracket(password):
    # validate password contains left double curly bracket
    # check password not contains `{{`
    if '{{' in password:
        raise serializers.ValidationError(_('Password can not contains `{{` '))
