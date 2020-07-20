from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from users.models.user import User


class OrgTests(APITestCase):
    def test_create(self):
        print(User.objects.all())
        reverse('api-orgs:org-list')



{"name":"a-07","admins":["138167d2-6843-4e25-b838-59657157c6c6"],"auditors":["8d4b3ec4-8339-4a2c-b33c-c2633da62c84"],"users":["ea60e8ce-876d-493b-a641-ff836258629c"]}

