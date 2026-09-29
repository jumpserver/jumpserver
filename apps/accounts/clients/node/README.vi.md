# JumpServer PAM Node.js SDK

SDK này theo chức năng của SDK chính sách thông tin xác thực Python: lấy theo tài khoản được phép hoặc chính sách luân phiên, xác nhận phiên bản áp dụng, theo dõi sự kiện, xử lý lệnh và đồng bộ Agent. URL, chữ ký HMAC, Digest, thời gian UTC, ID yêu cầu và tiêu đề được tạo tự động.

## Yêu cầu môi trường

- Node.js 20.3+ / ws
- `demo.js`

## Cấu hình và chạy

Cài SDK nguồn và cấu hình bên dưới. Cấp quyền tài khoản và gắn chính sách trong quản lý ứng dụng; lấy AK/SK và ID tổ chức từ tài liệu kết nối. Thay các giá trị mẫu và bảo vệ bí mật triển khai. Mỗi bản sao cần ID ổn định và duy nhất. Chỉ dùng một bộ chọn: ID tài khoản hoặc key chính sách.

```bash
cd apps/accounts/clients/node
export JMS_ENDPOINT='https://jumpserver.example.com'
export JMS_APP_ID='<app-id>'
export JMS_APP_SECRET='<app-secret>'
export JMS_ORG_ID='<org-id>'
export JMS_INSTANCE_ID='app-node-1'
export JMS_ACCOUNT_ID='<account-id>'

npm ci
node demo.js
```

Các SDK hiện được cài từ mã nguồn kho này và chưa được phát hành lên kho gói công khai. Thay /path/to/jumpserver bằng đường dẫn tuyệt đối. Chạy lệnh cài Go và Node.js trong thư mục ứng dụng hoặc thêm phụ thuộc Java vào pom.xml của ứng dụng. Thay lệnh nhập cục bộ trong ví dụ bằng lệnh nhập gói dưới đây.

```bash
npm install /path/to/jumpserver/apps/accounts/clients/node
```

```javascript
const { Client } = require('@jumpserver/pam')
// ESM: import { Client } from '@jumpserver/pam'
```

## Yêu cầu và phản hồi

```javascript
'use strict'

const { Client } = require('./index')

async function main() {
  const client = new Client({
    endpoint: process.env.JMS_ENDPOINT,
    appId: process.env.JMS_APP_ID,
    appSecret: process.env.JMS_APP_SECRET,
    instanceId: process.env.JMS_INSTANCE_ID,
    orgId: process.env.JMS_ORG_ID,
  })
  try {
    const credential = await client.getCredential({ accountId: process.env.JMS_ACCOUNT_ID })
    // Pass credential.account.username / secret to the application connection pool.
    console.log(
      `Fetched revision ${credential.revision}; implement application credential switching.`,
    )
  } finally {
    client.close()
  }
}

if (require.main === module)
  main().catch((error) => {
    console.error(error.code || error.name)
    process.exitCode = 1
  })
```

## Sự kiện và áp dụng thông tin xác thực

Xử lý snapshot đầu tiên/kết nối lại và credential.updated. Ví dụ đầy đủ xử lý subscription, alternating_rotation và lệnh. Triển khai kiểm tra kết nối thực, chuyển nhóm kết nối và giải phóng kết nối cũ. Hàm mẫu ném lỗi để ngăn xác nhận trước khi áp dụng. Xóa khỏi bộ nhớ đệm các tài khoản không còn trong snapshot và xử lý thu hồi.

```javascript
'use strict'
const { Client } = require('./index')

async function applyCredential(credential) {
  // Validate a real connection, switch the pool, then release old connections.
  throw new Error('Implement application credential switching')
}
async function restartApplication() {
  throw new Error('Implement application restart and health check')
}
async function handleCommand(client, event) {
  if (event.event === 'application.restart.requested') return restartApplication()
  if (event.event !== 'credential.switch.requested')
    throw new Error('Unsupported application command')
  const credential = await client.getCredential({ key: event.credentialKey })
  if (credential.revision !== event.revision || credential.account.id !== event.accountId)
    throw new Error('Requested account version is superseded')
  await applyCredential(credential)
  await client.confirmCredential({
    key: credential.key,
    revision: credential.revision,
    accountId: credential.account.id,
  })
}
async function main() {
  const client = new Client({
    endpoint: process.env.JMS_ENDPOINT,
    appId: process.env.JMS_APP_ID,
    appSecret: process.env.JMS_APP_SECRET,
    instanceId: process.env.JMS_INSTANCE_ID,
    orgId: process.env.JMS_ORG_ID,
  })
  const stop = () => client.close()
  process.once('SIGINT', stop)
  process.once('SIGTERM', stop)
  try {
    for await (const event of client.watchCredentialEvents()) {
      if (event.commandId) {
        try {
          await client.executeApplicationCommand(event, (command) => handleCommand(client, command))
        } catch {
          /* Failure is reported; keep secrets out of logs. */
        }
        continue
      }
      const updates =
        event.event === 'snapshot'
          ? event.credentials
          : event.event === 'credential.updated'
            ? [event]
            : []
      // On snapshots, remove application caches absent from the new authorized scope.
      for (const update of updates || []) {
        const mode = update.credentialMode
        const key = update.credentialKey || update.key
        let credential
        if (mode === 'subscription' && update.accountId)
          credential = await client.getCredential({ accountId: update.accountId })
        else if (mode === 'alternating_rotation' && key)
          credential = await client.getCredential({ key })
        else continue
        await applyCredential(credential)
        if (mode === 'alternating_rotation')
          await client.confirmCredential({
            key: credential.key,
            revision: credential.revision,
            accountId: credential.account.id,
          })
      }
    }
  } finally {
    client.close()
    process.removeListener('SIGINT', stop)
    process.removeListener('SIGTERM', stop)
  }
}
if (require.main === module)
  main().catch((error) => {
    console.error(error.code || error.name)
    process.exitCode = 1
  })
```

Với luân phiên hai tài khoản, xác minh kết nối thật, chuyển nhóm kết nối và giải phóng kết nối cũ trước khi xác nhận đúng key, revision và account_id. Đăng ký thay đổi thông tin xác thực không cần xác nhận. Không xác nhận khi kiểm tra kết nối thất bại.

## Lệnh ứng dụng

Thăm dò, nhận quyền thực thi và báo cáo kết quả dùng phương thức SDK. Chỉ nhận quyền thành công mới chạy hàm xử lý. Chuyển đổi kiểm tra phiên bản và tài khoản, áp dụng rồi xác nhận; khởi động lại phải kiểm tra tình trạng sau khởi động. Chỉ báo thành công khi hoàn tất. Lỗi báo cáo không thay thế lỗi nghiệp vụ gốc.

## Phương thức thông dụng

- `getCredential({key})`
- `getCredential({accountId})`
- `confirmCredential({key, revision, accountId})`
- `watchCredentialEvents({signal})`
- `listApplicationCommands()`
- `reportApplicationCommandResult({commandId, status, errorCode})`
- `executeApplicationCommand(event, handler)`
- `syncAgent({credentials, deliveredCredentials, ...})`
- `clone() / close()`

## Khắc phục sự cố

Lỗi HTTP, mạng, xác thực và giải mã dùng kiểu lỗi SDK với mã và trạng thái HTTP. Đóng luồng và máy khách sau khi dùng; bản sao có vòng đời độc lập. Thử lại lỗi tạm thời ở tầng ứng dụng và không ghi bí mật hay tiêu đề xác thực vào nhật ký.

`PAMError`

Mọi SDK dùng giao thức phiên bản 1; Agent dùng lược đồ cấu hình phiên bản 1. Khi nhận client_upgrade_required (HTTP 426), kiểm tra tương thích và nâng cấp. Cho phép trường tùy chọn và thông báo chưa biết; không áp dụng hay xác nhận chính sách chưa hỗ trợ. Biên nhận được gửi tự động và không chứng minh đã áp dụng thông tin xác thực.

## Tích hợp Linux Agent

Đồng bộ phục vụ triển khai Agent. Cần danh tính hoặc source Agent và ID cấu hình, dùng KnownRevision cho phiên bản đệm và đã chuyển giao. Cài đặt Linux, chuyển giao tệp và API cục bộ hiện do Python Agent cung cấp, ứng dụng mọi ngôn ngữ đều có thể dùng.
