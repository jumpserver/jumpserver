package pam

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"net/http"
	"strings"
	"time"
)

const Version = "1.0.0"
const ProtocolVersion = 1
const ConfigSchemaVersion = 1
const clientPath = "/api/v1/accounts/credential-client"

var signatureHeaders = []string{"(request-target)", "accept", "date", "digest", "x-jms-request-id", "x-jms-org", "x-jms-client-version", "x-jms-protocol-version", "x-jms-config-schema-version"}

func (c *Client) sign(request *http.Request, body []byte) error {
	id := make([]byte, 16)
	if _, err := rand.Read(id); err != nil {
		return err
	}
	id[6] = (id[6] & 0x0f) | 0x40
	id[8] = (id[8] & 0x3f) | 0x80
	request.Header.Set("Accept", "application/json")
	request.Header.Set("Date", time.Now().UTC().Format(http.TimeFormat))
	digest := sha256.Sum256(body)
	request.Header.Set("Digest", "SHA-256="+base64.StdEncoding.EncodeToString(digest[:]))
	request.Header.Set("X-JMS-Request-ID", fmt.Sprintf("%x-%x-%x-%x-%x", id[:4], id[4:6], id[6:8], id[8:10], id[10:]))
	request.Header.Set("X-JMS-ORG", c.options.OrgID)
	request.Header.Set("X-Source", c.options.Source)
	request.Header.Set("X-JMS-Client-Version", Version)
	request.Header.Set("X-JMS-Protocol-Version", "1")
	schema := "0"
	if c.options.Source == "jms-pam-agent" {
		schema = "1"
	}
	request.Header.Set("X-JMS-Config-Schema-Version", schema)
	parts := make([]string, 0, len(signatureHeaders))
	for _, name := range signatureHeaders {
		value := request.Header.Get(name)
		if name == "(request-target)" {
			value = strings.ToLower(request.Method) + " " + request.URL.RequestURI()
		}
		parts = append(parts, name+": "+value)
	}
	mac := hmac.New(sha256.New, []byte(c.options.AppSecret))
	mac.Write([]byte(strings.Join(parts, "\n")))
	request.Header.Set("Authorization", fmt.Sprintf(`Signature keyId="%s",algorithm="hmac-sha256",signature="%s",headers="%s"`, c.options.AppID, base64.StdEncoding.EncodeToString(mac.Sum(nil)), strings.Join(signatureHeaders, " ")))
	return nil
}
