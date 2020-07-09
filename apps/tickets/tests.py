import datetime

from common.utils.timezone import now
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from orgs.models import Organization, OrganizationMember, ROLE as ORG_ROLE
from orgs.utils import set_current_org
from users.models.user import User
from assets.models import Asset, AdminUser, SystemUser


class TicketTest(APITestCase):
    def setUp(self):
        Organization.objects.bulk_create([
                Organization(name='org-01'),
                Organization(name='org-02'),
                Organization(name='org-03'),
        ])
        org_01, org_02, org_03 = Organization.objects.all()
        self.org_01, self.org_02, self.org_03 = org_01, org_02, org_03

        set_current_org(org_01)

        AdminUser.objects.bulk_create([
            AdminUser(name='au-01', username='au-01'),
            AdminUser(name='au-02', username='au-02'),
            AdminUser(name='au-03', username='au-03'),
        ])

        SystemUser.objects.bulk_create([
            SystemUser(name='su-01', username='su-01'),
            SystemUser(name='su-02', username='su-02'),
            SystemUser(name='su-03', username='su-03'),
        ])

        admin_users = AdminUser.objects.all()
        Asset.objects.bulk_create([
            Asset(hostname='asset-01', ip='192.168.1.1', public_ip='192.168.1.1', admin_user=admin_users[0]),
            Asset(hostname='asset-02', ip='192.168.1.2', public_ip='192.168.1.2', admin_user=admin_users[0]),
            Asset(hostname='asset-03', ip='192.168.1.3', public_ip='192.168.1.3', admin_user=admin_users[0]),
        ])

        new_user = User.objects.create
        new_org_memeber = OrganizationMember.objects.create

        u = new_user(name='user-01', username='user-01', email='user-01@jms.com')
        new_org_memeber(org=org_01, user=u, role=ORG_ROLE.USER)
        new_org_memeber(org=org_02, user=u, role=ORG_ROLE.USER)
        self.user_01 = u

        u = new_user(name='org-admin-01', username='org-admin-01', email='org-admin-01@jms.com')
        new_org_memeber(org=org_01, user=u, role=ORG_ROLE.ADMIN)
        self.org_admin_01 = u

        u = new_user(name='org-admin-02', username='org-admin-02', email='org-admin-02@jms.com')
        new_org_memeber(org=org_02, user=u, role=ORG_ROLE.ADMIN)
        self.org_admin_02 = u

    def test_create_request_asset_perm(self):
        url = reverse('api-tickets:ticket-request-asset-perm')
        ticket_url = reverse('api-tickets:ticket')

        self.client.force_login(self.user_01)

        date_start = now()
        date_expired = date_start + datetime.timedelta(days=7)

        data = {
            "title": "request-01",
            "ips": [
                "192.168.1.1"
            ],
            "date_start": date_start,
            "date_expired": date_expired,
            "hostname": "",
            "system_user": "",
            "org_id": self.org_01.id,
            "assignees": [
                str(self.org_admin_01.id),
                str(self.org_admin_02.id),
            ]
        }

        self.client.post(data)

        self.client.force_login(self.org_admin_01)
        res = self.client.get(ticket_url, params={'assgin': 1})
