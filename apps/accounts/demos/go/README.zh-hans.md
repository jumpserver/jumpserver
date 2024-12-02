# JumpServer PAM 客户端

该包提供了一个 Go 客户端，用于与 JumpServer PAM API 交互，以检索各种资产的密码。它简化了发送请求和处理响应的过程。

## 功能

- 在发送请求之前验证参数。
- 支持基于资产和账户的密码检索。
- 使用 HMAC-SHA256 签名进行身份验证，方便与 JumpServer PAM API 集成。

## 使用说明

1. **下载 Go 代码文件**：
   将代码文件下载到您的项目目录中。

2. **导入包**：
   在您的 Go 文件中导入该包，您即可直接使用其功能。

## 需求

- `Go 1.16+`
- `github.com/google/uuid`
- `gopkg.in/twindagger/httpsig.v1`

## 使用方法

### 初始化

要使用 JumpServer PAM 客户端，通过提供所需的 `endpoint`、`keyID` 和 `keySecret` 创建一个实例。

```go
package main

import (
	"fmt"
	
	"your_module_path/jms_pam"
)

func main() {
	client := jms_pam.NewJumpServerPAM(
		"http://127.0.0.1", // 替换为您的 JumpServer 端点
		"your-key-id",      // 替换为您的实际 Key ID
		"your-key-secret",  // 替换为您的实际 Key Secret
		"",                 // 留空以使用默认的组织 ID
	)
}
```

### 创建密码请求

您可以通过指定资产或账户信息来创建请求。

```go
request, err := jms_pam.NewSecretRequest("Linux", "", "root", "")
if err != nil {
    fmt.Println("创建请求时出错:", err)
    return
}
```

### 发送请求

使用客户端的 `Send` 方法发送请求。

```go
secretObj, err := client.Send(request)
if err != nil {
    fmt.Println("发送请求时出错:", err)
    return
}
```

### 处理响应

检查密码是否成功检索，并相应地处理响应。

```go
if secretObj.Valid {
    fmt.Println("密码:", secretObj.Secret)
} else {
    fmt.Println("获取密码失败:", string(secretObj.Desc))
}
```

### 完整示例

以下是如何使用该客户端的完整示例：

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
		fmt.Println("创建请求时出错:", err)
		return
	}

	secretObj, err := client.Send(request)
	if err != nil {
		fmt.Println("发送请求时出错:", err)
		return
	}

	if secretObj.Valid {
		fmt.Println("密码:", secretObj.Secret)
	} else {
		fmt.Println("获取密码失败:", string(secretObj.Desc))
	}
}
```

## 错误处理

该库会在创建 `SecretRequest` 时返回无效参数的错误。这包括对有效 UUID 的检查以及确保提供了必需的参数。

## 贡献

欢迎贡献！如有任何增强或错误修复，请提出问题或提交拉取请求。
