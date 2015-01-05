from django.shortcuts import render
from django.shortcuts import render_to_response


def user_add(request):
    return render_to_response('user_add.html')


