from django.urls import path

from .. import api

app_name = 'vaults'

urlpatterns = [
    path('testing', api.VaultConnectTestingAPI.as_view(), name='secret-connect-testing')
]
