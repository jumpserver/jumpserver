// Package pam provides the JumpServer credential policy SDK.
package pam

import (
	"encoding/json"
	"fmt"
)

type Platform struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Category string `json:"category"`
	Type     string `json:"type"`
}
type Asset struct {
	ID       string   `json:"id"`
	Name     string   `json:"name"`
	Address  string   `json:"address"`
	Platform Platform `json:"platform"`
}
type Account struct {
	ID         string `json:"id"`
	Name       string `json:"name"`
	Username   string `json:"username"`
	SecretType string `json:"secret_type"`
	Secret     string `json:"secret"`
}

type AccountSwitch struct {
	AccountIDs []string `json:"account_ids"`
}

func (a Account) String() string {
	return fmt.Sprintf("Account{ID:%q Username:%q Secret:[REDACTED]}", a.ID, a.Username)
}
func (a Account) GoString() string { return a.String() }

type Credential struct {
	Key           string         `json:"key"`
	Revision      int64          `json:"revision"`
	Asset         Asset          `json:"asset"`
	Account       Account        `json:"account"`
	AccountSwitch *AccountSwitch `json:"account_switch,omitempty"`
	FromLocal     bool           `json:"-"`
}

func (c Credential) String() string {
	return fmt.Sprintf("Credential{Key:%q Revision:%d Account:%s}", c.Key, c.Revision, c.Account)
}
func (c Credential) GoString() string { return c.String() }

type CredentialSelector struct {
	Key       string
	AccountID string
}

// AuthorizedAccount contains metadata for an application's pull scope.
// Credentials lists push policies, and may be empty for pull-only accounts.
type AuthorizedAccount struct {
	ID          string          `json:"id"`
	Name        string          `json:"name"`
	Username    string          `json:"username"`
	SecretType  string          `json:"secret_type"`
	Asset       Asset           `json:"asset"`
	Credentials []AccountPolicy `json:"credentials"`
}

type AccountPolicy struct {
	Key           string         `json:"key"`
	Mode          string         `json:"mode"`
	Revision      int64          `json:"revision"`
	AccountSwitch *AccountSwitch `json:"account_switch,omitempty"`
}
type CredentialConfirmation struct {
	Key      string `json:"key"`
	Revision int64  `json:"revision"`
}
type KnownRevision struct {
	Key      string `json:"key"`
	Revision int64  `json:"revision"`
}
type CredentialRevision struct {
	Key           string         `json:"key"`
	Revision      int64          `json:"revision"`
	Available     bool           `json:"available"`
	Changed       bool           `json:"changed"`
	AccountSwitch *AccountSwitch `json:"account_switch,omitempty"`
}
type DeliveryScope struct {
	Keys       []string `json:"keys"`
	AccountIDs []string `json:"account_ids"`
}
type AgentScope struct {
	Keys             []string `json:"credential_keys"`
	ConfirmationKeys []string `json:"confirmation_keys"`
}
type AgentSync struct {
	ConfigDigest   string               `json:"config_digest"`
	Credentials    []CredentialRevision `json:"credentials"`
	RemovedKeys    []string             `json:"removed_keys"`
	DateLastSynced string               `json:"date_last_synced"`
	Scope          AgentScope           `json:"scope"`
}
type AgentSyncOptions struct {
	Credentials          []KnownRevision
	DeliveredCredentials []KnownRevision
	DeliveryScope        *DeliveryScope
	ConfigDigest         string
	SyncStatus           string
	SyncError            string
	RestartSupported     bool
}
type CommandResult struct {
	Accepted bool   `json:"accepted"`
	Status   string `json:"status"`
}

// Event exposes protocol metadata; Credentials contains initial/reconnect snapshot items.
// Data preserves all protocol fields, including future notification payloads.
type Event struct {
	Event          string                     `json:"event"`
	EventID        string                     `json:"event_id"`
	CommandID      string                     `json:"command_id"`
	Key            string                     `json:"key"`
	CredentialKey  string                     `json:"credential_key"`
	CredentialMode string                     `json:"credential_mode"`
	AccountID      string                     `json:"account_id"`
	AccountSwitch  *AccountSwitch             `json:"account_switch,omitempty"`
	Revision       int64                      `json:"revision"`
	Credentials    []Event                    `json:"credentials"`
	Data           map[string]json.RawMessage `json:"-"`
}

func (e *Event) UnmarshalJSON(raw []byte) error {
	type fields Event
	var value fields
	if err := json.Unmarshal(raw, &value); err != nil {
		return err
	}
	data, err := object(raw)
	if err != nil {
		return err
	}
	*e = Event(value)
	e.Data = data
	return nil
}

type CommandHandler func(Event) error

type PAMError struct {
	Code       string
	StatusCode int
	Detail     string
	RequestID  string
	Err        error
}

func (e *PAMError) Error() string { return fmt.Sprintf("[%s] %s", e.Code, e.Detail) }
func (e *PAMError) Unwrap() error { return e.Err }

func required(data map[string]json.RawMessage, names ...string) error {
	for _, name := range names {
		value, ok := data[name]
		if !ok || string(value) == "null" || string(value) == `""` {
			return fmt.Errorf("missing %s", name)
		}
	}
	return nil
}
func object(data []byte) (map[string]json.RawMessage, error) {
	var values map[string]json.RawMessage
	if err := json.Unmarshal(data, &values); err != nil {
		return nil, err
	}
	if values == nil {
		return nil, fmt.Errorf("response must be an object")
	}
	return values, nil
}
func validCredential(data map[string]json.RawMessage) error {
	if err := required(data, "key", "revision", "asset", "account"); err != nil {
		return err
	}
	var c Credential
	bytes, _ := json.Marshal(data)
	if err := json.Unmarshal(bytes, &c); err != nil {
		return err
	}
	if c.Key == "" || c.Revision < 0 {
		return fmt.Errorf("invalid credential revision")
	}
	for _, item := range []struct {
		data   json.RawMessage
		fields []string
	}{
		{data["asset"], []string{"id", "name", "address", "platform"}},
		{data["account"], []string{"id", "name", "username", "secret_type", "secret"}},
	} {
		nested, err := object(item.data)
		if err != nil {
			return err
		}
		if err = required(nested, item.fields...); err != nil {
			return err
		}
	}
	asset, _ := object(data["asset"])
	platform, err := object(asset["platform"])
	if err != nil {
		return err
	}
	return required(platform, "id", "name", "category", "type")
}
