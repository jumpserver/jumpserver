# -*- coding: utf-8 -*-
#
from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Label, Asset

__all__ = ['LabelForm']


class LabelForm(forms.ModelForm):
    assets = forms.ModelMultipleChoiceField(
        queryset=Asset.objects.all(), label=_('Asset'), required=False,
        widget=forms.SelectMultiple(
            attrs={'class': 'select2', 'data-placeholder': _('Select assets')}
        )
    )

    class Meta:
        model = Label
        fields = ['name', 'value', 'assets']

    def __init__(self, *args, **kwargs):
        if kwargs.get('instance', None):
            initial = kwargs.get('initial', {})
            initial['assets'] = kwargs['instance'].assets.all()
        super().__init__(*args, **kwargs)

        # 前端渲染优化, 防止过多资产
        assets_field = self.fields.get('assets')
        if not self.data:
            instance = kwargs.get('instance')
            if instance:
                assets_field.queryset = instance.assets.all()
            else:
                assets_field.queryset = Asset.objects.none()

    def save(self, commit=True):
        label = super().save(commit=commit)
        assets = self.cleaned_data['assets']
        label.assets.set(assets)
        return label
