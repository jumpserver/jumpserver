package pam

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

// Options identify a stable application replica. Timeout applies to HTTP calls and WS handshakes.
type Options struct {
	Endpoint   string
	AppID      string
	AppSecret  string
	InstanceID string
	OrgID      string
	Timeout    time.Duration
	Source     string
}
type Client struct {
	options              Options
	http                 *http.Client
	mu                   sync.Mutex
	closed               bool
	stop                 context.Context
	cancel               context.CancelFunc
	watcher              *EventWatcher
	latestCredentials    map[CredentialSelector]Credential
	credentialGeneration uint64
}

func NewClient(options Options) (*Client, error) {
	endpoint, err := url.Parse(options.Endpoint)
	if err != nil || endpoint == nil || (endpoint.Scheme != "https" && endpoint.Scheme != "http") || endpoint.Host == "" || endpoint.User != nil || endpoint.RawQuery != "" || endpoint.Fragment != "" {
		return nil, fmt.Errorf("endpoint must be an HTTP(S) URL without credentials, query or fragment")
	}
	if options.AppID == "" || options.AppSecret == "" || options.InstanceID == "" || strings.TrimSpace(options.InstanceID) != options.InstanceID || len(options.InstanceID) > 128 {
		return nil, fmt.Errorf("app identity and a stable instance ID are required")
	}
	if options.Timeout == 0 {
		options.Timeout = 10 * time.Second
	}
	if options.Timeout < 0 {
		return nil, fmt.Errorf("timeout must be positive")
	}
	if options.OrgID == "" {
		options.OrgID = "00000000-0000-0000-0000-000000000002"
	}
	if options.Source == "" {
		options.Source = "jms-pam"
	}
	options.Endpoint = strings.TrimRight(options.Endpoint, "/")
	stop, cancel := context.WithCancel(context.Background())
	transport := http.DefaultTransport.(*http.Transport).Clone()
	return &Client{options: options, stop: stop, cancel: cancel, latestCredentials: make(map[CredentialSelector]Credential), http: &http.Client{Transport: transport, Timeout: options.Timeout, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}}, nil
}
func (c *Client) Clone() (*Client, error) { return NewClient(c.options) }
func (c *Client) Close() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if !c.closed {
		c.closed = true
		c.cancel()
		c.http.CloseIdleConnections()
		clear(c.latestCredentials)
		c.credentialGeneration++
	}
	return nil
}
func (c *Client) request(ctx context.Context, method, path string, data map[string]any, target any, validate func(map[string]json.RawMessage) error) error {
	c.mu.Lock()
	closed := c.closed
	c.mu.Unlock()
	if closed {
		return errors.New("client is closed")
	}
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	release := context.AfterFunc(c.stop, cancel)
	defer release()
	data["instance_id"] = c.options.InstanceID
	endpoint, err := url.Parse(c.options.Endpoint + clientPath + path)
	if err != nil {
		return err
	}
	var body []byte
	if method == http.MethodGet {
		params := endpoint.Query()
		for name, value := range data {
			params.Set(name, fmt.Sprint(value))
		}
		endpoint.RawQuery = params.Encode()
	} else {
		body, err = json.Marshal(data)
		if err != nil {
			return err
		}
	}
	request, err := http.NewRequestWithContext(ctx, method, endpoint.String(), bytes.NewReader(body))
	if err != nil {
		return err
	}
	if body != nil {
		request.Header.Set("Content-Type", "application/json")
	}
	if err = c.sign(request, body); err != nil {
		return err
	}
	response, err := c.http.Do(request)
	if err != nil {
		return &PAMError{Code: "NetworkError", Detail: "HTTP request failed", Err: err}
	}
	defer response.Body.Close()
	if response.StatusCode == 401 || response.StatusCode == 403 || response.StatusCode == 404 || response.StatusCode == 426 {
		c.mu.Lock()
		clear(c.latestCredentials)
		c.credentialGeneration++
		c.mu.Unlock()
	}
	raw, err := io.ReadAll(io.LimitReader(response.Body, 16*1024*1024+1))
	if err != nil {
		return &PAMError{Code: "NetworkError", StatusCode: response.StatusCode, Detail: "HTTP response failed", Err: err}
	}
	payload, err := object(raw)
	if err != nil {
		return &PAMError{Code: "ResponseError", StatusCode: response.StatusCode, Detail: "The server returned invalid JSON", Err: err}
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		code, detail, requestID := "HTTPError", "HTTP request failed", ""
		var value string
		if json.Unmarshal(payload["code"], &value) == nil && value != "" {
			code = value
		}
		value = ""
		if json.Unmarshal(payload["detail"], &value) == nil && value != "" {
			detail = value
		}
		json.Unmarshal(payload["request_id"], &requestID)
		if response.StatusCode == 400 && code == "credential_not_found" {
			c.mu.Lock()
			clear(c.latestCredentials)
			c.credentialGeneration++
			c.mu.Unlock()
		}
		return &PAMError{Code: code, StatusCode: response.StatusCode, Detail: detail, RequestID: requestID}
	}
	if validate != nil {
		err = validate(payload)
	}
	if err == nil {
		err = json.Unmarshal(raw, target)
	}
	if err != nil {
		return &PAMError{Code: "ResponseError", StatusCode: response.StatusCode, Detail: "The server returned an invalid response", Err: err}
	}
	return nil
}
func (c *Client) GetCredential(ctx context.Context, selector CredentialSelector) (Credential, error) {
	return c.getCredential(ctx, selector, true)
}

func (c *Client) ListAuthorizedAccounts(ctx context.Context) ([]AuthorizedAccount, error) {
	accounts := []AuthorizedAccount{}
	seen := map[string]bool{}
	for {
		page, count, err := c.ListAuthorizedAccountsPage(ctx, 200, len(accounts), "")
		if err != nil {
			return nil, err
		}
		if len(page) == 0 && len(accounts) < count {
			return nil, &PAMError{Code: "ResponseError", Detail: "Incomplete account list"}
		}
		for _, account := range page {
			if seen[account.ID] {
				return nil, &PAMError{Code: "ResponseError", Detail: "Duplicate account in paginated list"}
			}
			seen[account.ID] = true
			accounts = append(accounts, account)
		}
		if len(accounts) >= count {
			return accounts, nil
		}
	}
}

func (c *Client) ListAuthorizedAccountsPage(ctx context.Context, limit, offset int, search string) ([]AuthorizedAccount, int, error) {
	if limit < 1 || limit > 500 || offset < 0 {
		return nil, 0, fmt.Errorf("invalid account page")
	}
	var value struct {
		Count    int                 `json:"count"`
		Accounts []AuthorizedAccount `json:"accounts"`
	}
	err := c.request(ctx, http.MethodGet, "/accounts/", map[string]any{"limit": limit, "offset": offset, "search": search}, &value, func(data map[string]json.RawMessage) error {
		if err := required(data, "count", "accounts"); err != nil {
			return err
		}
		var count int
		if err := json.Unmarshal(data["count"], &count); err != nil || count < 0 {
			return fmt.Errorf("invalid account count")
		}
		var accounts []AuthorizedAccount
		if err := json.Unmarshal(data["accounts"], &accounts); err != nil || accounts == nil {
			return fmt.Errorf("invalid accounts metadata")
		}
		seen := map[string]bool{}
		for _, account := range accounts {
			if account.ID == "" || account.Asset.ID == "" || seen[account.ID] {
				return fmt.Errorf("invalid authorized account")
			}
			seen[account.ID] = true
			for _, policy := range account.Credentials {
				if policy.Key == "" || policy.Revision < 0 || (policy.Mode != "subscription" && policy.Mode != "alternating_rotation") {
					return fmt.Errorf("invalid account policy")
				}
			}
		}
		return nil
	})
	return value.Accounts, value.Count, err
}

// GetCredentialFresh requires a live backend response; use it for business switches.
func (c *Client) GetCredentialFresh(ctx context.Context, selector CredentialSelector) (Credential, error) {
	return c.getCredential(ctx, selector, false)
}

func (c *Client) getCredential(ctx context.Context, selector CredentialSelector, allowLocalFallback bool) (Credential, error) {
	if (selector.Key == "") == (selector.AccountID == "") {
		return Credential{}, fmt.Errorf("exactly one of Key or AccountID is required")
	}
	data := map[string]any{}
	if selector.Key != "" {
		data["key"] = selector.Key
	} else {
		data["account_id"] = selector.AccountID
	}
	var value Credential
	c.mu.Lock()
	generation := c.credentialGeneration
	c.mu.Unlock()
	err := c.request(ctx, http.MethodGet, "/credential/", data, &value, validCredential)
	c.mu.Lock()
	defer c.mu.Unlock()
	if err == nil {
		if !c.closed && generation == c.credentialGeneration {
			if latest, found := c.latestCredentials[selector]; found && value.Revision < latest.Revision {
				return Credential{}, &PAMError{Code: "ResponseError", StatusCode: 200, Detail: "Credential revision moved backwards"}
			}
			c.latestCredentials[selector] = value
		}
		return value, nil
	}
	var failure *PAMError
	if errors.As(err, &failure) {
		denied := failure.StatusCode == 401 || failure.StatusCode == 403 || failure.StatusCode == 404 || failure.Code == "client_upgrade_required" || (failure.StatusCode == 400 && failure.Code == "credential_not_found")
		if denied {
			clear(c.latestCredentials)
			c.credentialGeneration++
		}
		temporary := failure.Code == "NetworkError" || (failure.StatusCode >= 500 && failure.StatusCode < 600)
		latest, found := c.latestCredentials[selector]
		if allowLocalFallback && selector.Key != "" && temporary && !denied && !c.closed && ctx.Err() == nil && found {
			value = latest
			value.FromLocal = true
			return value, nil
		}
	}
	return value, err
}
func (c *Client) ConfirmCredential(ctx context.Context, key string, revision int64, accountID string) (CredentialConfirmation, error) {
	if key == "" || accountID == "" || revision < 1 {
		return CredentialConfirmation{}, fmt.Errorf("key, account ID and a positive revision are required")
	}
	var value CredentialConfirmation
	err := c.request(ctx, http.MethodPost, "/confirm/", map[string]any{"key": key, "revision": revision, "account_id": accountID}, &value, func(data map[string]json.RawMessage) error { return required(data, "key", "revision") })
	if err == nil && value.Revision < 0 {
		err = &PAMError{Code: "ResponseError", Detail: "Invalid revision"}
	}
	return value, err
}
func (c *Client) SyncAgent(ctx context.Context, options AgentSyncOptions) (AgentSync, error) {
	for _, items := range [][]KnownRevision{options.Credentials, options.DeliveredCredentials} {
		for _, item := range items {
			if item.Key == "" || item.Revision < 0 {
				return AgentSync{}, fmt.Errorf("invalid known revision")
			}
		}
	}
	if options.Credentials == nil {
		options.Credentials = []KnownRevision{}
	}
	if options.DeliveredCredentials == nil {
		options.DeliveredCredentials = []KnownRevision{}
	}
	var value AgentSync
	err := c.request(ctx, http.MethodPost, "/agent/sync/", map[string]any{"credentials": options.Credentials, "delivered_credentials": options.DeliveredCredentials, "delivery_scope": options.DeliveryScope, "config_digest": options.ConfigDigest, "sync_status": options.SyncStatus, "sync_error": options.SyncError, "restart_supported": options.RestartSupported}, &value, func(data map[string]json.RawMessage) error {
		if err := required(data, "config_digest", "credentials", "removed_keys", "date_last_synced"); err != nil {
			return err
		}
		var items []map[string]json.RawMessage
		if err := json.Unmarshal(data["credentials"], &items); err != nil {
			return err
		}
		seen := map[string]bool{}
		for _, item := range items {
			if err := required(item, "key", "revision", "available", "changed"); err != nil {
				return err
			}
			var revision CredentialRevision
			raw, _ := json.Marshal(item)
			if err := json.Unmarshal(raw, &revision); err != nil {
				return err
			}
			if revision.Revision < 0 || seen[revision.Key] {
				return fmt.Errorf("invalid revision metadata")
			}
			seen[revision.Key] = true
		}
		var keys []string
		if err := json.Unmarshal(data["removed_keys"], &keys); err != nil {
			return err
		}
		for _, key := range keys {
			if key == "" {
				return fmt.Errorf("invalid removed key")
			}
		}
		return nil
	})
	return value, err
}
func (c *Client) ListApplicationCommands(ctx context.Context) ([]Event, error) {
	var value struct {
		Commands []Event `json:"commands"`
	}
	err := c.request(ctx, http.MethodGet, "/commands/", map[string]any{}, &value, func(data map[string]json.RawMessage) error {
		if err := required(data, "commands"); err != nil {
			return err
		}
		var items []map[string]json.RawMessage
		if err := json.Unmarshal(data["commands"], &items); err != nil {
			return err
		}
		for _, item := range items {
			if item == nil {
				return fmt.Errorf("commands must contain objects")
			}
		}
		return nil
	})
	return value.Commands, err
}
func (c *Client) ReportApplicationCommandResult(ctx context.Context, commandID, status, errorCode string) (CommandResult, error) {
	if commandID == "" || (status != "running" && status != "success" && status != "failed") {
		return CommandResult{}, fmt.Errorf("command ID and a valid status are required")
	}
	data := map[string]any{"command_id": commandID, "status": status}
	if errorCode != "" {
		data["error_code"] = errorCode
	}
	var value CommandResult
	err := c.request(ctx, http.MethodPost, "/command-result/", data, &value, func(data map[string]json.RawMessage) error { return required(data, "accepted", "status") })
	return value, err
}
func (c *Client) ExecuteApplicationCommand(ctx context.Context, event Event, handler CommandHandler) (CommandResult, error) {
	if handler == nil {
		return CommandResult{}, fmt.Errorf("handler is required")
	}
	claim, err := c.ReportApplicationCommandResult(ctx, event.CommandID, "running", "")
	if err != nil || !claim.Accepted {
		return claim, err
	}
	if err = handler(event); err != nil {
		c.ReportApplicationCommandResult(ctx, event.CommandID, "failed", "execution_failed")
		return CommandResult{}, err
	}
	return c.ReportApplicationCommandResult(ctx, event.CommandID, "success", "")
}
