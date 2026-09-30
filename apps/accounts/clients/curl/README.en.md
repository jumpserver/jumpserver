# cURL — Usage guide

This directory contains a signed HTTP script for diagnosing the legacy account-secret API. For application integration, use the Python, Go, Java or Node.js SDK.

## Requirements

- Bash / cURL / OpenSSL / base64
- `demo.sh`

The script requires Bash, cURL, OpenSSL and base64. Replace ASSET and ACCOUNT in the script, and ensure the signed query is encoded exactly as sent by cURL.

## Configure and run

Create an application in Application Management and authorize the target asset accounts. Set the endpoint, application AK/SK and organization ID below; replace every placeholder with its actual value before running.

```bash
cd apps/accounts/clients/curl
export API_URL='https://jumpserver.example.com'
export API_KEY_ID='<app-id>'
export API_KEY_SECRET='<app-secret>'
export ORG_ID='<org-id>'

bash demo.sh
```

The examples query asset ubuntu_docker and account root by default. Replace them in the example with real authorized names. Run commands from the repository root. Example output contains secrets; do not send it to application logs.

## Request and response

```http
GET /api/v1/accounts/integration-applications/account-secret/?asset=ubuntu_docker&account=root
```

```json
{"id":"<app-id>","secret":"<account-secret>"}
```

The response id identifies the application, not an account revision. A null secret can reflect the server secret-view setting. These examples do not receive credential events, report applied revisions or execute application commands.

## Troubleshooting

For 401, check AK/SK, organization, host time and the signed URL. For 403, check application status and account authorization. For 400, check asset/account selectors and query encoding. Do not log secrets or Authorization headers. Account names and asset names must match the application’s authorized resources.

## Credential policy access

The signature details and protocol table below are diagnostic references. Use SDK methods for credential policies, or use the Go jms-pam-agent through JSON files, EnvironmentFile or Unix Socket.

| HTTP | API | JSON / query |
| --- | --- | --- |
| GET | `/api/v1/accounts/credential-client/credential/` | `instance_id`, `key` / `account_id` |
| POST | `/api/v1/accounts/credential-client/confirm/` | `instance_id`, `key`, `revision`, `account_id` |
| GET | `/api/v1/accounts/credential-client/commands/` | `instance_id` |
| POST | `/api/v1/accounts/credential-client/command-result/` | `instance_id`, `command_id`, `status`, `error_code` |
| WebSocket | `/ws/accounts/credential-events/` | `instance_id` |

Sign requests with HMAC-SHA256 in the header order below. Include the encoded path and query in request-target, SHA-256 of the exact body in Digest, a unique UUID in X-JMS-Request-ID, an HTTP UTC Date, X-JMS-Client-Version, X-JMS-Protocol-Version: 1 and X-JMS-Config-Schema-Version: 0 for SDKs. API and WebSocket use the application AK/SK and a stable, unique instance_id; refresh the signature for each request or reconnect.

```text
(request-target) accept date digest x-jms-request-id x-jms-org
x-jms-client-version x-jms-protocol-version x-jms-config-schema-version
```

For alternating rotation, validate a real connection, switch the application connection pool and release old connections before confirming the exact key, revision and account_id. Credential change subscriptions require no confirmation. A failed connection check must prevent confirmation.

A received receipt only means an event was read. Send received with event_id on the same WebSocket before handling business events; snapshot and pong require no receipt. Reconcile the snapshot on every connection and reconnect, process credential.updated, and handle revocation or configuration changes.
