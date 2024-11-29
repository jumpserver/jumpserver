# JumpServer PAM クライアント

このパッケージは、JumpServer PAM API と対話し、さまざまなアセットのシークレットを取得するための Python クライアントを提供します。リクエストを送信し、レスポンスを処理するプロセスを簡素化します。

## 特徴

- リクエストを送信する前にパラメータを検証します。
- アセットおよびアカウントベースのシークレット取得をサポートします。
- HTTP 署名を使用して JumpServer PAM API と簡単に統合できます。

## インストール

以下のコマンドを使用して、パッケージを pip でインストールできます：

```bash
pip install jms_pam-0.0.1-py3-none-any.whl
```

## 要件

- `Python 3.6+`
- `requests`
- `httpsig`

## 使用方法

### 初期化

JumpServer PAM クライアントを使用するには、必要な `endpoint`、`key_id`、および `key_secret` を提供してインスタンスを作成します。

```python
from jms_pam import JumpServerPAM, SecretRequest

client = JumpServerPAM(
    endpoint='http://127.0.0.1',
    key_id='your-key-id',
    key_secret='your-key-secret'
)
```

### シークレットリクエストの作成

アセットまたはアカウント情報を指定して、シークレットのリクエストを作成できます。

```python
request = SecretRequest(asset='Linux', account='root')
```

### リクエストの送信

クライアントの `send` メソッドを使用してリクエストを送信します。

```python
secret_obj = client.send(request)
```

### レスポンスの処理

シークレットが正常に取得されたかどうかを確認し、レスポンスを適切に処理します。

```python
if secret_obj.valid:
    print('秘密: %s' % secret_obj.secret)
else:
    print('シークレットの取得に失敗しました: %s' % secret_obj.desc)
```

### 完全な例

以下は、クライアントの使用方法の完全な例です：

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
    print('シークレットの取得に失敗しました: %s' % secret_obj.desc)
```

## エラーハンドリング

ライブラリは、提供されたパラメータが検証要件を満たしていない場合に `RequestParamsError` を発生させます。これには、有効な UUID の確認やパラメータ間の相互依存性のチェックが含まれます。

## 貢献

貢献を歓迎します！改善やバグ修正のために、問題を開くかプルリクエストを送信してください。
