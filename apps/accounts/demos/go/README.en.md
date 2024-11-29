# JumpServer PAM Client

This package provides a Go client for interacting with the JumpServer PAM API to retrieve secrets for various assets. It simplifies the process of sending requests and handling responses.

## Features

- Validate parameters before sending requests.
- Support for both asset and account-based secret retrieval.
- Easy integration with JumpServer PAM API using HMAC-SHA256 signatures for authentication.

## Usage Instructions

1. **Download Go Code Files**:
   Download the code files into your project directory.

2. **Import the Package**:
   Import the package in your Go file, and you can directly use its functionalities.

## Requirements

- `Go 1.16+`
- `github.com/google/uuid`
- `gopkg.in/twindagger/httpsig.v1`

## Usage

### Initialization

To use the JumpServer PAM client, create an instance by providing the required `endpoint`, `keyID`, and `keySecret`.

```go
package main

import (
	"fmt"
	
	"your_module_path/jms_pam" 
)

func main() {
	client := jms_pam.NewJumpServerPAM(
		"http://127.0.0.1", // Replace with your JumpServer endpoint
		"your-key-id",      // Replace with your actual Key ID
		"your-key-secret",  // Replace with your actual Key Secret
		"",                 // Leave empty for default organization ID
	)
}
```

### Creating a Secret Request

You can create a request for a secret by specifying the asset or account information.

```go
request, err := jms_pam.NewSecretRequest("Linux", "", "root", "")
if err != nil {
    fmt.Println("Error creating request:", err)
    return
}
```

### Sending the Request

Send the request using the `Send` method of the client.

```go
secretObj, err := client.Send(request)
if err != nil {
    fmt.Println("Error sending request:", err)
    return
}
```

### Handling the Response

Check if the secret was retrieved successfully and handle the response accordingly.

```go
if secretObj.Valid {
    fmt.Println("Secret:", secretObj.Secret)
} else {
    fmt.Println("Get secret failed:", string(secretObj.Desc))
}
```

### Complete Example

Here’s a complete example of how to use the client:

```go
package main

import (
	"fmt"
	
	"your_module_path/jms_pam"
)

func main() {
	client := jms_pam.NewJumpServerPAM(
		"http://127.0.0.1",
		"your-key-id",
		"your-key-secret",
		"",
	)

	request, err := jms_pam.NewSecretRequest("Linux", "", "root", "")
	if err != nil {
		fmt.Println("Error creating request:", err)
		return
	}

	secretObj, err := client.Send(request)
	if err != nil {
		fmt.Println("Error sending request:", err)
		return
	}

	if secretObj.Valid {
		fmt.Println("Secret:", secretObj.Secret)
	} else {
		fmt.Println("Get secret failed:", string(secretObj.Desc))
	}
}
```

## Error Handling

The library returns errors for invalid parameters when creating a `SecretRequest`. This includes checks for valid UUIDs and ensuring that required parameters are provided.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.
