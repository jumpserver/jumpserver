# JumpServer PAM 客戶端

此套件提供了一個 Python 客戶端，用於與 JumpServer PAM API 互動，以檢索各種資產的秘密。它簡化了發送請求和處理響應的過程。

## 特性

- 在發送請求之前驗證參數。
- 支持基於資產和帳戶的秘密檢索。
- 通過 HTTP 簽名輕鬆集成 JumpServer PAM API。

## 安裝

您可以通過 pip 安裝此套件：

```bash
pip install jms_pam-0.0.1-py3-none-any.whl
```

## 需求

- `Python 3.6+`
- `requests`
- `httpsig`

## 使用方法

### 初始化

要使用 JumpServer PAM 客戶端，通過提供所需的 `endpoint`、`key_id` 和 `key_secret` 創建一個實例。

```python
from jms_pam import JumpServerPAM, SecretRequest

client = JumpServerPAM(
    endpoint='http://127.0.0.1',
    key_id='your-key-id',
    key_secret='your-key-secret'
)
```

### 創建秘密請求

您可以通過指定資產或帳戶信息來創建一個秘密請求。

```python
request = SecretRequest(asset='Linux', account='root')
```

### 發送請求

使用客戶端的 `send` 方法發送請求。

```python
secret_obj = client.send(request)
```

### 處理響應

檢查秘密是否成功檢索，並相應地處理響應。

```python
if secret_obj.valid:
    print('秘密: %s' % secret_obj.secret)
else:
    print('獲取秘密失敗: %s' % secret_obj.desc)
```

### 完整示例

以下是如何使用該客戶端的完整示例：

```python
from jumpserver_pam_client import JumpServerPAM, SecretRequest

client = JumpServerPAM(
    endpoint='http://127.0.0.1',
    key_id='your-key-id',
    key_secret='your-key-secret'
)

request = SecretRequest(asset='Linux', account='root')
secret_obj = client.send(request)

if secret_obj.valid:
    print('秘密: %s' % secret_obj.secret)
else:
    print('獲取秘密失敗: %s' % secret_obj.desc)
```

## 錯誤處理

如果提供的參數不符合驗證要求，該庫將引發 `RequestParamsError`。這包括對有效 UUID 的檢查和參數之間的相互依賴性檢查。

## 貢獻

歡迎貢獻！請打開一個問題或提交拉取請求，以進行任何增強或修復錯誤。
