# JumpServer PAM Python SDK / Agent

Python 3.9+ は認証情報ポリシー SDK を提供します。Go 製 jms-pam-agent は Python 不要で、ローカルファイル、固定アクションまたは Socket で認証情報を配信します。Linux、macOS、Windows でフォアグラウンド実行でき、組み込みの systemd インストールは Linux 専用です。

<!-- agent-doc:start -->

## Go Agent の接続

systemd とアプリケーションユーザーのある Linux ホストを用意し、接続ウィザードから jms_pam_agent.json を取得します。Go バイナリをビルドまたは取得してインストールし、安定した一意のインスタンス ID を指定します。ローカル設定は /etc/jms-pam-agent/agent.json、サービス名は jms-pam-agent です。.

```bash
cd apps/accounts/clients/go
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
chmod 0600 ./jms_pam_agent.json
sudo /usr/local/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

組み込みインストーラーには Linux と root が必要です。macOS、非 root Linux、Windows ではウィザードで JSON または Socket を選び、init-local と run --local --config を実行してください。初期化は一度だけ行い、生成された非公開のローカル設定を再利用します。フォアグラウンドモードでは systemd 操作を行いません。

`/etc/jms-pam-agent/agent.json`: `0600`; `state_file`, `event_file`, `delivery.delivery_root`, `delivery.socket_path`.

- JSON: `/opt/jumpserver-pam/credentials/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<credential-key>.env`
- Unix Socket: `/run/jms-pam-agent/agent.sock`

JSON はファイル配信、EnvironmentFile は固定した systemd サービス、Unix Socket はローカル API に使用します。Agent は配信成功後に配信リビジョンを記録し、アプリケーションは検証・適用後に生効リビジョンを記録します。Socket はアプリケーションユーザー所有、0600 で、そのユーザーとして操作します。

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<credential-key>.env
```

systemd unit で EnvironmentFile を指定します。reload はアプリケーションがファイルを再読込する場合だけ使用してください。実行中のプロセスに新しい環境変数は注入されません。パス、ユーザー、サービス、操作権限はインストール時に固定され、拡張には再インストールが必要です。

ローカル rules でファイル、JSON/EnvironmentFile または信頼済みテンプレートと、systemd reload/restart や固定実行ファイルを設定します。スクリプトは標準入力で認証情報 JSON を受け取り、固定引数とタイムアウトを使い、適用を検証してから成功を返します。Core は実行パスや権限を拡張できません。設定変更後に Agent を再起動します。

認証には app_id、app_secret、org_id と安定した instance_id を使用し、認可範囲はアプリケーションに関連付けたポリシーに従います。すべてのパスとサービス操作はローカル設定です。state_file は最新パスワードを保持し、event_file は秘密を含まないイベント情報を追記します。delivery は既定の出力、rules はファイル、テンプレートと reload/restart または固定スクリプトを指定します。更新通知で最新値を取得・保存し、ファイルを原子的に置き換えてから操作を実行します。失敗は再試行します。rules の key には get_accounts の credentials[].key を使用します。購読 key にはアカウント ID が含まれます。空の rules は key ごとの既定ファイルを出力します。

```json
{
  "endpoint": "https://jumpserver.example.com",
  "app_id": "<application-id>",
  "app_secret": "<application-secret>",
  "org_id": "<org-id>",
  "instance_id": "orders-node-1",
  "state_file": "/var/lib/jms-pam-agent/state.json",
  "event_file": "/var/lib/jms-pam-agent/events.jsonl",
  "reconcile_interval": 300,
  "delivery": {
    "delivery_mode": "json",
    "delivery_root": "/opt/jumpserver-pam/credentials",
    "socket_path": "/run/jms-pam-agent/agent.sock",
    "app_user": "orders",
    "systemd_unit": "",
    "systemd_action": ""
  },
  "rules": []
}
```

`rules`:

```json
[
  {
    "keys": [
      "<credential-key>"
    ],
    "files": [
      {
        "path": "/etc/order-service/database.json",
        "format": "template",
        "template_file": "/etc/jms-pam-agent/orders-db.tmpl",
        "owner": "orders"
      }
    ],
    "action": {
      "type": "systemd",
      "unit": "order-service.service",
      "operation": "reload",
      "timeout_seconds": 30
    }
  }
]
```

`/etc/jms-pam-agent/orders-db.tmpl`:

```gotemplate
{
  "username": {{json (index .Credentials "<credential-key>").Username}},
  "password": {{json (index .Credentials "<credential-key>").Secret}}
}
```

```bash
jms-pam-agent get_accounts
jms-pam-agent get_secret '<account-id>'
sudo jms-pam-agent check-config
sudo systemctl restart jms-pam-agent
```


### ローカル API と確認

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

交互ローテーションでは実際の接続を検証し、接続プールを切り替えて古い接続を解放した後に、正確な key、revision、account_id を確認します。認証情報変更の購読では確認は不要です。接続検証に失敗した場合は確認してはいけません。

```bash
/usr/local/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jms-pam-agent/agent.sock'
```

confirm は交互ローテーション専用です。ローカル確認は先に永続化され、confirmed は Core が受理済み、pending は後で再試行する状態です。ファイル書込やサービス再起動だけで確認しないでください。

### トラブルシューティング

```bash
sudo systemctl start jms-pam-agent
sudo systemctl status jms-pam-agent --no-pager
sudo journalctl -u jms-pam-agent -n 100 --no-pager
sudo systemctl restart jms-pam-agent
```

Agent は起動時、関連イベント受信時、300 秒ごとに同期します。通信障害時は取得済みの最新の許可済み認証情報を保持し、識別情報または権限が拒否されると Socket の取得を停止します。署名付き同期の成功で復旧します。配信済みファイルは保持され、SIGINT/SIGTERM でサービス、接続、読取スレッドを終了します。

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Python SDK の接続

ポリシーを作成してアプリケーションに関連付け、資産アカウントを許可し、接続ウィザードから jms_pam_config.py を取得します。Python 3.9+ が必要です。以下のリポジトリ用コマンド、またはダウンロード済み SDK のディレクトリで python3 -m pip install . を実行します。

```bash
python3 -m pip install ./apps/accounts/clients/python
```

jms_pam_config.py をアプリケーションから読み込める場所に配置します。client_options は識別情報を含むため、コミットやログ出力は禁止です。各レプリカに安定した一意の instance_id を設定します。get_credential は account_id またはローテーション用 key のどちらか一方だけを受け取ります。

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


with Client(instance_id=instance_id, **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### イベントと認証情報の適用

初回・再接続の snapshot と credential.updated を処理します。例では subscription と alternating_rotation を分けています。apply_credential で接続を検証し、接続プールを切り替え、古い接続を解放してください。未実装の関数は例外を発生させ、未適用の認証情報の確認を防止します。

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def apply_credential(credential):
    raise NotImplementedError('アプリケーションの認証情報切替を実装して検証してください')


with Client(instance_id=instance_id, **client_options) as client:
    for event in client.watch_credential_events():
        if event.get("event") == "snapshot":
            updates = event.get("credentials", [])
        elif event.get("event") == "credential.updated":
            updates = [event]
        else:
            continue
        for update in updates:
            mode = update.get("credential_mode")
            key = update.get("credential_key") or update.get("key")
            account_id = update.get("account_id")
            if mode == "subscription" and account_id and key:
                policy_key = key if key.endswith(f":{account_id}") else f"{key}:{account_id}"
                credential = client.get_credential(key=policy_key, allow_local_fallback=False)
            elif mode == "alternating_rotation" and key:
                credential = client.get_credential(key=key, allow_local_fallback=False)
            else:
                continue
            apply_credential(credential)
            if mode == "alternating_rotation":
                client.confirm_credential(
                    key=credential.key,
                    revision=credential.revision,
                    account_id=credential.account.id,
                )
```

交互ローテーションでは実際の接続を検証し、接続プールを切り替えて古い接続を解放した後に、正確な key、revision、account_id を確認します。認証情報変更の購読では確認は不要です。接続検証に失敗した場合は確認してはいけません。

SDK は業務イベントを返す前に received 受領通知を可能な範囲で自動送信します。アプリケーションによる追加送信は不要です。受領通知は読み取り済みを表すだけで、認証情報の適用や確認の代わりにはなりません。初回接続と再接続のスナップショットを処理してください。snapshot と pong に受領通知は不要です。

## イベントハンドラー

ローカル状態を初期化してから監視を開始します。Python と Node.js はサブクラス、Go は EventHandlers、Java は CredentialEventListener を使用します。例の接続切替処理を実装してください。従来の API も利用できます。

```python
"""Subscription example using subclass hooks; demo.py retains the iterator API."""

from jms_pam import Client
from jms_pam_config import client_options


class MyClient(Client):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.credentials = {}

    def on_event(self, event):
        if event.get("event") == "snapshot":
            authorized_keys = {item["key"] for item in event.get("credentials", [])}
            for key in self.credentials.keys() - authorized_keys:
                # Also release this key's application connections.
                del self.credentials[key]

    def on_credential_changed(self, credential):
        # Validate and switch application connections using credential.asset and
        # credential.account. The handler must be safe to repeat on retry/reconnect.
        # Never log credential.account.secret or authentication headers.
        raise NotImplementedError("Implement the application connection update first")
        # Save only after the application has successfully switched connections:
        # self.credentials[credential.key] = credential

    def on_credential_revoked(self, event):
        self.credentials.pop(event.get("credential_key"), None)
        # Also release the affected application connections.


with MyClient(instance_id="order-service-node-1", **client_options) as client:
    client.watch_events()
```

初回・再接続の snapshot と credential.updated はモード別に認証情報を取得し、ハンドラーを順番に呼び出します。受信と処理は上限 128 件のキューで接続され、満杯時は受信を待機します。取得・適用の失敗は 1–30 秒の指数バックオフで再試行し、毎回取得し直します。同じ対象の更新は再試行を置換し、snapshot は範囲を更新、失効・設定変更は再試行を解除します。処理は繰り返し可能にしてください。観測・失効フックは自動再試行しません。コマンドは実行権の取得が必要です。received は受信のみを示し、SDK はローテーションを自動確認しません。古いリビジョンのイベントは、新しいリビジョンの取得の再試行を取り消しません。

`watch_events(stop_event=...)` / `start_events(stop_event=...)`; `stop_events()` / `close()`

watch_events は停止まで待機します。start_events は初回同期の完了を保証しないため、業務の準備を待ってください。クライアントごとに監視は 1 つです。stop_events と close は処理を待ちます。フック内から停止できます。clone はサブクラスの状態を再初期化します。

### 最新の認証情報とバックエンド障害

取得はまず API を呼びます。取得成功時に保持値を更新し、古いバージョンで新しい値を上書きせず、時間による有効期限も設けません。タイムアウト、ネットワーク障害、HTTP 5xx の場合だけ、同じ検索条件の最後に取得した値をローカル由来のフラグ付きで返します。保持値がなければ元のエラーです。SDK は更新・失効・終了までクライアントのメモリに保持し、clone や再起動は空から始まります。Agent は保護された既存のローカル状態に保存します。HTTP 401/403/404 または client_upgrade_required は SDK の保持値を消去して失敗し、不正な成功応答も失敗します。失効は対象を、snapshot は認可範囲外を削除します。設定変更時は次の snapshot で範囲を確認するまで保持します。Agent は HTTP 同期の前に明示的な取り消しと snapshot の範囲縮小を適用して保存し、バックエンド障害中や再起動後も該当するローカル取得を停止します。credential_not_found（HTTP 400）でも SDK の保持値を削除します。 account_id による直接 pull には常にライブ API 応答が必要です。push の snapshot はキャッシュされた pull 認可を示しません。

- `credential.from_local`
- `get_credential(key=..., allow_local_fallback=False)` / `get_credential(account_id=..., allow_local_fallback=False)`

管理された監視を有効にすると、snapshot と credential.updated が自動で取得し、保持値を更新してから業務フックを呼びます。更新失敗時は前の値を保持し再試行します。Agent も更新通知で取得し、障害時は既存値を保持します。更新や手動切替には下記の API 取得必須の呼び出しを使用してください。保持値を新しく取得したバージョンと見なしたり、ローテーションを自動確認したりしません。

アイドル時は 10 秒ごとに ping を送り、約 30 秒メッセージがなければ再接続します。待機は 1–30 秒の指数バックオフで毎回再署名します。snapshot は現在の状態を復元し、履歴イベントは再送しません。



### アプリケーションコマンド

list_application_commands で保留中の要求を取得し、execute_application_command(event, handler) で実行権を申請します。accepted が true の場合だけ処理します。切替処理は要求されたアカウントとリビジョンを検証して適用・確認し、再起動処理はヘルスチェック後に成功を報告します。失敗の報告エラーは元の処理例外を隠しません。

### 主なメソッド

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `watch_events(stop_event=...)` / `start_events(stop_event=...)` / `stop_events()`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

with または close で HTTP セッションとイベント接続を閉じ、clone で独立したセッションを作成します。HTTP、ネットワーク、認証、解析のエラーは code、status_code、detail、original_error を持つ PAMError になります。一時障害を再試行し、権限拒否を明示的に処理してください。

新規コードは snake_case のキーワードメソッドと dataclass 属性を使います。旧 credential.v1 API は DeprecationWarning とともに保持されます。SDK と Agent はバージョン 1 プロトコルを共有し、sync_agent は保持済みと配信済みのリビジョンを KnownRevision で指定します。

<!-- sdk-doc:end -->
