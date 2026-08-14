# -*- coding: utf-8 -*-
#
"""
资产导入导出模板格式转换函数

提供模板格式与 serializer 格式之间的双向转换：
- to_template: serializer 格式 → 模板格式（导出时使用）
- from_template: 模板格式 → serializer 格式（导入时使用）
"""

import json
from uuid import UUID


# ============================================================
# 协议转换
# 模板格式: "ssh/22;rdp/3389;telnet/23"
# Serializer 格式: [{"name": "ssh", "port": 22}, {"name": "rdp", "port": 3389}]
# ============================================================

def protocols_to_template(value):
    """导出: 协议列表 → 分号分隔字符串"""
    if not value:
        return ''
    if isinstance(value, str):
        return value
    parts = []
    for p in value:
        if isinstance(p, dict):
            parts.append(f"{p.get('name', '')}/{p.get('port', '')}")
        else:
            parts.append(str(p))
    return ';'.join(parts)


def protocols_from_template(value):
    """导入: 分号分隔字符串 → 协议列表"""
    if not value:
        return []
    if isinstance(value, list):
        return value
    result = []
    for item in str(value).split(';'):
        item = item.strip()
        if not item:
            continue
        if '/' in item:
            name, port = item.split('/', 1)
            result.append({'name': name.strip(), 'port': int(port.strip())})
        else:
            result.append({'name': item, 'port': 0})
    return result


# ============================================================
# 帐号信息转换
# 模板格式: [{"帐号名": "x", "帐号密码": "x", "帐号密钥": "x", "是否是特权帐号": "是"}]
# Serializer 格式: [{"name": "x", "username": "x", "secret": "x", "secret_type": "password", "privileged": true}]
# ============================================================

def accounts_to_template(value):
    """导出: 帐号列表（英文键） → 帐号列表（中文键）"""
    if not value:
        return ''
    if isinstance(value, str):
        return value
    result = []
    for account in value:
        if not isinstance(account, dict):
            continue
        item = {'帐号名': account.get('name', '') or account.get('username', '')}
        secret_type = account.get('secret_type', 'password')
        secret = account.get('secret', '')
        if secret_type == 'password':
            item['帐号密码'] = secret
        elif secret_type == 'ssh_key':
            item['帐号密钥'] = secret
        privileged = account.get('privileged', False)
        item['是否是特权帐号'] = '是' if privileged else '否'
        result.append(item)
    return json.dumps(result, ensure_ascii=False)


def accounts_from_template(value):
    """导入: 帐号列表（中文键） → 帐号列表（英文键）"""
    if not value:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(value, list):
        return []
    result = []
    for account in value:
        if not isinstance(account, dict):
            continue
        name = account.get('帐号名', '')
        item = {
            'name': name,
            'username': name,
        }
        password = account.get('帐号密码', '')
        ssh_key = account.get('帐号密钥', '')
        if ssh_key:
            item['secret'] = ssh_key
            item['secret_type'] = 'ssh_key'
        else:
            item['secret'] = password
            item['secret_type'] = 'password'
        privileged = account.get('是否是特权帐号', '')
        item['privileged'] = str(privileged).lower() in ('是', 'yes', 'true', '1')
        result.append(item)
    return result


# ============================================================
# 平台转换
# 模板格式: "Linux"
# Serializer 格式: {"id": "xxx", "name": "Linux", "type": "linux"}
# ============================================================

def platform_to_template(value):
    """导出: 平台对象 → 平台名称"""
    if not value:
        return ''
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get('name', '') or value.get('value', '')
    return str(value)


def _name_or_pk(value):
    """从模板值中提取名称字符串或 pk（int/UUID），空值返回 None"""
    if value is None or value == '-':
        return None
    if isinstance(value, dict):
        value = value.get('id') or value.get('pk') or value.get('name')
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, UUID)):
        return value if isinstance(value, UUID) else int(value)
    value = str(value).strip()
    if not value:
        return None
    if value.isdigit():
        return int(value)
    return value


def platform_from_template(value):
    """导入: 平台名称 → 平台 pk（按名称查询，平台为全局模型），解析失败返回 None"""
    value = _name_or_pk(value)
    if value is None:
        return None
    if isinstance(value, (int, UUID)):
        return value
    from assets.models import Platform
    platform = Platform.objects.filter(name=value).first()
    if platform:
        return platform.pk
    return None


# ============================================================
# 网域转换
# 模板格式: "default"
# Serializer 格式: {"id": "xxx", "name": "default"}
# ============================================================

def zone_to_template(value):
    """导出: 网域对象 → 网域名称"""
    if not value:
        return ''
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get('name', '')
    return str(value)


def zone_from_template(value):
    """导入: 网域名称 → 网域 pk（按名称查询当前组织下的网域），解析失败返回 None"""
    value = _name_or_pk(value)
    if value is None:
        return None
    if isinstance(value, (int, UUID)):
        return value
    from assets.models import Zone
    zone = Zone.objects.filter(name=value).first()
    if zone:
        return zone.pk
    return None


# ============================================================
# 标签转换
# 模板格式: ["标签名:标签值", ...]
# Serializer 格式: [{"name": "key", "value": "val"}, ...]
# ============================================================

def labels_to_template(value):
    """导出: 标签列表 → 字符串列表"""
    if not value:
        return ''
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(f"{item.get('name', '')}:{item.get('value', '')}")
            else:
                parts.append(str(item))
        return json.dumps(parts, ensure_ascii=False)
    return str(value)


def labels_from_template(value):
    """导入: 标签字符串/列表 → 标签列表
    支持格式: JSON 数组字符串 '["env:prod"]'、纯文本 'env:prod' 或 'env:prod;test:1'
    """
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        value = value.strip()
        if value.startswith('['):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []
            return value if isinstance(value, list) else []
        # 纯文本: 分号分隔的 name:value
        return [v.strip() for v in value.split(';') if v.strip()]
    return []


# ============================================================
# 节点路径转换
# 模板格式: "/default;/default/child"
# Serializer 格式: ["/default", "/default/child"]
# ============================================================

def nodes_display_to_template(value):
    """导出: 节点路径列表 → 分号分隔字符串"""
    if not value:
        return ''
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ';'.join(str(v) for v in value)
    return str(value)


def nodes_display_from_template(value):
    """导入: 分号分隔字符串 → 节点路径列表"""
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [v.strip() for v in str(value).split(';') if v.strip()]


# ============================================================
# 布尔转换
# 模板格式: "是"/"否"
# Serializer 格式: True/False
# ============================================================

def boolean_from_template(value):
    """导入: 是/否/yes/no/true/false/1/0 → bool"""
    if value is None or value == '' or value == '-':
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('是', 'yes', 'true', '1', 'y', 't')


# ============================================================
# ID 转换
# 模板格式: UUID 字符串（导出时展示）
# 导入时忽略（新建资产留空）
# ============================================================

def id_from_template(value):
    """导入: 忽略 ID 列，导入均为新建资产"""
    return None
