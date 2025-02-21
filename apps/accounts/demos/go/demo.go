package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

type APIClient struct {
	Client    *http.Client
	APIURL    string
	KeyID     string
	KeySecret string
	OrgID     string
}

func NewAPIClient() *APIClient {
	return &APIClient{
		Client:    &http.Client{},
		APIURL:    getEnv("API_URL", "http://127.0.0.1:8080"),
		KeyID:     getEnv("API_KEY_ID", "72b0b0aa-ad82-4182-a631-ae4865e8ae0e"),
		KeySecret: getEnv("API_KEY_SECRET", "6fuSO7P1m4cj8SSlgaYdblOjNAmnxDVD7tr8"),
		OrgID:     getEnv("ORG_ID", "00000000-0000-0000-0000-000000000002"),
	}
}

func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

func (c *APIClient) GetAccountSecret(asset, account string) (map[string]interface{}, error) {
	u, err := url.Parse(c.APIURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse API URL: %v", err)
	}
	u.Path = "/api/v1/accounts/integration-applications/account-secret/"

	q := u.Query()
	q.Add("asset", asset)
	q.Add("account", account)
	u.RawQuery = q.Encode()

	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %v", err)
	}

	date := time.Now().UTC().Format("Mon, 02 Jan 2006 15:04:05 GMT")
	req.Header.Set("Accept", "application/json")
	req.Header.Set("X-JMS-ORG", c.OrgID)
	req.Header.Set("Date", date)
	req.Header.Set("X-Source", "jms-pam")

	headersList := []string{"(request-target)", "accept", "date", "x-jms-org"}
	var signatureParts []string

	for _, h := range headersList {
		var value string
		if h == "(request-target)" {
			value = strings.ToLower(req.Method) + " " + req.URL.RequestURI()
		} else {
			canonicalKey := http.CanonicalHeaderKey(h)
			value = req.Header.Get(canonicalKey)
		}
		signatureParts = append(signatureParts, fmt.Sprintf("%s: %s", h, value))
	}

	signatureString := strings.Join(signatureParts, "\n")
	mac := hmac.New(sha256.New, []byte(c.KeySecret))
	mac.Write([]byte(signatureString))
	signatureB64 := base64.StdEncoding.EncodeToString(mac.Sum(nil))

	headersJoined := strings.Join(headersList, " ")
	authHeader := fmt.Sprintf(
		`Signature keyId="%s",algorithm="hmac-sha256",headers="%s",signature="%s"`,
		c.KeyID,
		headersJoined,
		signatureB64,
	)
	req.Header.Set("Authorization", authHeader)

	resp, err := c.Client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API returned non-200 status: %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %v", err)
	}

	return result, nil
}

func main() {
	client := NewAPIClient()
	result, err := client.GetAccountSecret("ubuntu_docker", "root")
	if err != nil {
		log.Fatalf("Error: %v", err)
	}
	fmt.Printf("Result: %+v\n", result)
}
