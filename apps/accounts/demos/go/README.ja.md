# JumpServer PAM クライアント

このパッケージは、JumpServer PAM API と対話し、さまざまな資産のパスワードを取得するための Go クライアントを提供します。リクエストの送信とレスポンスの処理を簡素化します。

## 機能

- リクエスト送信前にパラメータを検証します。
- 資産およびアカウントに基づくパスワード取得をサポートします。
- HMAC-SHA256 署名を使用して認証を行い、JumpServer PAM API との統合を容易にします。

## 使用手順

1. **Go コードファイルのダウンロード**：
   コードファイルをプロジェクトディレクトリにダウンロードします。

2. **パッケージのインポート**：
   Go ファイルにパッケージをインポートすると、その機能を直接使用できます。

## 要件

- `Go 1.16+`
- `github.com/google/uuid`
- `gopkg.in/twindagger/httpsig.v1`

## 使用方法

### 初期化

JumpServer PAM クライアントを使用するには、必要な `endpoint`、`keyID`、および `keySecret` を提供してインスタンスを作成します。

```go
package main

import (
	"fmt"
	
	"your_module_path/jms_pam"
)

func main() {
	client := jms_pam.NewJumpServerPAM(
		"http://127.0.0.1", // あなたの JumpServer エンドポイントに置き換えてください
		"your-key-id",      // 実際の Key ID に置き換えてください
		"your-key-secret",  // 実際の Key Secret に置き換えてください
		"",                 // デフォルトの組織 ID を使用するには空のままにします
	)
}
```

### パスワードリクエストの作成

資産またはアカウント情報を指定してリクエストを作成できます。

```go
request, err := jms_pam.NewSecretRequest("Linux", "", "root", "")
if err != nil {
    fmt.Println("リクエスト作成中にエラー:", err)
    return
}
```

### リクエストの送信

クライアントの `Send` メソッドを使用してリクエストを送信します。

```go
secretObj, err := client.Send(request)
if err != nil {
    fmt.Println("リクエスト送信中にエラー:", err)
    return
}
```

### レスポンスの処理

パスワードが正常に取得されたかどうかを確認し、それに応じてレスポンスを処理します。

```go
if secretObj.Valid {
    fmt.Println("パスワード:", secretObj.Secret)
} else {
    fmt.Println("パスワードの取得に失敗:", string(secretObj.Desc))
}
```

### 完全な例

以下は、クライアントの使用方法に関する完全な例です。

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
		fmt.Println("リクエスト作成中にエラー:", err)
		return
	}

	secretObj, err := client.Send(request)
	if err != nil {
		fmt.Println("リクエスト送信中にエラー:", err)
		return
	}

	if secretObj.Valid {
		fmt.Println("パスワード:", secretObj.Secret)
	} else {
		fmt.Println("パスワードの取得に失敗:", string(secretObj.Desc))
	}
}
```

## エラーハンドリング

このライブラリは、`SecretRequest` を作成する際に無効なパラメータに対するエラーを返します。これには、有効な UUID の確認や、必要なパラメータが提供されていることの確認が含まれます。

## 貢献

貢献を歓迎します！改善やバグ修正のために問題を提起したり、プルリクエストを送信してください。
