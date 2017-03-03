#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

from users.models import User, UserGroup, init_all_models
from django.shortcuts import reverse
from django.test import TestCase, Client, TransactionTestCase

from .base import gen_username, gen_name, gen_email, get_role


class UserListViewTests(TransactionTestCase):
    def setUp(self):
        init_all_models()
        self.client.login(username='admin', password='admin')

    def test_a_new_user_in_list(self):
        username = gen_username()
        user = User(username=username, email=gen_email(), role=get_role())
        user.save()
        response = self.client.get(reverse('users:user-list'))

        self.assertContains(response, username)

    def test_list_view_with_admin_user(self):
        response = self.client.get(reverse('users:user-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin')
        self.assertEqual(response.context['user_list'].count(), User.objects.all().count())

    def test_pagination(self):
        User.generate_fake(count=20)
        response = self.client.get(reverse('users:user-list'))
        self.assertEqual(response.context['is_paginated'], True)

    def tearDown(self):
        self.client.logout()


class UserAddTests(TestCase):
    def setUp(self):
        init_all_models()
        self.client.login(username='admin', password='admin')

    def test_add_a_new_user(self):
        username = gen_username()
        data = {
            'username': username,
            'comment': '',
            'name': gen_name(),
            'email': gen_email(),
            'groups': [UserGroup.objects.first().id, ],
            'role': get_role(),
            'date_expired': '2086-08-06 19:12:22',
        }

        response = self.client.post(reverse('users:user-create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['location'], reverse('users:user-list'))

        response = self.client.get(reverse('users:user-list'))
        self.assertContains(response, username)

    def tearDown(self):
        self.client.logout()

