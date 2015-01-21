from django.shortcuts import render_to_response
from juser.models import User


def perm_user_list(request):
    header_title, path1, path2 = u'查看授权用户 | Perm User Detail.', u'授权管理', u'用户详情'
    users = User.objects.all()
    return render_to_response('jperm/perm_user_list.html', locals(),)
