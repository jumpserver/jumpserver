from django.shortcuts import redirect

from django.views.generic import DetailView

from .models import Organization


class SwitchOrgView(DetailView):
    model = Organization
    object = None

    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.object = Organization.get_instance(pk)
        request.session['oid'] = self.object.id.__str__()
        return redirect('index')
