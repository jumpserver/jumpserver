from django.shortcuts import redirect, reverse
from django.http import HttpResponseForbidden

from django.views.generic import DetailView, View

from .models import Organization
from common.utils import UUID_PATTERN


class SwitchOrgView(DetailView):
    model = Organization
    object = None

    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.object = Organization.get_instance(pk)
        oid = str(self.object.id)
        request.session['oid'] = oid
        host = request.get_host()
        referer = request.META.get('HTTP_REFERER', '')
        if referer.find(host) == -1:
            return redirect(reverse('index'))
        if UUID_PATTERN.search(referer):
            return redirect(reverse('index'))
        # 组织管理员切换到组织审计员时(403)
        if not self.object.get_org_admins().filter(id=request.user.id):
            return redirect(reverse('index'))
        return redirect(referer)


class SwitchToAOrgView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_common_user:
            return HttpResponseForbidden()
        admin_orgs = request.user.admin_orgs
        audit_orgs = request.user.audit_orgs
        default_org = Organization.default()
        if admin_orgs:
            if default_org in admin_orgs:
                redirect_org = default_org
            else:
                redirect_org = admin_orgs[0]
            return redirect(reverse('orgs:org-switch', kwargs={'pk': redirect_org.id}))
        if audit_orgs:
            if default_org in audit_orgs:
                redirect_org = default_org
            else:
                redirect_org = audit_orgs[0]
            return redirect(reverse('orgs:org-switch', kwargs={'pk': redirect_org.id}))
