import httpx
import openai
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.views import Response

from .. import serializers


class ChatAITestingAPI(GenericAPIView):
    serializer_class = serializers.ChatAISettingSerializer
    rbac_perms = {
        'POST': 'settings.change_chatai'
    }

    def get_config(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = self.serializer_class().data
        data.update(serializer.validated_data)
        for k, v in data.items():
            if v:
                continue
            # 页面没有传递值, 从 settings 中获取
            data[k] = getattr(settings, k, None)
        return data

    def post(self, request):
        config = self.get_config(request)
        chat_ai_enabled = config['CHAT_AI_ENABLED']
        if not chat_ai_enabled:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'msg': _('Chat AI is not enabled')}
            )

        proxy = config['GPT_PROXY']
        model = config['GPT_MODEL']

        kwargs = {
            'base_url': config['GPT_BASE_URL'] or None,
            'api_key': config['GPT_API_KEY'],
        }
        if proxy:
            kwargs['http_client'] = httpx.Client(
                proxies=proxy,
                transport=httpx.HTTPTransport(local_address='0.0.0.0')
            )
        client = openai.OpenAI(**kwargs)

        ok = False
        error = ''
        try:
            client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": "Say this is a test",
                    }
                ],
                model=model,
            )
            ok = True
        except openai.APIConnectionError as e:
            error = str(e.__cause__)  # an underlying Exception, likely raised within httpx.
        except openai.APIStatusError as e:
            error = str(e.message)
        except Exception as e:
            ok, error = False, str(e)

        if ok:
            _status, msg = status.HTTP_200_OK, _('Test success')
        else:
            _status, msg = status.HTTP_400_BAD_REQUEST, error

        return Response(status=_status, data={'msg': msg})
