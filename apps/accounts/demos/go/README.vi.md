# Hướng dẫn

## 1. Giới thiệu

API này truy xuất mật khẩu tài khoản trên tài sản PAM, hỗ trợ các yêu cầu RESTful và trả về dữ liệu ở định dạng JSON.

## 2. Yêu cầu môi trường

- `Go 1.16+`
- `crypto/hmac`
- `crypto/sha256`
- `encoding/base64`
- `net/http`

## 3. Cách sử dụng

**Phương thức yêu cầu**: `GET api/v1/accounts/integration-applications/account-secret/`

**Tham số yêu cầu**

| Tên tham số | Kiểu | Bắt buộc | Mô tả |
|-------------|------|----------|-------|
| asset       | str  | Có       | Tên tài sản |
| account     | str  | Có       | Tên tài khoản |

**Ví dụ phản hồi**:
```json
{
    "id": "72b0b0aa-ad82-4182-a631-ae4865e8ae0e",
    "secret": "123456"
}
```

## Câu hỏi thường gặp (FAQ)

Hỏi: Làm cách nào để lấy API Key?

Đáp: Tạo một ứng dụng trong PAM - Quản lý ứng dụng để nhận KEY_ID và KEY_SECRET.

## Lịch sử thay đổi

| Phiên bản | Thay đổi       | Ngày       |
|-----------|----------------|------------|
| 1.0.0     | Phiên bản đầu tiên | 2025-02-11 |
