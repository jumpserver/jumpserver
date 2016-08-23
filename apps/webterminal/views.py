from django.shortcuts import render
from django.urls import reverse_lazy
from django.db.models import Q
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.detail import DetailView
from django.views.generic.base import TemplateView
from django.views import View
from django.http import HttpResponse
from ws4redis.redis_store import RedisMessage
from ws4redis.publisher import RedisPublisher
from django.conf import settings


# Create your views here.
class TerminalView(TemplateView):
    template_name = 'main.html'

    def get(self, request, *args, **kwargs):
        welcome = RedisMessage('Hello everybody')  # create a welcome message to be sent to everybody
        RedisPublisher(facility='foobar', broadcast=True).publish_message(welcome)
        return super(TerminalView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        redis_publisher = RedisPublisher(facility='foobar', groups=[request.POST.get('group')])
        message = RedisMessage(request.POST.get('message'))
        redis_publisher.publish_message(message)
        return HttpResponse('OK')
