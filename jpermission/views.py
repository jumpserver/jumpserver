from django.shortcuts import render_to_response


def perm_user_list(request):
    return render_to_response('jperm/perm_user_list.html')
