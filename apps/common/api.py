# -*- coding: utf-8 -*-
#
import os
import uuid

from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, serializers

from users.models import User
from assets.models import Node
from .utils import get_object_or_none


class OutputSerializer(serializers.Serializer):
    output = serializers.CharField()
    is_end = serializers.BooleanField()
    mark = serializers.CharField()


class LogTailApi(generics.RetrieveAPIView):
    permission_classes = ()
    buff_size = 1024 * 10
    serializer_class = OutputSerializer
    end = False
    mark = ''
    log_path = ''

    def is_file_finish_write(self):
        return True

    def get_log_path(self):
        raise NotImplementedError()

    def get_no_file_message(self, request):
        return 'Not found the log'

    def filter_line(self, line):
        """
        过滤行，可能替换一些信息
        :param line:
        :return:
        """
        return line

    def read_from_file(self):
        with open(self.log_path, 'r') as f:
            offset = cache.get(self.mark, 0)
            f.seek(offset)
            data = f.read(self.buff_size).replace('\n', '\r\n')

            new_mark = str(uuid.uuid4())
            cache.set(new_mark, f.tell(), 5)

            if data == '' and self.is_file_finish_write():
                self.end = True
            _data = ''
            for line in data.split('\r\n'):
                new_line = self.filter_line(line)
                if line == '':
                    continue
                _data += new_line + '\r\n'
            return _data, self.end, new_mark

    def get(self, request, *args, **kwargs):
        self.mark = request.query_params.get("mark") or str(uuid.uuid4())
        self.log_path = self.get_log_path()

        if not self.log_path or not os.path.isfile(self.log_path):
            msg = self.get_no_file_message(self.request)
            return Response({"data": msg}, status=200)

        data, end, new_mark = self.read_from_file()
        return Response({"data": data, 'end': end, 'mark': new_mark})


class ResourcesIdCacheApi(APIView):
    def post(self, request, *args, **kwargs):
        objs_id = request.data.get('objs_id', [])
        spm = uuid.uuid4().hex
        if objs_id:
            cache.set(spm, objs_id, 300)
            return Response({'spm': spm})
        if self.request.query_params.get('resourse') == 'users':
            users = User.objects.all()
            if users:
                objs_id = [user.id for user in users]
        if self.request.query_params.get('resource') == 'assets':
            node_id = request.data.get('node_id', [])
            node = get_object_or_none(Node, id=node_id) if node_id else Node.root()
            assets = node.get_all_assets()
            if assets:
                objs_id = [asset.id for asset in assets]
        cache.set(spm, objs_id, 300)
        return Response({'spm': spm})
