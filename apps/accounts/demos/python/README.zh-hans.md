# JumpServer PAM 客户端

该包提供了一个 Python 客户端，用于与 JumpServer PAM API 交互，以检索各种资产的密码。它简化了发送请求和处理响应的过程。

## 特性

- 在发送请求之前验证参数。
- 支持基于资产和账户的密码检索。
- 通过 HTTP 签名轻松集成 JumpServer PAM API。

## 安装

您可以通过 pip 安装该包：

```bash
pip install jms_pam-0.0.1-py3-none-any.whl
```

## 需求

- `Python 3.6+`
- `requests`
- `httpsig`

## 使用方法

### 初始化

要使用 JumpServer PAM 客户端，通过提供所需的 `endpoint`、`key_id` 和 `key_secret` 创建一个实例。

```python
from jms_pam import JumpServerPAM, SecretRequest

client = JumpServerPAM(
    endpoint='http://127.0.0.1',
    key_id='your-key-id',
    key_secret='your-key-secret'
)
```

### 创建密码请求

您可以通过指定资产或账户信息来创建一个密码请求。

```python
request = SecretRequest(asset='Linux', account='root')
```

### 发送请求

使用客户端的 `send` 方法发送请求。

```python
secret_obj = client.send(request)
```

### 处理响应

检查密码是否成功检索，并相应地处理响应。

```python
if secret_obj.valid:
    print('密码: %s' % secret_obj.secret)
else:
    print('获取密码失败: %s' % secret_obj.desc)
```

### 完整示例

以下是如何使用该客户端的完整示例：

```python
from jms_pam import JumpServerPAM, SecretRequest

client = JumpServerPAM(
    endpoint='http://127.0.0.1',
    key_id='your-key-id',
    key_secret='your-key-secret'
)

request = SecretRequest(asset='Linux', account='root')
secret_obj = client.send(request)

if secret_obj.valid:
    print('密码: %s' % secret_obj.secret)
else:
    print('获取密码失败: %s' % secret_obj.desc)
```

## 错误处理

如果提供的参数不符合验证要求，库会引发 `RequestParamsError`。这包括对有效 UUID 的检查和参数之间的相互依赖性检查。

## 贡献

欢迎贡献！请打开一个问题或提交拉取请求，以进行任何增强或修复错误。
