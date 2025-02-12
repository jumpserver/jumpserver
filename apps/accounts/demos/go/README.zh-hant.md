## 1. 簡介

本 API 提供了 PAM 查看資產賬號服務，支持 RESTful 風格的調用，返回數據採用 JSON 格式。

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
| asset    | str  | 是   | 資產 ID / 資產名稱 |
| account  | str  | 是   | 賬號 ID / 賬號名稱 |

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

## 使用方法

### 初始化

要使用 JumpServer PAM 客戶端，通過提供所需的 `endpoint`、`keyID` 和 `keySecret` 創建一個實例。

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
		"",                 // 留空以使用默認的組織 ID
	)
}
```

### 創建密碼請求

您可以通過指定資產或帳戶信息來創建請求。

```go
request, err := jms_pam.NewSecretRequest("Linux", "", "root", "")
if err != nil {
    fmt.Println("創建請求時出錯:", err)
    return
}
```

### 發送請求

使用客戶端的 `Send` 方法發送請求。

```go
secretObj, err := client.Send(request)
if err != nil {
    fmt.Println("發送請求時出錯:", err)
    return
}
```

### 處理響應

檢查密碼是否成功檢索，並相應地處理響應。

```go
if secretObj.Valid {
    fmt.Println("密碼:", secretObj.Secret)
} else {
    fmt.Println("獲取密碼失敗:", string(secretObj.Desc))
}
```

### 完整示例

以下是如何使用該客戶端的完整示例：

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
		fmt.Println("創建請求時出錯:", err)
		return
	}

	secretObj, err := client.Send(request)
	if err != nil {
		fmt.Println("發送請求時出錯:", err)
		return
	}

	if secretObj.Valid {
		fmt.Println("密碼:", secretObj.Secret)
	} else {
		fmt.Println("獲取密碼失敗:", string(secretObj.Desc))
	}
}
```

## 錯誤處理

該庫會在創建 `SecretRequest` 時返回無效參數的錯誤。這包括對有效 UUID 的檢查以及確保提供了必需的參數。

## 貢獻

歡迎貢獻！如有任何增強或錯誤修復，請提出問題或提交拉取請求。
