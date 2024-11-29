# JumpServer PAM Client

This package provides a Python client for interacting with the JumpServer PAM API to retrieve secrets for various assets. It simplifies the process of sending requests and handling responses.

## Features

- Validate parameters before sending requests.
- Support for both asset and account-based secret retrieval.
- Easy integration with JumpServer PAM API using HTTP signatures for authentication.

## Installation

You can install the package via pip:

```bash
pip install jms_pam-0.0.1-py3-none-any.whl
```

## Requirements

- `Python 3.6+`
- `requests`
- `httpsig`

## Usage

### Initialization

To use the JumpServer PAM client, create an instance by providing the required `endpoint`, `key_id`, and `key_secret`.

```python
from jms_pam import JumpServerPAM, SecretRequest

client = JumpServerPAM(
    endpoint='http://127.0.0.1',
    key_id='your-key-id',
    key_secret='your-key-secret'
)
```

### Creating a Secret Request

You can create a request for a secret by specifying the asset or account information.

```python
request = SecretRequest(asset='Linux', account='root')
```

### Sending the Request

Send the request using the `send` method of the client.

```python
secret_obj = client.send(request)
```

### Handling the Response

Check if the secret was retrieved successfully and handle the response accordingly.

```python
if secret_obj.valid:
    print('Secret: %s' % secret_obj.secret)
else:
    print('Get secret failed: %s' % secret_obj.desc)
```

### Complete Example

Here’s a complete example of how to use the client:

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
    print('Secret: %s' % secret_obj.secret)
else:
    print('Get secret failed: %s' % secret_obj.desc)
```

## Error Handling

The library raises `RequestParamsError` if the parameters provided do not meet the validation requirements. This includes checks for valid UUIDs and interdependencies between parameters.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.
