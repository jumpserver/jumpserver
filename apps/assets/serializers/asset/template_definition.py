# -*- coding: utf-8 -*-
#
"""
Asset import/export template definitions.

Define import/export column structure for each asset type based on
the Sangfor OSM template files.

Template file reference:
- asset_hosts.xlsx
- asset_devices.xlsx
- asset_databases.xlsx
- asset_webs.xlsx
- asset_clouds.xlsx
"""

from dataclasses import dataclass
from typing import Optional, Callable, List

from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from . import template_transforms as transforms


@dataclass
class TemplateColumn:
    header: str
    field_name: str
    help_text: str
    required: bool = False
    render_transform: Optional[Callable] = None
    parse_transform: Optional[Callable] = None


@dataclass
class AssetImportTemplate:
    columns: List[TemplateColumn]

    def get_column_headers(self):
        return [c.header for c in self.columns]

    def get_field_names(self):
        return [c.field_name for c in self.columns]

    def build_display_row(self, row_data):
        """
        将模板原始行转换为前端更新接口可直接提交的格式
        - platform: {"pk": <id>}
        - nodes: [{"pk": <node_id>, "name": <全路径>}]（由节点路径解析）
        - zone: {"pk": "<pk>", "name": "<名称>"}
        - protocols: [{"name", "port"}]
        - labels: [{"pk": <label_id>}]（由 name:value 解析）
        - is_active: bool
        - accounts 不参与资产创建/更新提交
        """
        display_row = {}
        for k, v in row_data.items():
            column = self.get_column_by_field_name(k)
            if not column:
                display_row[k] = v
                continue
            field_name = column.field_name
            if field_name == 'id':
                # ID 仅展示，导入新建资产时忽略
                display_row[k] = v
                continue
            if field_name == 'accounts':
                continue
            parsed = column.parse_transform(v) if column.parse_transform else v
            if field_name == 'platform':
                display_row[field_name] = {
                    'pk': parsed,
                    'name': str(v).strip(),
                } if parsed is not None else None
            elif field_name == 'zone':
                display_row[field_name] = {
                    'pk': parsed,
                    'name': str(v).strip(),
                } if parsed is not None else None
            elif field_name == 'nodes_display':
                # 直接返回节点路径列表，节点不存在时由后端创建接口自动创建
                display_row['nodes_display'] = parsed or []
            elif field_name == 'labels':
                # 直接返回 name:value 列表，标签不存在时由后端创建接口自动创建
                display_row[field_name] = parsed or []
            else:
                display_row[field_name] = parsed
        display_row.setdefault('directory_services', [])
        return display_row

    def get_help_texts(self):
        return [c.help_text for c in self.columns]

    def get_column_by_field_name(self, field_name):
        for c in self.columns:
            if c.field_name == field_name:
                return c
        return None

    def get_column_by_header(self, header):
        for c in self.columns:
            if c.header == header:
                return c
        return None


# ============================================================
# Shared column helpers (reused across asset types)
# ============================================================

def _id_column():
    return TemplateColumn(
        header=_('ID'),
        field_name='id',
        help_text=_('ID, asset unique identifier, leave blank when importing to create a new asset'),
        required=False,
        parse_transform=transforms.id_from_template,
    )


def _name_column(label, max_length=128):
    return TemplateColumn(
        header=format_lazy(_('{} (Required)'), label),
        field_name='name',
        help_text=format_lazy(_('{} name, max {} characters'), label, max_length),
        required=True,
    )


def _address_column(label, help_text, required=True):
    if required:
        header = format_lazy(_('{} (Required)'), label)
    else:
        header = label
    return TemplateColumn(
        header=header,
        field_name='address',
        help_text=help_text,
        required=required,
    )


def _platform_column(header, help_text):
    return TemplateColumn(
        header=header,
        field_name='platform',
        help_text=help_text,
        required=True,
        render_transform=transforms.platform_to_template,
        parse_transform=transforms.platform_from_template,
    )


def _nodes_display_column():
    return TemplateColumn(
        header=_('Node path (Required)'),
        field_name='nodes_display',
        help_text=_('Node path, format /root/child, auto-created if not exist'),
        required=True,
        render_transform=transforms.nodes_display_to_template,
        parse_transform=transforms.nodes_display_from_template,
    )


def _protocols_column(header, help_text, required=True):
    return TemplateColumn(
        header=header,
        field_name='protocols',
        help_text=help_text,
        required=required,
        render_transform=transforms.protocols_to_template,
        parse_transform=transforms.protocols_from_template,
    )


def _accounts_column():
    return TemplateColumn(
        header=_('Account info'),
        field_name='accounts',
        help_text=_(
            'Account info, JSON format '
            '[{"帐号名":"x","帐号密码":"x","帐号密钥":"x","是否是特权帐号":"是/否"}]'
        ),
        required=False,
        render_transform=transforms.accounts_to_template,
        parse_transform=transforms.accounts_from_template,
    )


def _zone_column():
    return TemplateColumn(
        header=_('Zone'),
        field_name='zone',
        help_text=_('Zone name, must be an existing zone under current organization'),
        required=False,
        render_transform=transforms.zone_to_template,
        parse_transform=transforms.zone_from_template,
    )


def _labels_column():
    return TemplateColumn(
        header=_('Tags'),
        field_name='labels',
        help_text=_('Tags, format ["key:value", ...], auto-created if not exist'),
        required=False,
        render_transform=transforms.labels_to_template,
        parse_transform=transforms.labels_from_template,
    )


def _is_active_column():
    return TemplateColumn(
        header=_('Active'),
        field_name='is_active',
        help_text=_('Is active, fill Yes/No'),
        required=False,
        parse_transform=transforms.boolean_from_template,
    )


def _comment_column(max_length=512):
    return TemplateColumn(
        header=_('Comment'),
        field_name='comment',
        help_text=format_lazy(_('Comment, max {} characters'), max_length),
        required=False,
    )


# ============================================================
# Host template — corresponds to asset_hosts.xlsx
# ============================================================

host_import_template = AssetImportTemplate(columns=[
    _id_column(),
    _name_column(_('Host name')),
    _address_column(
        _('IP/Host'),
        _('IP/Host, max 767 characters, supports IPv4/IPv6 and domain names'),
    ),
    _platform_column(
        _('Platform type (Required)'),
        _('Platform type, such as Windows, Linux'),
    ),
    _nodes_display_column(),
    _protocols_column(
        _('Protocols (Required)'),
        _('Protocols, format sftp/22;ssh/22;telnet/23;rdp/3389;vnc/5900'),
    ),
    _accounts_column(),
    _zone_column(),
    _labels_column(),
    _is_active_column(),
    _comment_column(),
])


# ============================================================
# Device template — corresponds to asset_devices.xlsx
# ============================================================

device_import_template = AssetImportTemplate(columns=[
    _id_column(),
    _name_column(_('Device name')),
    _address_column(
        _('IP/Host'),
        _('IP/Host, max 767 characters, supports IPv4/IPv6 and domain names'),
    ),
    _platform_column(
        _('Platform type (Required)'),
        _('Platform type, such as Cisco, H3C, Huawei'),
    ),
    _nodes_display_column(),
    _protocols_column(
        _('Protocols (Required)'),
        _('Protocols, format ssh/22;telnet/23'),
    ),
    _accounts_column(),
    _zone_column(),
    _labels_column(),
    _is_active_column(),
    _comment_column(),
])


# ============================================================
# Database template — corresponds to asset_databases.xlsx
# ============================================================

database_import_template = AssetImportTemplate(columns=[
    _id_column(),
    _name_column(_('Database name')),
    _address_column(
        _('Address'),
        _('Database address, max 767 characters, supports IPv4/IPv6 and domain names'),
    ),
    TemplateColumn(
        header=_('Platform/DB type (Required)'),
        field_name='platform',
        help_text=_('Platform/Database type, such as MySQL, MariaDB, PostgreSQL'),
        required=True,
        render_transform=transforms.platform_to_template,
        parse_transform=transforms.platform_from_template,
    ),
    _nodes_display_column(),
    TemplateColumn(
        header=_('Protocol (Required)'),
        field_name='protocols',
        help_text=_('Protocol, format mysql/4000, mariadb/3306'),
        required=True,
        render_transform=transforms.protocols_to_template,
        parse_transform=transforms.protocols_from_template,
    ),
    TemplateColumn(
        header=_('Default database (Required)'),
        field_name='db_name',
        help_text=_('Default database name'),
        required=True,
    ),
    _accounts_column(),
    TemplateColumn(
        header=_('CA cert'),
        field_name='ca_cert',
        help_text=_('CA certificate content'),
        required=False,
    ),
    TemplateColumn(
        header=_('Client cert'),
        field_name='client_cert',
        help_text=_('Client certificate content'),
        required=False,
    ),
    TemplateColumn(
        header=_('Client key'),
        field_name='client_key',
        help_text=_('Client key content'),
        required=False,
    ),
    TemplateColumn(
        header=_('Use SSL'),
        field_name='use_ssl',
        help_text=_('Use SSL, fill Yes/No'),
        required=False,
    ),
    TemplateColumn(
        header=_('PostgreSQL SSL mode'),
        field_name='pg_ssl_mode',
        help_text=_('PostgreSQL SSL mode, such as require, verify-ca, verify-full'),
        required=False,
    ),
    TemplateColumn(
        header=_('Ignore cert verify'),
        field_name='allow_invalid_cert',
        help_text=_('Ignore certificate verification, fill Yes/No'),
        required=False,
    ),
    _zone_column(),
    _labels_column(),
    _is_active_column(),
    _comment_column(),
])


# ============================================================
# Web template — corresponds to asset_webs.xlsx
# ============================================================

web_import_template = AssetImportTemplate(columns=[
    _id_column(),
    _name_column(_('Web name')),
    _address_column(
        _('URL'),
        _('URL address, such as http://172.18.18.7:9000'),
    ),
    _platform_column(
        _('Platform (Required)'),
        _('Platform type, such as Website'),
    ),
    _protocols_column(
        _('Protocols'),
        _('Protocols, format http/9000'),
        required=False,
    ),
    _nodes_display_column(),
    _accounts_column(),
    _zone_column(),
    _is_active_column(),
    _comment_column(),
    _labels_column(),
])


# ============================================================
# Cloud template — corresponds to asset_clouds.xlsx
# ============================================================

cloud_import_template = AssetImportTemplate(columns=[
    _id_column(),
    _name_column(_('Cloud service name')),
    _address_column(
        _('URL'),
        _('URL address, such as https://172.18.18.11:6443/'),
    ),
    _platform_column(
        _('Platform (Required)'),
        _('Platform type, such as Kubernetes, Vmware-vSphere'),
    ),
    _nodes_display_column(),
    _protocols_column(
        _('Protocols (Required)'),
        _('Protocols, format k8s/6443;http(s)/80'),
    ),
    _accounts_column(),
    _zone_column(),
    _labels_column(),
    _is_active_column(),
    _comment_column(),
])
