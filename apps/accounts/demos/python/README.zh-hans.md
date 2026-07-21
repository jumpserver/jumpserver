# 使用说明

## 1. 简介

本 API 提供 PAM 资产账号密码查询服务，支持 RESTful 风格调用，并以 JSON 格式返回数据。

## 2. 环境要求

- `Python 3.11+`
- `requests==2.31.0`
- `httpsig==1.3.0`

## 3. 使用方法
**请求方式**: `GET api/v1/accounts/integration-applications/account-secret/`

**请求参数**

| 参数名      | 类型   | 必填 | 说明           |
|------------|------|----|--------------|
| asset      | str | 是  | 资产名称       |
| account    | str | 是  | 账号名称       |

**响应示例**:
```json
{
    "id": "72b0b0aa-ad82-4182-a631-ae4865e8ae0e",
    "secret": "123456"
}
```

## 常见问题（FAQ）

Q: API Key 如何获取？

A: 您可以在 PAM - 应用管理中创建应用，以生成 KEY_ID 和 KEY_SECRET。

## 版本历史（Changelog）


| 版本号   | 变更内容              | 日期         |
| ----- | ----------------- |------------|
| 1.0.0 | 初始版本              | 2025-02-11 |
