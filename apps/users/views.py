from django.shortcuts import render
from django.views.generic.base import TemplateView


def hello(request):
    return render(request, 'base.html')
