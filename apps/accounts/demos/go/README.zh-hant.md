# JumpServer PAM 客戶端

該包提供了一個 Go 客戶端，用於與 JumpServer PAM API 交互，以檢索各種資產的密碼。它簡化了發送請求和處理響應的過程。

## 功能

- 在發送請求之前驗證參數。
- 支持基於資產和帳戶的密碼檢索。
- 使用 HMAC-SHA256 簽名進行身份驗證，方便與 JumpServer PAM API 集成。

## 使用說明

1. **下載 Go 代碼文件**：
   將代碼文件下載到您的項目目錄中。

2. **導入包**：
   在您的 Go 文件中導入該包，您即可直接使用其功能。

## 需求

- `Go 1.16+`
- `github.com/google/uuid`
- `gopkg.in/twindagger/httpsig.v1`

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
