# 使用說明

## 1. 簡介

本 API 提供了 PAM 查看資產賬號服務，支持 RESTful 風格的調用，返回數據採用 JSON 格式。

## 2. 環境要求

- `Python 3.11+`
- `requests==2.31.0`
- `httpsig==1.3.0`

## 3. 使用方法
**請求方式**: `GET api/v1/accounts/integration-applications/account-secret/`

**請求參數**

| 參數名      | 類型   | 必填 | 說明           |
|------------|------|----|--------------|
| asset    | str  | 是  | 資產 ID / 資產名稱 |
| account    | str | 是  | 賬號 ID / 賬號名稱 |

**響應示例**:
```json
{
    "id": "72b0b0aa-ad82-4182-a631-ae4865e8ae0e", 
    "secret": "123456"
}
```

## 常見問題（FAQ）

Q: API Key 如何獲取？

A: 你可以在 PAM - 應用管理 創建應用生成 KEY_ID 和 KEY_SECRET。

## 版本歷史（Changelog）


| 版本號   | 變更內容              | 日期         |
| ----- | ----------------- |------------|
| 1.0.0 | 初始版本              | 2025-02-11 |
