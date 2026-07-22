# 使用說明

## 1. 簡介

本 API 提供 PAM 資產帳號密碼查詢服務，支援 RESTful 風格呼叫，並以 JSON 格式傳回資料。

## 2. 環境要求

- `Go 1.16+`
- `crypto/hmac`
- `crypto/sha256`
- `encoding/base64`
- `net/http`

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

## 使用方法

### 初始化

要使用 JumpServer PAM 客戶端，請提供所需的 `endpoint`、`keyID` 和 `keySecret` 來建立實例。

```go
package main

import (
	"fmt"

	"your_module_path/jms_pam"
)

func main() {
	client := jms_pam.NewJumpServerPAM(
		"http://127.0.0.1", // 替換為您的 JumpServer 端點
		"your-key-id",      // 替換為您的實際 Key ID
		"your-key-secret",  // 替換為您的實際 Key Secret
		"",                 // 留空以使用預設的組織 ID
	)
}
```

### 建立密碼請求

您可以透過指定資產或帳號資訊來建立請求。

```go
request, err := jms_pam.NewSecretRequest("Linux", "", "root", "")
if err != nil {
    fmt.Println("建立請求時發生錯誤:", err)
    return
}
```

### 傳送請求

使用客戶端的 `Send` 方法傳送請求。

```go
secretObj, err := client.Send(request)
if err != nil {
    fmt.Println("傳送請求時發生錯誤:", err)
    return
}
```

### 處理回應

檢查是否成功取得密碼，並據此處理回應。

```go
if secretObj.Valid {
    fmt.Println("密碼:", secretObj.Secret)
} else {
    fmt.Println("取得密碼失敗:", string(secretObj.Desc))
}
```

### 完整範例

以下是使用此客戶端的完整範例：

```go
package main

import (
	"fmt"

	"your_module_path/jms_pam"
)

func main() {
	client := jms_pam.NewJumpServerPAM(
		"http://127.0.0.1",
		"your-key-id",
		"your-key-secret",
		"",
	)

	request, err := jms_pam.NewSecretRequest("Linux", "", "root", "")
	if err != nil {
		fmt.Println("建立請求時發生錯誤:", err)
		return
	}

	secretObj, err := client.Send(request)
	if err != nil {
		fmt.Println("傳送請求時發生錯誤:", err)
		return
	}

	if secretObj.Valid {
		fmt.Println("密碼:", secretObj.Secret)
	} else {
		fmt.Println("取得密碼失敗:", string(secretObj.Desc))
	}
}
```

## 錯誤處理

此程式庫會在建立 `SecretRequest` 時針對無效參數傳回錯誤，包括檢查 UUID 是否有效，以及確認已提供必要參數。

## 貢獻

歡迎貢獻！如有功能改進或錯誤修正，請提出問題或提交拉取請求。
