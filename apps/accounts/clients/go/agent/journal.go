package agent

import (
	"encoding/json"
	"time"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

// Whitelist notification metadata; never serialize Event.Data or credentials.
type journalMetadata struct {
	Event       string            `json:"event"`
	EventID     string            `json:"event_id,omitempty"`
	CommandID   string            `json:"command_id,omitempty"`
	Key         string            `json:"credential_key,omitempty"`
	Mode        string            `json:"credential_mode,omitempty"`
	AccountID   string            `json:"account_id,omitempty"`
	Revision    int64             `json:"revision"`
	Credentials []journalMetadata `json:"credentials,omitempty"`
}

func metadata(event pam.Event) journalMetadata {
	value := journalMetadata{Event: event.Event, EventID: event.EventID, CommandID: event.CommandID, Key: eventKey(event), Mode: event.CredentialMode, AccountID: event.AccountID, Revision: event.Revision}
	for _, item := range event.Credentials {
		value.Credentials = append(value.Credentials, metadata(item))
	}
	return value
}

func (a *Agent) recordEvent(phase string, event pam.Event) error {
	if a.Config.EventFile == "" {
		return nil
	}
	record := struct {
		Timestamp  string `json:"timestamp"`
		InstanceID string `json:"instance_id"`
		Phase      string `json:"phase"`
		journalMetadata
	}{time.Now().UTC().Format(time.RFC3339Nano), a.Config.InstanceID, phase, metadata(event)}
	raw, err := json.Marshal(record)
	if err != nil {
		return err
	}
	return appendPrivate(a.Config.EventFile, append(raw, '\n'))
}
