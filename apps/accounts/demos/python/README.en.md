# Instructions

## 1. Introduction

This API provides the PAM asset account service, supports RESTful style calls, and returns data in JSON format.

## 2. Environment Requirements

- `Python 3.11+`
- `requests==2.31.0`
- `httpsig==1.3.0`

## 3. Usage
**Request Method**: `GET api/v1/accounts/integration-applications/account-secret/`

**Request Parameters**

| Parameter Name | Type | Required | Description       |
|----------------|------|----------|-------------------|
| asset          | str  | Yes      | Asset ID / Asset Name |
| account        | str  | Yes      | Account ID / Account Name |

**Response Example**:
```json
{
    "id": "72b0b0aa-ad82-4182-a631-ae4865e8ae0e", 
    "secret": "123456"
}
```

## Frequently Asked Questions (FAQ)

Q: How to obtain the API Key?

A: You can create an application in PAM - Application Management to generate KEY_ID and KEY_SECRET.

## Changelog


| Version | Changes                | Date       |
|---------|------------------------|------------|
| 1.0.0   | Initial version        | 2025-02-11 |
