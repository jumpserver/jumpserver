# JumpServer PAM Python SDK / Agent

Python 3.9+ で認証情報ポリシー SDK と Linux Agent を利用できます。SDK はアプリケーション AK/SK を使い、Agent は他の言語でも利用できるようにローカルで認証情報を配信します。

<!-- agent-doc:start -->

## Linux Agent の接続

systemd、Python 3.9+、アプリケーションユーザーを備えた Linux ホストを準備します。ポリシーにアプリケーションを関連付け、対象アカウントを許可します。交互ローテーションでは両方のアカウントが必要です。接続ウィザードで Agent、実行ユーザー、インストール先、配信方法を選び、jms_pam_agent.json をダウンロードします。SDK をインストールして以下の既定パスのコマンドを実行し、各レプリカに安定した一意の ID を指定します。

```bash
sudo python3 -m venv /opt/jumpserver-pam/venv
sudo /opt/jumpserver-pam/venv/bin/python -m pip install '<sdk-directory>'
sudo /opt/jumpserver-pam/venv/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

以下は既定のパスです。configuration-id はブートストラップ、credential-key はポリシーから取得します。実際のインストール先を使用してください。ブートストラップには AK/SK が含まれるため、アクセスを制限し、インストール後にダウンロード済みファイルを削除して設定を保護します。

- JSON: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env`
- Unix Socket: `/run/jumpserver-pam/<configuration-id>/agent.sock`

JSON はファイル配信、EnvironmentFile は固定した systemd サービス、Unix Socket はローカル API に使用します。Agent は配信成功後に配信リビジョンを記録し、アプリケーションは検証・適用後に生効リビジョンを記録します。Socket はアプリケーションユーザー所有、0600 で、そのユーザーとして操作します。

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env
```

systemd unit で EnvironmentFile を指定します。reload はアプリケーションがファイルを再読込する場合だけ使用してください。実行中のプロセスに新しい環境変数は注入されません。パス、ユーザー、サービス、操作権限はインストール時に固定され、拡張には再インストールが必要です。

### ローカル API と確認

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

交互ローテーションでは実際の接続を検証し、接続プールを切り替えて古い接続を解放した後に、正確な key、revision、account_id を確認します。認証情報変更の購読では確認は不要です。接続検証に失敗した場合は確認してはいけません。

```bash
/opt/jumpserver-pam/venv/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jumpserver-pam/<configuration-id>/agent.sock'
```

confirm は交互ローテーション専用です。ローカル確認は先に永続化され、confirmed は Core が受理済み、pending は後で再試行する状態です。ファイル書込やサービス再起動だけで確認しないでください。

### トラブルシューティング

```bash
sudo systemctl status 'jms-pam-agent-<configuration-id>.service' --no-pager
sudo journalctl -u 'jms-pam-agent-<configuration-id>.service' -n 100 --no-pager
sudo systemctl restart 'jms-pam-agent-<configuration-id>.service'
```

Agent は起動時、関連イベント受信時、300 秒ごとに同期します。通信障害時は許可済みキャッシュを保持し、識別情報または権限が拒否されると Socket の取得を停止します。署名付き同期の成功で復旧します。配信済みファイルは保持され、SIGINT/SIGTERM でサービス、接続、読取スレッドを終了します。

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
from jms_pam_config import client_options


with Client(instance_id="app-node-1", **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### イベントと認証情報の適用

初回・再接続の snapshot と credential.updated を処理します。例では subscription と alternating_rotation を分けています。apply_credential で接続を検証し、接続プールを切り替え、古い接続を解放してください。未実装の関数は例外を発生させ、未適用の認証情報の確認を防止します。

```python
from jms_pam import Client
from jms_pam_config import client_options


def apply_credential(credential):
    raise NotImplementedError('アプリケーションの認証情報切替を実装して検証してください')


with Client(instance_id="app-node-1", **client_options) as client:
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
            if mode == "subscription" and account_id:
                credential = client.get_credential(account_id=account_id)
            elif mode == "alternating_rotation" and key:
                credential = client.get_credential(key=key)
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

### アプリケーションコマンド

list_application_commands で保留中の要求を取得し、execute_application_command(event, handler) で実行権を申請します。accepted が true の場合だけ処理します。切替処理は要求されたアカウントとリビジョンを検証して適用・確認し、再起動処理はヘルスチェック後に成功を報告します。失敗の報告エラーは元の処理例外を隠しません。

### 主なメソッド

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

with または close で HTTP セッションとイベント接続を閉じ、clone で独立したセッションを作成します。HTTP、ネットワーク、認証、解析のエラーは code、status_code、detail、original_error を持つ PAMError になります。一時障害を再試行し、権限拒否を明示的に処理してください。

新規コードは snake_case のキーワードメソッドと dataclass 属性を使います。旧 credential.v1 API は DeprecationWarning とともに保持されます。SDK と Agent はバージョン 1 プロトコルを共有し、sync_agent はキャッシュと配信リビジョンを KnownRevision で指定します。

<!-- sdk-doc:end -->
