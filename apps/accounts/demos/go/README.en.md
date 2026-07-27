# Instructions

## 1. Introduction

This API retrieves account secrets for PAM assets, supports RESTful requests, and returns data in JSON format.

## 2. Environment Requirements

- `Go 1.16+`
- `crypto/hmac`
- `crypto/sha256`
- `encoding/base64`
- `net/http`

## 3. Usage

**Request Method**: `GET api/v1/accounts/integration-applications/account-secret/`

**Request Parameters**

| Parameter Name | Type | Required | Description       |
|----------------|------|----------|-------------------|
| asset          | str  | Yes      | Asset Name        |
| account        | str  | Yes      | Account Name      |

**Response Example**:
```json
{
    "id": "72b0b0aa-ad82-4182-a631-ae4865e8ae0e",
    "secret": "123456"
}
```

## Frequently Asked Questions (FAQ)

Q: How do I obtain an API key?

A: Create an application in PAM - Application Management to generate a KEY_ID and KEY_SECRET.

## Changelog


| Version | Changes                | Date       |
|---------|------------------------|------------|
| 1.0.0   | Initial version        | 2025-02-11 |
