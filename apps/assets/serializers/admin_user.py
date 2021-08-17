# -*- coding: utf-8 -*-
#
from ..models import SystemUser
from .system_user import SystemUserSerializer as SuS


class AdminUserSerializer(SuS):
    """
    管理用户
    """

    class Meta(SuS.Meta):
        fields = SuS.Meta.fields_mini + \
                 SuS.Meta.fields_write_only + \
                 SuS.Meta.fields_m2m + \
                 [
                     'type', 'protocol', "priority", 'sftp_root', 'ssh_key_fingerprint',
                     'date_created', 'date_updated', 'comment', 'created_by',
                 ]

    def validate_type(self, val):
        return SystemUser.Type.admin

    def validate_protocol(self, val):
        return 'ssh'
