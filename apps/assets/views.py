from django.views.generic import TemplateView, ListView
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.views.generic.detail import DetailView
from .models import Asset, AssetGroup, IDC, AssetExtend
from .forms import AssetForm

from .utils import AdminUserRequiredMixin


class AssetAddView(AdminUserRequiredMixin, CreateView):
    model = Asset
    form_class = AssetForm
    template_name = 'assets/asset_add.html'
    success_url = reverse_lazy('assets:asset-list')

    def form_invalid(self, form):
        print(form.errors)
        return super(AssetAddView, self).form_invalid(form)


class AssetEditView():
    pass


class AssetDeleteView(DeleteView):
    model = Asset
    success_url = reverse_lazy('assets:asset-list')


class AssetListView(ListView):
    model = Asset
    context_object_name = 'assets'
    template_name = 'assets/asset_list.html'


class AssetDetailView(DetailView):
    model = Asset
    context_object_name = 'asset'
    template_name = 'assets/asset_detail.html'

