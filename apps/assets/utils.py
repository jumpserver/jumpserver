# ~*~ coding: utf-8 ~*~
#
from rest_framework import serializers
from models import Tag
from django.views.generic.edit import CreateView

class CreateAssetTagsMiXin(CreateView):
    def get_form_kwargs(self):
        tags_list = self.request.POST.getlist('tags')
        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
        }
        if self.request.method in ('POST', 'PUT'):
            post_data = self.request.POST.copy()
            if post_data.has_key('tags'):
                post_data.pop('tags')
                for t in tags_list:
                    try:
                        oTag = Tag.objects.get(pk=int(t))
                    except (Tag.DoesNotExist, UnicodeEncodeError):
                        oTag = Tag(name=t, created_by=self.request.user.username or 'Admin')
                        oTag.save()
                        post_data.update({'tags':oTag.pk})
                    else:
                        post_data.update({'tags':int(t)})
            kwargs.update({
                'data': post_data,
                'files': self.request.FILES,
            })
        return kwargs

class UpdateAssetTagsMiXin(CreateAssetTagsMiXin):
    def get_form_kwargs(self):
        kwargs = super(UpdateAssetTagsMiXin, self).get_form_kwargs()
        if hasattr(self, 'object'):
            kwargs.update({'instance': self.object})
        return kwargs