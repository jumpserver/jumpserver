//go:build windows

package agent

import (
	"context"
	"encoding/json"
	"net"
	"net/http"
	"os"
	"os/user"
	"path/filepath"
	"strings"
	"testing"
	"time"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

type windowsRemote struct{ credential pam.Credential }

func (r windowsRemote) ListAuthorizedAccounts(context.Context) ([]pam.AuthorizedAccount, error) {
	return nil, nil
}
func (r windowsRemote) SyncAgent(context.Context, pam.AgentSyncOptions) (pam.AgentSync, error) {
	return pam.AgentSync{
		Scope:       pam.AgentScope{Keys: []string{r.credential.Key}},
		Credentials: []pam.CredentialRevision{{Key: r.credential.Key, Revision: r.credential.Revision, Available: true}},
	}, nil
}
func (r windowsRemote) GetCredentialFresh(context.Context, pam.CredentialSelector) (pam.Credential, error) {
	return r.credential, nil
}
func (r windowsRemote) WatchCredentialEvents(ctx context.Context, _ func(pam.Event) error) error {
	<-ctx.Done()
	return ctx.Err()
}
func (r windowsRemote) ConfirmCredential(context.Context, string, int64, string) (pam.CredentialConfirmation, error) {
	return pam.CredentialConfirmation{}, nil
}
func (r windowsRemote) ListApplicationCommands(context.Context) ([]pam.Event, error) {
	return nil, nil
}
func (r windowsRemote) ReportApplicationCommandResult(context.Context, string, string, string) (pam.CommandResult, error) {
	return pam.CommandResult{}, nil
}

func TestWindowsForegroundRunKeepsCredentialsPrivate(t *testing.T) {
	home, err := os.UserHomeDir()
	if err != nil {
		t.Fatal(err)
	}
	directory, err := os.MkdirTemp(home, ".jms-pam-agent-test-")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.RemoveAll(directory) })
	if err := protectPrivate(directory); err != nil {
		t.Fatal(err)
	}
	account, err := user.Current()
	if err != nil {
		t.Fatal(err)
	}
	key := "account:windows-test"
	config := Config{
		Local: true, Endpoint: "https://example.com", AppID: "app", AppSecret: "secret",
		InstanceID: "windows-test", StateFile: filepath.Join(directory, "state.json"),
		EventFile: filepath.Join(directory, "events.jsonl"), ReconcileSeconds: 300,
		Delivery: DeliveryConfiguration{
			Mode: "json", Root: filepath.Join(directory, "credentials"),
			Socket: filepath.Join(directory, "agent.sock"), User: account.Username,
		},
	}
	remote := windowsRemote{credential: pam.Credential{
		Key: key, Revision: 1, Account: pam.Account{ID: "windows-test", Secret: "private-secret"},
	}}
	service, err := New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- service.Run(ctx) }()
	defer func() { cancel(); <-done }()
	var response *http.Response
	transport := &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, "unix", config.Delivery.Socket)
	}}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: time.Second}
	for i := 0; i < 50; i++ {
		response, err = client.Get("http://localhost/v1/health")
		if err == nil {
			break
		}
		time.Sleep(20 * time.Millisecond)
	}
	if err != nil {
		t.Fatal(err)
	}
	response.Body.Close()
	if response.StatusCode != 200 {
		t.Fatalf("health HTTP %d", response.StatusCode)
	}
	filename := filepath.Join(config.Delivery.Root, defaultCredentialFilename(key, "json"))
	var delivered Credential
	for i := 0; i < 50; i++ {
		raw, readErr := os.ReadFile(filename)
		if readErr == nil && json.Unmarshal(raw, &delivered) == nil {
			break
		}
		time.Sleep(20 * time.Millisecond)
	}
	if delivered.Secret != "private-secret" || strings.Contains(filepath.Base(filename), ":") {
		t.Fatal("Windows credential delivery failed or used an invalid filename")
	}
	for _, path := range []string{config.StateFile, filename} {
		if err := privateFile(path); err != nil {
			t.Fatalf("credential file is not private: %v", err)
		}
	}
}
