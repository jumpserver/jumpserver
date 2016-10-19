# -*- coding: utf-8 -*-
#

from rest_framework import serializers


class TerminalHeatbeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = TerminalHeatbeat
        fields = ['terminal']


if __name__ == '__main__':
    pass
