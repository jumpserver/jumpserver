import ssl
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from authentication.mapping import (
    MISSING, AuthMappingError, AuthMappingService,
    match_group_mapping, match_role_mapping, normalize_auth_attributes,
)
from authentication.backends.ldap import LDAPAuthorizationBackend, LDAPUser
from jumpserver.rewriting.smtp import EmailBackend
from orgs.models import Organization
from rbac.const import Scope
from settings.const import ImportStatus
from settings.api.ldap import LDAPMappingOptionApi, LDAPUserListApi
from settings.serializers.auth.ldap import (
    LDAPSettingSerializer, LDAPTestConfigSerializer,
    LDAPUserGroupMapSerializer, LDAPUserRoleMapSerializer,
    LDAPUserSerializer,
)
from settings.serializers.msg import EmailSettingSerializer
from settings.utils.ldap import LDAPImportUtil, LDAPServerUtil, LDAPTestUtil
from settings.ws import LdapWebsocket


class LDAPEntry:
    def __init__(self, entry_dn, **attributes):
        self.entry_dn = entry_dn
        self.attributes = {
            name: SimpleNamespace(
                values=value if isinstance(value, list) else [value]
            )
            for name, value in attributes.items()
        }

    def __getitem__(self, item):
        return self.attributes[item]


class LDAPConnection:
    def __init__(self, entries):
        self.group_entries = entries
        self.entries = []
        self.result = {
            'controls': {
                '1.2.840.113556.1.4.319': {'value': {'cookie': None}}
            }
        }
        self.search_calls = []

    def search(self, **kwargs):
        self.search_calls.append(kwargs)
        self.entries = self.group_entries
        return True


class AuthMappingMatcherTestCase(SimpleTestCase):
    def test_group_exact_matches_are_case_insensitive_and_union_targets(self):
        rules = [
            {'value': 'Developers', 'user_group_id': 'group-1'},
            {'value': 'developers', 'user_group_id': 'group-2'},
            {'value': '*', 'user_group_id': 'fallback'},
        ]

        targets = match_group_mapping(rules, [b' DEVELOPERS ', 'other'])

        self.assertEqual(targets, ['group-1', 'group-2'])

    def test_group_wildcard_falls_back_only_without_exact_match(self):
        rules = [
            {'value': 'developers', 'user_group_id': 'group-1'},
            {'value': '*', 'user_group_id': 'fallback'},
        ]

        self.assertEqual(match_group_mapping(rules, []), ['fallback'])
        self.assertIsNone(match_group_mapping(rules, MISSING))
        self.assertEqual(
            match_group_mapping([rules[-1]], MISSING), ['fallback']
        )
        self.assertEqual(match_group_mapping([], MISSING), [])

    def test_group_wildcard_can_be_anywhere_and_is_optional(self):
        wildcard_first = [
            {'value': '*', 'user_group_id': 'fallback'},
            {'value': 'developers', 'user_group_id': 'group-1'},
        ]
        exact_only = [wildcard_first[-1]]

        self.assertEqual(match_group_mapping(wildcard_first, []), ['fallback'])
        self.assertEqual(match_group_mapping(exact_only, ['other']), [])

    def test_role_mapping_matches_multivalue_groups_and_dn(self):
        rules = [
            {
                'attribute': 'Groups', 'value': 'ops', 'scope': Scope.system,
                'role_id': 'role-1', 'org_id': None,
            },
            {
                'attribute': 'dn', 'value': 'cn=alice,dc=example,dc=test',
                'scope': Scope.org, 'role_id': 'role-2', 'org_id': 'org-1',
            },
            {
                'attribute': '', 'value': '*', 'scope': Scope.system,
                'role_id': 'fallback', 'org_id': None,
            },
        ]
        attributes = normalize_auth_attributes(
            {'memberOf': [b'users']},
            dn=b'CN=Alice,DC=example,DC=test',
            groups=[b'OPS', 'audit'],
        )

        targets = match_role_mapping(rules, attributes)

        self.assertEqual(targets, [
            {'scope': Scope.system, 'role_id': 'role-1', 'org_id': None},
            {'scope': Scope.org, 'role_id': 'role-2', 'org_id': 'org-1'},
        ])

    def test_role_wildcard_and_empty_rules_do_not_require_attributes(self):
        wildcard = [{
            'attribute': '', 'value': '*', 'scope': Scope.system,
            'role_id': 'fallback', 'org_id': None,
        }]

        self.assertEqual(match_role_mapping(wildcard, MISSING), [{
            'scope': Scope.system, 'role_id': 'fallback', 'org_id': None,
        }])
        self.assertEqual(match_role_mapping([], MISSING), [])

    def test_role_wildcard_can_be_anywhere_and_is_optional(self):
        exact = {
            'attribute': 'department', 'value': 'ops',
            'scope': Scope.system, 'role_id': 'role-1', 'org_id': None,
        }
        wildcard = {
            'attribute': '', 'value': '*',
            'scope': Scope.system, 'role_id': 'role-default', 'org_id': None,
        }

        self.assertEqual(
            match_role_mapping([wildcard, exact], {'department': ['ops']}),
            [{'scope': Scope.system, 'role_id': 'role-1', 'org_id': None}],
        )
        self.assertEqual(
            match_role_mapping([wildcard, exact], {'department': ['other']}),
            [{'scope': Scope.system, 'role_id': 'role-default', 'org_id': None}],
        )
        self.assertEqual(
            match_role_mapping([exact], {'department': ['other']}), []
        )

    def test_invalid_utf8_fails_closed(self):
        with self.assertRaises(UnicodeDecodeError):
            normalize_auth_attributes({'groups': [b'\xff']})

    @patch('authentication.mapping.tmp_to_root_org', return_value=nullcontext())
    @patch('authentication.mapping.Organization.objects.filter')
    @patch('authentication.mapping.Role.objects.filter')
    @patch('authentication.mapping.UserGroup.objects.filter')
    def test_batch_preview_uses_shared_resolution_once(
            self, group_filter, role_filter, org_filter, _root_org
    ):
        dangling_group_id = '11111111-1111-1111-1111-111111111111'
        fallback_group_id = '22222222-2222-2222-2222-222222222222'
        exact_role_id = '33333333-3333-3333-3333-333333333333'
        fallback_role_id = '44444444-4444-4444-4444-444444444444'
        group = SimpleNamespace(
            id=fallback_group_id, name='Default group',
            org_id=Organization.DEFAULT_ID,
        )
        exact_role = SimpleNamespace(
            id=exact_role_id, scope=Scope.system, display_name='Exact role',
        )
        fallback_role = SimpleNamespace(
            id=fallback_role_id, scope=Scope.system,
            display_name='Fallback role',
        )
        org_user = SimpleNamespace(
            id='00000000-0000-0000-0000-000000000007',
            scope=Scope.org, display_name='OrgUser',
        )
        org = SimpleNamespace(id=Organization.DEFAULT_ID, name='Default')
        group_filter.return_value = [group]
        role_filter.return_value = [exact_role, fallback_role, org_user]
        org_filter.return_value = [org]
        service = AuthMappingService(
            'ldap',
            group_rules=[
                {'value': 'ops', 'user_group_id': dangling_group_id},
                {'value': 'invalid', 'user_group_id': 'not-a-uuid'},
                {'value': '*', 'user_group_id': fallback_group_id},
            ],
            role_rules=[
                {
                    'attribute': 'department', 'value': 'ops',
                    'scope': Scope.system, 'role_id': exact_role_id,
                    'org_id': None,
                },
                {
                    'attribute': 'department', 'value': 'ops',
                    'scope': Scope.org,
                    'role_id': '00000000-0000-0000-0000-000000000007',
                    'org_id': Organization.DEFAULT_ID,
                },
                {
                    'attribute': '', 'value': '*',
                    'scope': Scope.system, 'role_id': fallback_role_id,
                    'org_id': None,
                },
            ],
        )

        previews = service.preview_many([
            ({'department': ['other']}, ['ops']),
            ({'department': ['ops']}, ['other']),
            ({'department': ['ops']}, MISSING),
            ({'department': ['other']}, [b'\xff']),
            ({'department': ['other']}, ['invalid']),
        ])

        self.assertEqual(previews[0]['groups'], [])
        self.assertEqual(previews[0]['roles'], [(fallback_role, None)])
        self.assertEqual(previews[1]['groups'], [group])
        self.assertEqual(
            previews[1]['roles'], [(exact_role, None), (org_user, org)]
        )
        self.assertIn('group attributes are unavailable', previews[2]['error'])
        self.assertEqual(previews[2]['groups'], [])
        self.assertEqual(previews[2]['roles'], [])
        self.assertTrue(previews[3]['error'])
        self.assertIn('Invalid authentication mapping target ID', previews[4]['error'])
        self.assertEqual(group_filter.call_count, 1)
        self.assertEqual(role_filter.call_count, 1)
        self.assertEqual(org_filter.call_count, 1)

    @patch('authentication.mapping.tmp_to_root_org', return_value=nullcontext())
    @patch(
        'authentication.mapping.UserGroup.objects.filter',
        side_effect=RuntimeError('mapping target query failed'),
    )
    def test_batch_preview_query_error_is_reported_per_record(
            self, _group_filter, _root_org
    ):
        service = AuthMappingService('ldap', group_rules=[{
            'value': '*',
            'user_group_id': '11111111-1111-1111-1111-111111111111',
        }])

        previews = service.preview_many([
            ({}, []),
            ({}, [b'\xff']),
        ])

        self.assertEqual(previews[0]['groups'], [])
        self.assertEqual(previews[0]['roles'], [])
        self.assertEqual(previews[0]['error'], 'mapping target query failed')
        self.assertEqual(previews[1]['groups'], [])
        self.assertEqual(previews[1]['roles'], [])
        self.assertTrue(previews[1]['error'])
        self.assertNotEqual(previews[1]['error'], 'mapping target query failed')


class AuthMappingOwnershipTestCase(SimpleTestCase):
    def test_unowned_group_removal_only_deletes_provenance(self):
        service = AuthMappingService('ldap')
        user = MagicMock()
        binding = MagicMock(owned=False)

        service._remove_group_binding(user, binding)

        binding.delete.assert_called_once_with()
        user.groups.remove.assert_not_called()

    @patch('authentication.mapping.AuthRoleBinding.objects')
    def test_unique_system_user_binding_is_kept_without_provenance(self, objects):
        objects.select_for_update.return_value.filter.return_value.exclude \
            .return_value.order_by.return_value.first.return_value = None
        service = AuthMappingService('ldap')
        user = MagicMock()
        role_binding = MagicMock(
            scope=Scope.system,
            role_id='00000000-0000-0000-0000-000000000003',
            pk='binding-1',
        )
        binding = MagicMock(owned=True, role_binding=role_binding, pk='source-1')
        system_bindings = MagicMock()

        with patch(
            'authentication.mapping.RoleBinding.objects_raw.filter',
            return_value=system_bindings,
        ):
            system_bindings.exclude.return_value.exists.return_value = False
            service._remove_role_binding(user, binding)

        binding.delete.assert_called_once_with()
        role_binding.delete.assert_not_called()

    @patch('authentication.mapping.BuiltinRole.org_user.get_role')
    @patch('authentication.mapping.Organization.objects.filter')
    def test_group_org_roles_are_deduplicated(
            self, org_filter, get_org_user_role
    ):
        org = SimpleNamespace(id=Organization.DEFAULT_ID)
        org_filter.return_value = [org]
        role = SimpleNamespace(id='org-user')
        get_org_user_role.return_value = role
        groups = [
            SimpleNamespace(id='group-1', org_id=Organization.DEFAULT_ID),
            SimpleNamespace(id='group-2', org_id=Organization.DEFAULT_ID),
        ]

        valid_groups, roles = AuthMappingService._resolve_group_org_roles(groups)

        self.assertEqual(valid_groups, groups)
        self.assertEqual(roles, [(role, org)])


class LDAPAttributeMapSerializerTestCase(SimpleTestCase):
    def get_serializer(self, **data):
        return LDAPTestConfigSerializer(data={
            'AUTH_LDAP_SERVER_URI': 'ldap://ldap.example.test',
            'AUTH_LDAP_SEARCH_OU': 'ou=users,dc=example,dc=test',
            'AUTH_LDAP_SEARCH_FILTER': '(uid=%(user)s)',
            'AUTH_LDAP_USER_ATTR_MAP': {
                'username': 'uid',
                'name': 'displayName',
                'email': 'mail',
            },
            **data,
        })

    def test_accepts_supported_and_legacy_attributes(self):
        serializer = self.get_serializer(AUTH_LDAP_USER_ATTR_MAP={
            'username': 'uid',
            'name': 'displayName',
            'email': '1.2.840.113556.1.4.656',
            'phone': 'telephoneNumber',
            'comment': 'description',
            'is_active': 'userAccountControl',
            'groups': 'memberOf',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejects_missing_unknown_and_invalid_attributes(self):
        cases = [
            {'username': 'uid', 'name': 'displayName'},
            {
                'username': 'uid', 'name': 'displayName', 'email': 'mail',
                'nickname': 'cn',
            },
            {
                'username': 'uid', 'name': 'displayName', 'email': 'mail',
                'wechat': 'wechat-id',
            },
            {
                'username': 'uid)(objectClass=*)',
                'name': 'displayName', 'email': 'mail',
            },
        ]
        for attr_map in cases:
            with self.subTest(attr_map=attr_map):
                serializer = self.get_serializer(AUTH_LDAP_USER_ATTR_MAP=attr_map)
                self.assertFalse(serializer.is_valid())
                self.assertIn('AUTH_LDAP_USER_ATTR_MAP', serializer.errors)

    def test_group_search_filter_requires_one_percent_s(self):
        for search_filter in [
            '(member=uid)',
            '(|(member=%s)(owner=%s))',
            '(member=%(user)s)',
            '(member=%d)',
        ]:
            with self.subTest(search_filter=search_filter):
                serializer = self.get_serializer(
                    AUTH_LDAP_GROUP_SEARCH_FILTER=search_filter
                )
                self.assertFalse(serializer.is_valid())
                self.assertIn('AUTH_LDAP_GROUP_SEARCH_FILTER', serializer.errors)

        serializer = self.get_serializer(
            AUTH_LDAP_GROUP_SEARCH_FILTER='(&(objectClass=group)(member=%s))'
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    @patch('settings.serializers.auth.ldap.tmp_to_root_org', return_value=nullcontext())
    @patch('settings.serializers.auth.ldap.UserGroup.objects.filter')
    def test_group_mapping_preserves_order_and_rejects_duplicate_rows(
            self, group_filter, _tmp_to_root_org
    ):
        group_filter.return_value.only.return_value.first.return_value = (
            SimpleNamespace(org_id=Organization.DEFAULT_ID)
        )
        first_id = '11111111-1111-1111-1111-111111111111'
        second_id = '22222222-2222-2222-2222-222222222222'
        serializer = LDAPUserGroupMapSerializer(data=[
            {'value': 'Developers', 'user_group_id': first_id},
            {'value': 'developers', 'user_group_id': second_id},
            {'value': '*', 'user_group_id': first_id},
        ], many=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            [row['user_group_id'] for row in serializer.validated_data],
            [first_id, second_id, first_id],
        )

        duplicate = LDAPUserGroupMapSerializer(data=[
            {'value': 'Developers', 'user_group_id': first_id},
            {'value': 'developers', 'user_group_id': first_id},
        ], many=True)
        self.assertFalse(duplicate.is_valid())

    @patch('settings.serializers.auth.ldap.tmp_to_root_org', return_value=nullcontext())
    @patch('settings.serializers.auth.ldap.UserGroup.objects.filter')
    def test_group_wildcard_can_be_anywhere_but_must_be_unique(
            self, group_filter, _tmp_to_root_org
    ):
        group_filter.return_value.only.return_value.first.return_value = (
            SimpleNamespace(org_id=Organization.DEFAULT_ID)
        )
        group_id = '11111111-1111-1111-1111-111111111111'
        serializer = LDAPUserGroupMapSerializer(data=[
            {'value': '*', 'user_group_id': group_id},
            {'value': 'developers', 'user_group_id': group_id},
        ], many=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)

        duplicate = LDAPUserGroupMapSerializer(data=[
            {'value': '*', 'user_group_id': group_id},
            {
                'value': '*',
                'user_group_id': '22222222-2222-2222-2222-222222222222',
            },
        ], many=True)
        self.assertFalse(duplicate.is_valid())

    @patch('settings.serializers.auth.ldap.Role.objects.filter')
    def test_role_mapping_stores_string_ids_and_validates_scope(self, role_filter):
        role_filter.return_value.only.return_value.first.return_value = (
            SimpleNamespace(scope=Scope.system)
        )
        role_id = '11111111-1111-1111-1111-111111111111'
        serializer = LDAPUserRoleMapSerializer(data=[{
            'attribute': 'memberOf',
            'value': 'Developers',
            'scope': Scope.system,
            'role_id': role_id,
            'org_id': None,
        }], many=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsInstance(serializer.validated_data[0]['role_id'], str)

        role_filter.return_value.only.return_value.first.return_value = (
            SimpleNamespace(scope=Scope.org)
        )
        invalid = LDAPUserRoleMapSerializer(data=[{
            'attribute': 'memberOf',
            'value': 'Developers',
            'scope': Scope.system,
            'role_id': role_id,
            'org_id': None,
        }], many=True)
        self.assertFalse(invalid.is_valid())

    @patch('settings.serializers.auth.ldap.Role.objects.filter')
    def test_role_wildcard_can_be_anywhere_but_must_be_unique(self, role_filter):
        role_filter.return_value.only.return_value.first.return_value = (
            SimpleNamespace(scope=Scope.system)
        )
        wildcard_role_id = '11111111-1111-1111-1111-111111111111'
        exact_role_id = '22222222-2222-2222-2222-222222222222'
        serializer = LDAPUserRoleMapSerializer(data=[
            {
                'attribute': '', 'value': '*', 'scope': Scope.system,
                'role_id': wildcard_role_id, 'org_id': None,
            },
            {
                'attribute': 'department', 'value': 'ops',
                'scope': Scope.system, 'role_id': exact_role_id,
                'org_id': None,
            },
        ], many=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)

        duplicate = LDAPUserRoleMapSerializer(data=[
            {
                'attribute': '', 'value': '*', 'scope': Scope.system,
                'role_id': wildcard_role_id, 'org_id': None,
            },
            {
                'attribute': '', 'value': '*', 'scope': Scope.system,
                'role_id': exact_role_id, 'org_id': None,
            },
        ], many=True)
        self.assertFalse(duplicate.is_valid())

    @patch('settings.serializers.auth.ldap.tmp_to_root_org', return_value=nullcontext())
    @patch('settings.serializers.auth.ldap.UserGroup.objects.filter')
    def test_exact_group_mapping_requires_a_group_source(
            self, group_filter, _tmp_to_root_org
    ):
        group_filter.return_value.only.return_value.first.return_value = (
            SimpleNamespace(org_id=Organization.DEFAULT_ID)
        )
        group_id = '11111111-1111-1111-1111-111111111111'
        exact = LDAPSettingSerializer(data={
            **self.get_serializer().initial_data,
            'AUTH_LDAP_USER_GROUP_MAP': [{
            'value': 'developers', 'user_group_id': group_id,
            }],
        })
        fallback = LDAPSettingSerializer(data={
            **self.get_serializer().initial_data,
            'AUTH_LDAP_USER_GROUP_MAP': [{
            'value': '*', 'user_group_id': group_id,
            }],
        })

        self.assertFalse(exact.is_valid())
        self.assertIn('AUTH_LDAP_USER_GROUP_MAP', exact.errors)
        self.assertTrue(fallback.is_valid(), fallback.errors)

    def test_connection_test_does_not_resolve_mapping_targets(self):
        serializer = self.get_serializer(
            AUTH_LDAP_GROUP_ATTRIBUTE='memberOf',
            AUTH_LDAP_USER_GROUP_MAP=[{
                'value': 'developers',
                'user_group_id': 'not-yet-selected',
            }],
            AUTH_LDAP_USER_ROLE_MAP=[{
                'attribute': 'departmentNumber',
                'value': '42',
                'scope': '',
                'role_id': '',
                'org_id': None,
            }],
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data['AUTH_LDAP_USER_ROLE_MAP'][0]['attribute'],
            'departmentNumber',
        )

    @patch('settings.utils.LDAPSyncUtil')
    def test_saving_primary_ldap_settings_clears_sync_cache(self, sync_util):
        serializer = LDAPSettingSerializer()
        serializer._validated_data = {}

        serializer.post_save()

        sync_util.assert_called_once_with(category='ldap')
        sync_util.return_value.clear_cache.assert_called_once_with()


class LDAPServerUtilTestCase(SimpleTestCase):
    config = {
        'server_uri': 'ldap://ldap.example.test',
        'search_ou': 'ou=users,dc=example,dc=test',
        'search_filter': '(uid=%(user)s)',
        'attr_map': {
            'username': 'uid',
            'name': 'displayName',
            'email': 'mail',
            'comment': 'description',
            'groups': 'memberOf',
        },
    }

    def get_util(self, **config):
        return LDAPServerUtil(config={**self.config, **config})

    def get_user_entry(self, **attributes):
        values = {
            'uid': [' alice ', 'ignored'],
            'displayName': 'Alice',
            'mail': 'alice@example.test',
            'description': ['first', 'second'],
            **attributes,
        }
        return LDAPEntry(
            'CN=Alice,OU=Users,DC=example,DC=test',
            **values,
        )

    def test_ordinary_attributes_use_first_value_and_new_group_field_wins(self):
        util = self.get_util(group_attribute='preferredGroup')
        entry = self.get_user_entry(
            memberOf='CN=Legacy,OU=Groups,DC=example,DC=test',
            preferredGroup=[
                ' CN=One,OU=Groups,DC=example,DC=test ',
                'cn=one,ou=groups,dc=example,dc=test',
                'CN=Two,OU=Groups,DC=example,DC=test',
            ],
        )

        user = util.user_entry_to_dict(entry)

        self.assertEqual(user['username'], 'alice')
        self.assertEqual(user['comment'], 'first')
        self.assertEqual(user['groups'], [
            'CN=One,OU=Groups,DC=example,DC=test',
            'CN=Two,OU=Groups,DC=example,DC=test',
        ])
        self.assertEqual(user['status'], ImportStatus.pending)

    def test_legacy_missing_and_explicit_empty_group_states(self):
        legacy = self.get_util().user_entry_to_dict(self.get_user_entry(
            memberOf='CN=Legacy,OU=Groups,DC=example,DC=test'
        ))
        self.assertEqual(
            legacy['groups'], ['CN=Legacy,OU=Groups,DC=example,DC=test']
        )

        no_group_map = {
            key: value for key, value in self.config['attr_map'].items()
            if key != 'groups'
        }
        missing = self.get_util(attr_map=no_group_map).user_entry_to_dict(
            self.get_user_entry()
        )
        self.assertNotIn('groups', missing)

        empty = self.get_util(
            attr_map=no_group_map, group_attribute='memberOf'
        ).user_entry_to_dict(self.get_user_entry())
        self.assertEqual(empty['groups'], [])

    def test_group_search_overrides_direct_attribute_and_escapes_user_dn(self):
        util = self.get_util(
            group_attribute='memberOf',
            group_search_filter='(&(objectClass=group)(member=%s))',
            group_search_user_attribute='dn',
        )
        group_dn = r'CN=Ops\, Team,OU=Groups,DC=example,DC=test'
        util._conn = LDAPConnection([
            SimpleNamespace(entry_dn=group_dn),
            SimpleNamespace(entry_dn=group_dn.lower()),
        ])
        entry = self.get_user_entry(
            memberOf='CN=Ignored,OU=Groups,DC=example,DC=test'
        )
        entry.entry_dn = 'CN=Alice *(Admin),OU=Users,DC=example,DC=test'

        user = util.user_entry_to_dict(entry)

        self.assertEqual(user['groups'], [group_dn])
        search = util.connection.search_calls[0]
        self.assertEqual(search['search_base'], self.config['search_ou'])
        self.assertEqual(
            search['search_filter'],
            '(&(objectClass=group)'
            '(member=CN=Alice \\2a\\28Admin\\29,OU=Users,DC=example,DC=test))'
        )

    def test_group_search_defaults_to_mapped_username(self):
        util = self.get_util(
            group_search_ou='ou=groups,dc=example,dc=test',
            group_search_filter='(memberUid=%s)',
        )
        util._conn = LDAPConnection([])
        entry = self.get_user_entry(uid='ali*ce')

        user = util.user_entry_to_dict(entry)

        self.assertEqual(user['groups'], [])
        search = util.connection.search_calls[0]
        self.assertEqual(search['search_base'], 'ou=groups,dc=example,dc=test')
        self.assertEqual(search['search_filter'], r'(memberUid=ali\2ace)')

    def test_group_search_missing_substitution_fails_closed(self):
        util = self.get_util(
            group_search_filter='(memberUid=%s)',
            group_search_user_attribute='employeeNumber',
        )

        with self.assertRaisesRegex(ValueError, 'attribute is unavailable'):
            util.user_entry_to_dict(self.get_user_entry())

    def test_group_search_false_result_fails_closed(self):
        util = self.get_util(group_search_filter='(memberUid=%s)')
        connection = LDAPConnection([])
        connection.search = MagicMock(return_value=False)
        connection.result = {
            'result': 1,
            'description': 'operationsError',
        }
        util._conn = connection

        with self.assertRaisesRegex(RuntimeError, 'operationsError'):
            util.user_entry_to_dict(self.get_user_entry())

    def test_user_search_false_result_is_a_global_error(self):
        util = self.get_util()
        connection = LDAPConnection([])
        connection.search = MagicMock(return_value=False)
        connection.result = {
            'result': 1,
            'description': 'operationsError',
        }
        util._conn = connection

        with self.assertRaisesRegex(RuntimeError, 'user search failed'):
            util.search_user_entries()

    def test_entry_mapping_error_does_not_abort_other_users(self):
        util = self.get_util(
            group_search_filter='(memberUid=%s)',
            group_search_user_attribute='employeeNumber',
        )
        util._conn = LDAPConnection([])
        invalid = self.get_user_entry(uid='invalid')
        valid = self.get_user_entry(uid='valid', employeeNumber='1001')

        users = util.user_entries_to_dict([invalid, valid])

        self.assertEqual(users[0]['username'], 'invalid')
        self.assertIn('_auth_mapping_error', users[0])
        self.assertEqual(users[1]['username'], 'valid')
        self.assertEqual(users[1]['groups'], [])

    def test_role_attributes_are_requested_and_kept_as_internal_multivalues(self):
        util = self.get_util(user_role_map=[{
            'attribute': 'departmentNumber',
            'value': '42',
            'scope': Scope.system,
            'role_id': 'role-1',
            'org_id': None,
        }])
        entry = self.get_user_entry(
            departmentNumber=[b' 42 ', b'84'],
            memberOf='CN=Ops,OU=Groups,DC=example,DC=test',
        )

        user = util.user_entry_to_dict(entry)

        self.assertIn('departmentNumber', util.get_user_search_attributes())
        self.assertEqual(
            user['_auth_attributes']['departmentnumber'], ['42', '84']
        )
        self.assertEqual(
            user['_auth_attributes']['groups'],
            ['CN=Ops,OU=Groups,DC=example,DC=test'],
        )
        self.assertEqual(
            user['_auth_attributes']['dn'],
            ['CN=Alice,OU=Users,DC=example,DC=test'],
        )

    @patch('settings.utils.ldap.LDAPServerUtil')
    def test_config_search_validates_only_the_first_entry(self, server_util):
        entries = [object(), object(), object()]
        util = server_util.return_value
        util.search_user_entries.return_value = entries
        util.user_entries_to_dict.return_value = [{}]
        test_util = object.__new__(LDAPTestUtil)
        test_util.config = object()

        test_util.test_search()

        self.assertEqual(test_util.user_entries, entries)
        util.user_entries_to_dict.assert_called_once_with(entries[:1])

    def test_high_level_search_closes_connection_after_conversion(self):
        util = self.get_util()
        connection = MagicMock()
        util._conn = connection
        entries = [object()]
        util.search_user_entries = MagicMock(return_value=entries)
        util.user_entries_to_dict = MagicMock(side_effect=lambda value: [
            {'connection_open': util._conn is connection, 'entries': value}
        ])

        users = util.search()

        self.assertTrue(users[0]['connection_open'])
        connection.unbind.assert_called_once_with()
        self.assertIsNone(util._conn)


class LDAPImportUtilTestCase(SimpleTestCase):
    def test_group_name_uses_decoded_first_rdn(self):
        names = LDAPImportUtil().get_user_group_names([
            r'CN=Doe\, Jane,OU=Groups,DC=example,DC=test',
            r'cn=doe\, jane,ou=groups,dc=example,dc=test',
            'developers',
        ])

        self.assertEqual(names, ['AD Doe, Jane', 'AD developers'])

    def test_group_name_rejects_values_over_model_limit(self):
        with self.assertRaises(ValueError):
            LDAPImportUtil().get_user_group_names(['x' * 129])

    @override_settings(AUTH_LDAP_STRICT_SYNC=False)
    def test_import_distinguishes_missing_and_empty_groups(self):
        util = LDAPImportUtil()
        missing_user = object()
        empty_user = object()
        util.update_or_create = MagicMock(side_effect=[
            (missing_user, False), (empty_user, False),
        ])
        util.get_mapping_service = MagicMock(return_value=None)
        util.bind_org = MagicMock()
        org = MagicMock()
        org.is_root.return_value = True
        users = [
            {'username': 'missing'},
            {'username': 'empty', 'groups': []},
        ]

        _, errors, _ = util.perform_import(users, [org])

        self.assertEqual(errors, [])
        args = util.bind_org.call_args.args
        self.assertEqual(args[0], org)
        self.assertEqual(dict(args[1]), {})
        self.assertEqual(args[2], {empty_user})

    @override_settings(
        AUTH_LDAP_STRICT_SYNC=False,
        AUTH_LDAP_USER_GROUP_MAP=[{
            'value': 'developers',
            'user_group_id': '11111111-1111-1111-1111-111111111111',
        }],
        AUTH_LDAP_USER_ROLE_MAP=[],
    )
    def test_explicit_mapping_receives_internal_data_and_skips_legacy_groups(self):
        util = LDAPImportUtil()
        user_obj = object()
        service = MagicMock()
        util.get_mapping_service = MagicMock(return_value=service)
        util.update_or_create = MagicMock(return_value=(user_obj, False))
        util.bind_org = MagicMock()
        attributes = {'department': ['ops']}

        org = MagicMock()
        org.is_root.return_value = True
        _, errors, _ = util.perform_import([{
            'username': 'alice',
            'groups': ['developers'],
            '_auth_attributes': attributes,
        }], [org])

        self.assertEqual(errors, [])
        service.sync.assert_called_once_with(
            user_obj,
            attributes=attributes,
            groups=['developers'],
            raise_errors=True,
        )
        bind_args = util.bind_org.call_args.args
        self.assertEqual(dict(bind_args[1]), {})
        self.assertEqual(bind_args[2], set())

    @override_settings(
        AUTH_LDAP_STRICT_SYNC=False,
        AUTH_LDAP_USER_GROUP_MAP=[],
        AUTH_LDAP_USER_ROLE_MAP=[],
    )
    def test_selected_org_membership_exists_before_mapping_sync(self):
        util = LDAPImportUtil()
        user_obj = object()
        org = MagicMock()
        org.is_root.return_value = False
        events = []
        org.add_member.side_effect = lambda user: events.append(('org', user))
        service = MagicMock()
        service.sync.side_effect = lambda *args, **kwargs: events.append(
            ('mapping', args[0])
        )
        util.get_mapping_service = MagicMock(return_value=service)
        util.update_or_create = MagicMock(return_value=(user_obj, False))
        util.bind_org = MagicMock()

        with patch(
            'settings.utils.ldap.RoleBinding.objects_raw.filter'
        ) as role_binding_filter:
            role_binding_filter.return_value.first.return_value = None
            util.perform_import([{'username': 'alice'}], [org])

        self.assertEqual(events, [('org', user_obj), ('mapping', user_obj)])

    @patch('settings.utils.ldap.AuthRoleBinding.objects.filter')
    @patch('settings.utils.ldap.RoleBinding.objects_raw.filter')
    def test_imported_org_membership_downgrades_mapping_ownership(
            self, role_binding_filter, provenance_filter
    ):
        util = LDAPImportUtil()
        user = object()
        org = MagicMock(id=Organization.DEFAULT_ID)
        org.is_root.return_value = False
        role_binding = object()
        role_binding_filter.return_value.first.return_value = role_binding

        util.bind_user_orgs(user, [org])

        org.add_member.assert_called_once_with(user)
        role_binding_filter.assert_called_once_with(
            user=user,
            role_id='00000000-0000-0000-0000-000000000007',
            org_id=Organization.DEFAULT_ID,
            scope=Scope.org,
        )
        provenance_filter.assert_called_once_with(
            source='ldap', role_binding=role_binding, owned=True,
        )
        provenance_filter.return_value.update.assert_called_once_with(
            owned=False
        )

    @patch('settings.utils.ldap.tmp_to_org', side_effect=lambda org: nullcontext())
    def test_explicit_empty_groups_are_passed_to_cleanup(self, _tmp_to_org):
        util = LDAPImportUtil()
        user = MagicMock()
        org = MagicMock()
        org.is_root.return_value = False
        util.exit_user_group = MagicMock()

        util.bind_org(org, {}, {user})

        user_groups_mapper = util.exit_user_group.call_args.args[0]
        self.assertEqual(set(user_groups_mapper), {user})
        self.assertEqual(user_groups_mapper[user], set())

    @override_settings(AUTH_LDAP_STRICT_SYNC=False)
    def test_entry_mapping_error_skips_user_update_and_continues(self):
        util = LDAPImportUtil()
        valid_user = object()
        util.get_mapping_service = MagicMock(return_value=None)
        util.update_or_create = MagicMock(return_value=(valid_user, False))
        org = MagicMock()
        org.is_root.return_value = True

        _, errors, _ = util.perform_import([
            {
                'username': 'invalid',
                '_auth_mapping_error': 'group search failed',
            },
            {'username': 'valid'},
        ], [org])

        self.assertEqual(errors, [{'invalid': 'group search failed'}])
        util.update_or_create.assert_called_once_with({'username': 'valid'})


class LDAPWebsocketValidationTestCase(SimpleTestCase):
    def setUp(self):
        self.consumer = object.__new__(LdapWebsocket)
        self.consumer.category = 'ldap'

    def test_invalid_test_payload_returns_without_using_validated_data(self):
        ok, config_error = self.consumer.run_testing_config({})
        login_ok, login_error = self.consumer.run_testing_login({})

        self.assertFalse(ok)
        self.assertIn('error:', config_error)
        self.assertFalse(login_ok)
        self.assertIn('error:', login_error)


class LDAPMappingOptionApiTestCase(SimpleTestCase):
    def test_endpoint_uses_auth_setting_permission(self):
        self.assertEqual(
            LDAPMappingOptionApi.rbac_perms,
            {'GET': 'settings.change_auth'},
        )

    @patch('settings.api.ldap.IDSpmFilterBackend')
    @patch('settings.api.ldap.tmp_to_root_org', return_value=nullcontext())
    def test_query_and_spm_are_applied_before_pagination(
            self, _root_org, spm_backend
    ):
        request = SimpleNamespace(query_params={
            'type': 'user_group',
            'q': 'ops',
            'spm': 'selection-cache-key',
        })
        api = LDAPMappingOptionApi()
        api.request = request
        queryset = MagicMock()
        filtered = MagicMock()
        page = [SimpleNamespace(
            id='group-1', name='Ops', org_id=Organization.DEFAULT_ID,
        )]
        api.get_options_queryset = MagicMock(return_value=queryset)
        spm_backend.return_value.filter_queryset.return_value = filtered
        api.paginate_queryset = MagicMock(return_value=page)
        api.serialize_options = MagicMock(return_value=[{
            'id': 'group-1', 'label': 'Default / Ops',
            'org_id': Organization.DEFAULT_ID,
        }])
        response = object()
        api.get_paginated_response = MagicMock(return_value=response)

        self.assertIs(api.get(request), response)

        api.get_options_queryset.assert_called_once_with('user_group', 'ops')
        spm_backend.return_value.filter_queryset.assert_called_once_with(
            request, queryset, api
        )
        api.paginate_queryset.assert_called_once_with(filtered)

    @patch('settings.api.ldap.Role.objects.filter')
    def test_system_role_options_exclude_component(self, role_filter):
        queryset = role_filter.return_value

        LDAPMappingOptionApi.get_options_queryset('system_role', '')

        role_filter.assert_called_once_with(scope=Scope.system)
        queryset.exclude.assert_called_once_with(
            id='00000000-0000-0000-0000-000000000004'
        )

    @patch('settings.api.ldap.UserGroup.objects.exclude')
    def test_group_options_exclude_system_org(self, group_exclude):
        LDAPMappingOptionApi.get_options_queryset('user_group', '')

        group_exclude.assert_called_once_with(org_id=Organization.SYSTEM_ID)

    @patch('settings.api.ldap.Organization.objects.filter')
    def test_group_labels_use_org_then_group(self, org_filter):
        org_filter.return_value = [SimpleNamespace(
            id=Organization.DEFAULT_ID, name='Default',
        )]
        group = SimpleNamespace(
            id='group-1', name='Ops', org_id=Organization.DEFAULT_ID,
        )

        results = LDAPMappingOptionApi.serialize_options('user_group', [group])

        self.assertEqual(results, [{
            'id': 'group-1',
            'label': 'Default / Ops',
            'org_id': Organization.DEFAULT_ID,
        }])


class LDAPUserMappingPreviewTestCase(SimpleTestCase):
    @staticmethod
    def get_user(username='alice', groups=None):
        if groups is None:
            groups = ['CN=Raw,OU=Groups,DC=example,DC=test']
        return {
            'id': username,
            'username': username,
            'name': username.title(),
            'email': f'{username}@example.test',
            'groups': groups,
            '_auth_attributes': {'department': ['ops'], 'groups': groups},
            'existing': False,
            'status': ImportStatus.pending,
        }

    @override_settings(
        AUTH_LDAP_USER_GROUP_MAP=[{
            'value': 'ops', 'user_group_id': 'group-1',
        }],
        AUTH_LDAP_USER_ROLE_MAP=[],
    )
    @patch('settings.api.ldap.AuthMappingService')
    def test_standard_ldap_keeps_raw_groups_and_adds_full_labels(self, service):
        org = SimpleNamespace(id=Organization.DEFAULT_ID, name='Default')
        group = SimpleNamespace(
            id='group-1', name='Operators', org_id=Organization.DEFAULT_ID,
        )
        system_role = SimpleNamespace(
            id='role-1', scope=Scope.system, display_name='SystemAuditor',
        )
        org_user = SimpleNamespace(
            id='role-2', scope=Scope.org, display_name='OrgUser',
        )
        service.return_value.preview_many.return_value = [{
            'groups': [group],
            'roles': [(system_role, None), (org_user, org)],
            'error': '',
        }]
        api = LDAPUserListApi()
        api.request = SimpleNamespace(query_params={'category': 'ldap'})
        user = self.get_user(groups=['CN=Ops,DC=example,DC=test'])

        previews = api.get_mapping_previews([user])
        data = LDAPUserSerializer(
            user, context={'ldap_mapping_previews': previews}
        ).data

        self.assertEqual(data['groups'], ['CN=Ops,DC=example,DC=test'])
        self.assertEqual(data['mapped_groups'], ['Default / Operators'])
        self.assertEqual(data['mapped_roles'], [
            'SystemAuditor', 'Default / OrgUser',
        ])
        service.return_value.preview_many.assert_called_once_with([(
            user['_auth_attributes'], user['groups'],
        )])

    @patch('settings.api.ldap.AuthMappingService')
    def test_ldap_ha_uses_legacy_groups_without_standard_rules(self, service):
        api = LDAPUserListApi()
        api.request = SimpleNamespace(query_params={'category': 'ldap_ha'})
        user = self.get_user(groups=[
            'CN=Ops,OU=Groups,DC=example,DC=test',
        ])

        previews = api.get_mapping_previews([user])
        data = LDAPUserSerializer(
            user, context={'ldap_mapping_previews': previews}
        ).data

        self.assertEqual(
            data['groups'], ['CN=Ops,OU=Groups,DC=example,DC=test']
        )
        self.assertEqual(data['mapped_groups'], ['AD Ops'])
        self.assertEqual(data['mapped_roles'], [])
        service.assert_not_called()

    def test_legacy_preview_error_is_per_user_and_overrides_status(self):
        api = LDAPUserListApi()
        api.request = SimpleNamespace(query_params={'category': 'ldap_ha'})
        invalid = self.get_user('invalid', groups=['x' * 129])
        valid = self.get_user('valid', groups=['developers'])

        previews = api.get_mapping_previews([invalid, valid])
        data = LDAPUserSerializer(
            [invalid, valid], many=True,
            context={'ldap_mapping_previews': previews},
        ).data

        self.assertEqual(data[0]['mapped_groups'], [])
        self.assertEqual(data[0]['mapped_roles'], [])
        self.assertIn('error', data[0]['status'])
        self.assertEqual(data[1]['mapped_groups'], ['AD developers'])
        self.assertEqual(data[1]['status'], ImportStatus.pending)

    def test_strict_preview_error_suppresses_all_mapped_results(self):
        user = self.get_user()
        previews = {
            id(user): {
                'mapped_groups': [],
                'mapped_roles': [],
                'error': 'Authentication group attributes are unavailable',
            }
        }

        data = LDAPUserSerializer(
            user, context={'ldap_mapping_previews': previews}
        ).data

        self.assertEqual(data['mapped_groups'], [])
        self.assertEqual(data['mapped_roles'], [])
        self.assertEqual(data['status'], {
            'error': 'Authentication group attributes are unavailable',
        })


class LDAPLoginMappingTestCase(SimpleTestCase):
    @override_settings(
        AUTH_LDAP_USER_GROUP_MAP=[{
            'value': 'developers',
            'user_group_id': '11111111-1111-1111-1111-111111111111',
        }],
        AUTH_LDAP_USER_ROLE_MAP=[{
            'attribute': 'department',
            'value': 'ops',
            'scope': Scope.system,
            'role_id': '22222222-2222-2222-2222-222222222222',
            'org_id': None,
        }],
    )
    @patch('authentication.mapping.AuthMappingService.sync')
    @patch('settings.utils.LDAPServerUtil.search')
    def test_login_uses_standard_ldap_mapping_data(self, search, sync):
        attributes = {'department': ['ops'], 'groups': ['developers']}
        search.return_value = [{
            'username': 'alice',
            'groups': ['developers'],
            '_auth_attributes': attributes,
        }]
        ldap_user = object.__new__(LDAPUser)
        ldap_user.category = 'ldap'
        ldap_user._username = 'alice'
        ldap_user._user = MagicMock()

        ldap_user._sync_auth_mappings()

        sync.assert_called_once_with(
            ldap_user._user,
            attributes=attributes,
            groups=['developers'],
            raise_errors=True,
        )

    @patch('authentication.backends.ldap.LDAPUser')
    def test_mapping_error_fails_login_closed(self, ldap_user_class):
        backend = LDAPAuthorizationBackend()
        backend.pre_check = MagicMock(return_value=(True, ''))
        backend.authenticate_ldap_user = MagicMock(
            side_effect=AuthMappingError('mapping failed')
        )
        ldap_user_class.return_value = MagicMock()

        user = backend.authenticate(username='alice', password='secret')

        self.assertIsNone(user)


class SMTPEmailBackendTestCase(SimpleTestCase):
    @patch('django.core.mail.backends.smtp.ssl.create_default_context')
    @override_settings(
        EMAIL_CERT_VERIFY_MODE='custom_ca',
        EMAIL_CACERT_CONTENT='custom ca'
    )
    def test_custom_ca_is_added_to_default_context(self, create_context):
        context = create_context.return_value

        self.assertIs(EmailBackend().ssl_context, context)
        context.load_verify_locations.assert_called_once_with(cadata='custom ca')

    @patch('django.core.mail.backends.smtp.ssl.create_default_context')
    @override_settings(EMAIL_CERT_VERIFY_MODE='none')
    def test_certificate_verification_can_be_disabled(self, create_context):
        context = create_context.return_value

        self.assertIs(EmailBackend().ssl_context, context)
        self.assertFalse(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_NONE)


@override_settings(EMAIL_CERT_VERIFY_MODE='system', EMAIL_CACERT_CONTENT='')
class EmailSettingSerializerTestCase(SimpleTestCase):
    def get_serializer(self, **data):
        return EmailSettingSerializer(data={
            'EMAIL_HOST': 'smtp.example.test',
            'EMAIL_PORT': '587',
            **data,
        })

    def test_custom_ca_mode_requires_certificate(self):
        serializer = self.get_serializer(
            EMAIL_CERT_VERIFY_MODE='custom_ca', EMAIL_USE_TLS=True
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('EMAIL_CACERT_CONTENT', serializer.errors)

    def test_custom_ca_is_not_required_without_tls(self):
        serializer = self.get_serializer(
            EMAIL_CERT_VERIFY_MODE='custom_ca',
            EMAIL_USE_SSL=False,
            EMAIL_USE_TLS=False,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_private_key_is_rejected(self):
        serializer = self.get_serializer(
            EMAIL_CACERT_CONTENT='-----BEGIN PRIVATE KEY-----\nsecret'
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('EMAIL_CACERT_CONTENT', serializer.errors)

    def test_invalid_ca_certificate_is_rejected(self):
        serializer = self.get_serializer(EMAIL_CACERT_CONTENT='not a certificate')

        self.assertFalse(serializer.is_valid())
        self.assertIn('EMAIL_CACERT_CONTENT', serializer.errors)
