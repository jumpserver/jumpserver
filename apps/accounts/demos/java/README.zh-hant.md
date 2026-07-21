# 使用說明

## 1. 簡介

本 API 提供 PAM 資產帳號密碼查詢服務，支援 RESTful 風格呼叫，並以 JSON 格式傳回資料。

## 2. 環境要求

- `Java 11+`
- `HttpClient`

## 3. 使用方法

**請求方式**: `GET api/v1/accounts/integration-applications/account-secret/`

**請求參數**

| 參數名    | 類型   | 必填 | 說明            |
|----------|------|-----|---------------|
| asset    | str  | 是   | 資產名稱        |
| account  | str  | 是   | 帳號名稱        |

**回應範例**:
```json
{
    "id": "72b0b0aa-ad82-4182-a631-ae4865e8ae0e",
    "secret": "123456"
}
```

## 常見問題（FAQ）

Q: 如何取得 API Key？

A: 您可以在 PAM - 應用管理中建立應用，以產生 KEY_ID 和 KEY_SECRET。

## 版本歷史（Changelog）


| 版本號   | 變更內容              | 日期         |
| ----- | ----------------- |------------|
| 1.0.0 | 初始版本              | 2025-02-11 |
