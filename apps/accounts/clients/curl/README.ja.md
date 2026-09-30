# cURL — 利用ガイド

このディレクトリは旧 account-secret API の診断用 HTTP 署名スクリプトです。アプリケーションの連携には Python、Go、Java、Node.js の SDK を使用してください。

## 動作要件

- Bash / cURL / OpenSSL / base64
- `demo.sh`

Bash、cURL、OpenSSL、base64 が必要です。ASSET と ACCOUNT を変更し、署名対象のクエリが cURL の送信時と同じ形式でエンコードされていることを確認してください。

## 設定と実行

アプリケーション管理でアプリケーションを作成し、対象の資産アカウントを許可します。以下のエンドポイント、アプリケーション AK/SK、組織 ID を設定し、実行前にすべてのプレースホルダーを実際の値に変更してください。

```bash
cd apps/accounts/clients/curl
export API_URL='https://jumpserver.example.com'
export API_KEY_ID='<app-id>'
export API_KEY_SECRET='<app-secret>'
export ORG_ID='<org-id>'

bash demo.sh
```

既定の資産は ubuntu_docker、アカウントは root です。コード内で許可された実際の名前に変更してください。コマンドはリポジトリのルートから実行します。出力に秘密情報が含まれるため、アプリケーションログに記録しないでください。

## リクエストとレスポンス

```http
GET /api/v1/accounts/integration-applications/account-secret/?asset=ubuntu_docker&account=root
```

```json
{"id":"<app-id>","secret":"<account-secret>"}
```

id はアプリケーションの識別子で、アカウントのリビジョンではありません。secret が null の場合は、サーバーの秘密情報表示設定による制限が考えられます。このサンプルは認証情報イベント、生効リビジョンの報告、アプリケーションコマンドには対応していません。

## トラブルシューティング

401 では AK/SK、組織、ホスト時刻、署名 URL を確認します。403 ではアプリケーションの状態とアカウント権限、400 では資産・アカウントの指定と URL エンコードを確認してください。秘密情報と Authorization ヘッダーをログに記録しないでください。

## 認証情報ポリシーへの接続

以下の署名とプロトコル表は診断用の参考資料です。認証情報ポリシーは SDK メソッドで扱うか、Go jms-pam-agent の JSON ファイル、EnvironmentFile、Unix Socket を使用してください。

| HTTP | API | JSON / query |
| --- | --- | --- |
| GET | `/api/v1/accounts/credential-client/credential/` | `instance_id`, `key` / `account_id` |
| POST | `/api/v1/accounts/credential-client/confirm/` | `instance_id`, `key`, `revision`, `account_id` |
| GET | `/api/v1/accounts/credential-client/commands/` | `instance_id` |
| POST | `/api/v1/accounts/credential-client/command-result/` | `instance_id`, `command_id`, `status`, `error_code` |
| WebSocket | `/ws/accounts/credential-events/` | `instance_id` |

以下のヘッダー順で HMAC-SHA256 署名を計算します。request-target にエンコード済みパスとクエリ、Digest に実際の本文の SHA-256、X-JMS-Request-ID に一意の UUID、Date に HTTP UTC 時刻を設定します。X-JMS-Client-Version、X-JMS-Protocol-Version: 1、SDK 用 X-JMS-Config-Schema-Version: 0 も必要です。API と WebSocket ではアプリケーション AK/SK と安定した一意の instance_id を使い、各リクエストと再接続で署名を再生成します。

```text
(request-target) accept date digest x-jms-request-id x-jms-org
x-jms-client-version x-jms-protocol-version x-jms-config-schema-version
```

交互ローテーションでは実際の接続を検証し、接続プールを切り替えて古い接続を解放した後に、正確な key、revision、account_id を確認します。認証情報変更の購読では確認は不要です。接続検証に失敗した場合は確認してはいけません。

received はイベントを読み取ったことだけを示します。event_id を持つ業務イベントの処理前に、同じ WebSocket で received を送信します。snapshot と pong は受領通知不要です。接続・再接続のたびに快照を同期し、credential.updated、権限取消、設定変更を処理します。
