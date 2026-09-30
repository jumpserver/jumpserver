//go:build !windows

package agent

import (
	"context"
	"encoding/json"
	"errors"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"os/user"
	"path/filepath"
	"strings"
	"testing"
	"time"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

type fakeRemote struct {
	value                      pam.Credential
	metadata                   int64
	fault                      error
	credentialFault            error
	unsubscribed               bool
	confirmFault               error
	fetched, confirmed, claims int
	commandResults             []string
}

func (f *fakeRemote) SyncAgent(context.Context, pam.AgentSyncOptions) (pam.AgentSync, error) {
	if f.unsubscribed {
		return pam.AgentSync{ConfigDigest: "digest", Scope: pam.AgentScope{Keys: []string{}, ConfirmationKeys: []string{}}, Credentials: []pam.CredentialRevision{}}, f.fault
	}
	return pam.AgentSync{ConfigDigest: "digest", Scope: pam.AgentScope{Keys: []string{f.value.Key}, ConfirmationKeys: []string{f.value.Key}}, Credentials: []pam.CredentialRevision{{Key: f.value.Key, Revision: f.metadata, Available: true}}}, f.fault
}
func (f *fakeRemote) ListAuthorizedAccounts(context.Context) ([]pam.AuthorizedAccount, error) {
	return []pam.AuthorizedAccount{{ID: f.value.Account.ID, Name: f.value.Account.Name, Username: f.value.Account.Username, SecretType: f.value.Account.SecretType, Asset: f.value.Asset, Credentials: []pam.AccountPolicy{{Key: f.value.Key, Revision: f.metadata, Mode: "alternating_rotation"}}}}, f.fault
}
func (f *fakeRemote) GetCredentialFresh(_ context.Context, selector pam.CredentialSelector) (pam.Credential, error) {
	f.fetched++
	if f.credentialFault != nil {
		return f.value, f.credentialFault
	}
	if selector.AccountID != "" {
		if selector.AccountID != f.value.Account.ID {
			return pam.Credential{}, &pam.PAMError{Code: "credential_not_authorized", StatusCode: 403}
		}
		value := f.value
		value.Key = "account:" + selector.AccountID
		return value, f.fault
	}
	return f.value, f.fault
}
func (f *fakeRemote) WatchCredentialEvents(ctx context.Context, _ func(pam.Event) error) error {
	<-ctx.Done()
	return ctx.Err()
}
func (f *fakeRemote) ConfirmCredential(context.Context, string, int64, string) (pam.CredentialConfirmation, error) {
	f.confirmed++
	return pam.CredentialConfirmation{}, f.confirmFault
}
func (f *fakeRemote) ListApplicationCommands(context.Context) ([]pam.Event, error) { return nil, nil }
func (f *fakeRemote) ReportApplicationCommandResult(_ context.Context, _ string, status, _ string) (pam.CommandResult, error) {
	f.commandResults = append(f.commandResults, status)
	if status == "running" {
		f.claims++
	}
	return pam.CommandResult{Accepted: f.claims == 1, Status: "running"}, nil
}

// Use a private directory under the checkout; /tmp has writable ancestors and
// deliberately fails production path checks. No root/systemd mutation is tested.
func fixture(t *testing.T) (Config, *fakeRemote, *Agent) {
	t.Helper()
	directory, err := os.MkdirTemp(".", ".agent-test-")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.RemoveAll(directory) })
	root, err := filepath.Abs(directory)
	if err != nil {
		t.Fatal(err)
	}
	account, err := user.Current()
	if err != nil {
		t.Fatal(err)
	}
	config := Config{Endpoint: "https://example.com", AppID: "app", AppSecret: "secret", InstanceID: "instance", StateFile: filepath.Join(root, "state.json"), ReconcileSeconds: 300, Delivery: DeliveryConfiguration{Mode: "socket", Root: filepath.Join(root, "output"), Socket: filepath.Join(root, "run", "agent.sock"), User: account.Username}}
	remote := &fakeRemote{metadata: 2, value: pam.Credential{Key: "db", Revision: 2, Account: pam.Account{ID: "account", Secret: "latest-2"}}}
	service, err := New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	return config, remote, service
}

func TestLegacySubscriptionKeyMigratesToOneAccountFile(t *testing.T) {
	config, remote, service := fixture(t)
	config.Delivery.Mode = "json"
	accountID := remote.value.Account.ID
	oldKeys := []string{"orders-db:" + accountID, "other-policy:" + accountID}
	newKey := "account:" + accountID
	remote.value.Key = newKey
	for _, oldKey := range oldKeys {
		service.state.Latest[oldKey] = Credential{Key: oldKey, AccountID: accountID, Revision: remote.metadata, Secret: "previous"}
		service.state.Authorized[oldKey] = true
		service.state.Delivered[oldKey] = remote.metadata
	}
	if err := service.persist(); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(config.Delivery.Root, 0700); err != nil {
		t.Fatal(err)
	}
	for _, oldKey := range oldKeys {
		oldFile := filepath.Join(config.Delivery.Root, oldKey+".json")
		if err := os.WriteFile(oldFile, []byte(`{"secret":"previous"}`), 0600); err != nil {
			t.Fatal(err)
		}
	}
	restarted, err := New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	if err = restarted.Sync(context.Background()); err != nil {
		t.Fatal(err)
	}
	for _, oldKey := range oldKeys {
		oldFile := filepath.Join(config.Delivery.Root, oldKey+".json")
		if _, err = os.Stat(oldFile); !os.IsNotExist(err) {
			t.Fatalf("legacy default file remains: %v", err)
		}
		if _, exists := restarted.state.Latest[oldKey]; exists {
			t.Fatal("legacy subscription secret remains in Agent state")
		}
	}
	if _, err = os.Stat(filepath.Join(config.Delivery.Root, newKey+".json")); err != nil {
		t.Fatalf("account file was not delivered: %v", err)
	}
	if !restarted.state.Authorized[newKey] || restarted.state.Delivered[newKey] != remote.metadata {
		t.Fatal("account key was not authorized and delivered")
	}
}

func TestPolicyRevocationKeepsSharedAccountUntilLastPushPolicy(t *testing.T) {
	_, remote, service := fixture(t)
	remote.value.Key = "account:" + remote.value.Account.ID
	if err := service.Sync(context.Background()); err != nil {
		t.Fatal(err)
	}
	event := pam.Event{Event: "credential.revoked", CredentialKey: "cred-first", CredentialMode: "subscription", AccountID: remote.value.Account.ID}
	if err := service.HandleEvent(context.Background(), event); err != nil {
		t.Fatal(err)
	}
	if !service.state.Authorized[remote.value.Key] {
		t.Fatal("removing one push policy revoked an account covered by another")
	}
	remote.unsubscribed = true
	if err := service.HandleEvent(context.Background(), event); err != nil {
		t.Fatal(err)
	}
	if service.state.Authorized[remote.value.Key] {
		t.Fatal("removing the last push policy retained the account")
	}
}

func TestUpdateFetchRetentionOfflineRestartAndRevocation(t *testing.T) {
	config, remote, service := fixture(t)
	ctx := context.Background()
	if err := service.Sync(ctx); err != nil {
		t.Fatal(err)
	}
	remote.metadata = 3
	remote.value.Revision = 3
	remote.value.Account.Secret = "latest-3"
	if err := service.HandleEvent(ctx, pam.Event{Event: "credential.updated", CredentialKey: "db", Revision: 3}); err != nil {
		t.Fatal(err)
	}
	if remote.fetched != 2 {
		t.Fatal("notification did not refetch the latest credential")
	}
	remote.fault = &pam.PAMError{Code: "NetworkError"}
	if service.Sync(ctx) == nil {
		t.Fatal("outage was silently ignored")
	}
	restarted, err := New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	value, err := restarted.LocalCredential("db")
	if err != nil || value.Secret != "latest-3" {
		t.Fatal("offline restart lost latest credentials", err)
	}
	if restarted.HandleEvent(ctx, pam.Event{Event: "credential.revoked", CredentialKey: "db"}) == nil {
		t.Fatal("expected offline synchronization error")
	}
	restarted, err = New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = restarted.LocalCredential("db"); err == nil {
		t.Fatal("revocation was not persisted during the outage")
	}
}

func TestJournalRecordsReceivedSavedAndDeliveredWithoutPasswords(t *testing.T) {
	config, remote, _ := fixture(t)
	config.EventFile = filepath.Join(filepath.Dir(config.StateFile), "events.jsonl")
	config.Delivery.Mode = "json"
	service, err := New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	event := pam.Event{Event: "credential.updated", EventID: "update-2", CredentialKey: "db", Revision: 2, Data: map[string]json.RawMessage{"secret": json.RawMessage(`"NEVER_RECORD_THIS"`)}}
	if err = service.HandleEvent(context.Background(), event); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(config.EventFile)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(data), remote.value.Account.Secret) || strings.Contains(string(data), "NEVER_RECORD_THIS") {
		t.Fatal("event journal exposed credential or future event payload")
	}
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	if len(lines) != 3 {
		t.Fatalf("expected received, saved and delivered records; got %d", len(lines))
	}
	for i, phase := range []string{"received", "saved", "delivered"} {
		var record map[string]any
		if err = json.Unmarshal([]byte(lines[i]), &record); err != nil || record["phase"] != phase || record["credential_key"] != "db" || record["timestamp"] == "" {
			t.Fatalf("invalid journal phase %s", phase)
		}
	}
	data, err = os.ReadFile(filepath.Join(config.Delivery.Root, "db.json"))
	var delivered Credential
	if err != nil || json.Unmarshal(data, &delivered) != nil || delivered.Secret != remote.value.Account.Secret {
		t.Fatal("latest password was not delivered separately")
	}
	info, _ := os.Stat(config.EventFile)
	if info.Mode().Perm() != 0600 {
		t.Fatal("event journal is not private")
	}
	remote.fault = &pam.PAMError{Code: "NetworkError"}
	if service.HandleEvent(context.Background(), pam.Event{Event: "credential.updated", CredentialKey: "db", Revision: 3}) == nil {
		t.Fatal("outage was ignored")
	}
	data, _ = os.ReadFile(config.EventFile)
	if len(strings.Split(strings.TrimSpace(string(data)), "\n")) != 4 {
		t.Fatal("failed refresh did not preserve its received event")
	}
	data, _ = os.ReadFile(filepath.Join(config.Delivery.Root, "db.json"))
	if json.Unmarshal(data, &delivered) != nil || delivered.Revision != 2 {
		t.Fatal("failed refresh replaced the delivered password")
	}
}

func TestJournalFailureDoesNotPreventRevocation(t *testing.T) {
	config, remote, _ := fixture(t)
	config.EventFile = filepath.Join(filepath.Dir(config.StateFile), "events.jsonl")
	service, err := New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	if err = service.Sync(context.Background()); err != nil {
		t.Fatal(err)
	}
	if err = os.Remove(config.EventFile); err != nil {
		t.Fatal(err)
	}
	if err = os.Symlink(config.StateFile, config.EventFile); err != nil {
		t.Fatal(err)
	}
	remote.fault = &pam.PAMError{Code: "NetworkError"}
	if service.HandleEvent(context.Background(), pam.Event{Event: "credential.revoked", CredentialKey: "db"}) == nil {
		t.Fatal("unsafe journal and backend outage were ignored")
	}
	restored, err := New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = restored.LocalCredential("db"); err == nil {
		t.Fatal("failed journal prevented authorization reduction")
	}
}

func TestLocalModeKeepsExecutionSettingsLocal(t *testing.T) {
	config, _, _ := fixture(t)
	config.Local = true
	config.Delivery.Mode = "json"
	config.Rules = []Rule{{Keys: []string{"db"}, Action: &Action{Type: "systemd", Unit: "orders.service", Operation: "reload"}}}
	if config.Validate() == nil {
		t.Fatal("local mode accepted a systemd action")
	}
}

func TestUnknownConfigurationFieldIsRejected(t *testing.T) {
	config, _, _ := fixture(t)
	path := filepath.Join(filepath.Dir(config.StateFile), "agent.json")
	raw, _ := json.Marshal(config)
	var value map[string]any
	_ = json.Unmarshal(raw, &value)
	value["unexpected"] = "value"
	raw, _ = json.Marshal(value)
	if err := os.WriteFile(path, raw, 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := LoadConfig(path); err == nil {
		t.Fatal("unknown field was silently accepted")
	}
}

func TestAccountQueriesUseLiveAPIAndOnlyTemporaryFallback(t *testing.T) {
	_, remote, service := fixture(t)
	ctx := context.Background()
	if err := service.Sync(ctx); err != nil {
		t.Fatal(err)
	}
	accounts, err := service.Accounts(ctx)
	if err != nil || accounts.Source != "api" || len(accounts.Accounts) != 1 || remote.fetched != 1 {
		t.Fatal("account metadata fetched passwords or did not use live authorization", err)
	}
	value, err := service.AccountCredential(ctx, "account")
	if err != nil || value.Source != "api" || value.Secret != "latest-2" {
		t.Fatal("live account lookup failed", err)
	}
	if _, err = service.AccountCredential(ctx, "unlisted"); err == nil || remote.fetched != 3 {
		t.Fatal("unlisted account was accepted")
	}
	remote.metadata, remote.value.Revision = 3, 3
	remote.value.Account.Secret = "latest-3"
	value, err = service.AccountCredential(ctx, "account")
	if err != nil || value.Revision != 3 {
		t.Fatal("CLI did not pull the latest value", err)
	}
	if err = service.Sync(ctx); err != nil {
		t.Fatal("push cache did not refresh", err)
	}
	remote.credentialFault = &pam.PAMError{Code: "ResponseError", StatusCode: 200}
	if _, err = service.AccountCredential(ctx, "account"); err == nil {
		t.Fatal("invalid success fell back")
	}
	remote.credentialFault = nil
	remote.fault = &pam.PAMError{Code: "NetworkError"}
	accounts, err = service.Accounts(ctx)
	if err != nil || accounts.Source != "local" || len(accounts.Accounts) != 1 {
		t.Fatal("offline account metadata was unavailable", err)
	}
	value, err = service.AccountCredential(ctx, "account")
	if err != nil || value.Source != "local" || value.Secret != "latest-3" {
		t.Fatal("offline query lost the latest password", err)
	}
	remote.fault = &pam.PAMError{Code: "credential_not_authorized", StatusCode: 403}
	if _, err = service.AccountCredential(ctx, "account"); err == nil {
		t.Fatal("authorization failure fell back")
	}
	remote.fault = &pam.PAMError{Code: "NetworkError"}
	if _, err = service.AccountCredential(ctx, "account"); err == nil {
		t.Fatal("later outage revived explicitly denied credentials")
	}
}

func TestPullOnlyCredentialIsNotPersistedForOfflineUse(t *testing.T) {
	_, remote, service := fixture(t)
	value, err := service.AccountCredential(context.Background(), "account")
	if err != nil || value.Source != "api" || len(service.state.Latest) != 0 {
		t.Fatal("pull-only access was not served on demand", err)
	}
	remote.fault = &pam.PAMError{Code: "NetworkError"}
	if _, err = service.AccountCredential(context.Background(), "account"); err == nil {
		t.Fatal("pull-only credential was available offline")
	}
}

func TestSubscriptionEventUsesAccountKeyForRevisionFloor(t *testing.T) {
	config, remote, _ := fixture(t)
	key := "db:account"
	remote.value.Key = key
	service, err := New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	if err = service.Sync(ctx); err != nil {
		t.Fatal(err)
	}
	remote.metadata, remote.value.Revision = 4, 4
	if service.HandleEvent(ctx, pam.Event{Event: "credential.updated", CredentialKey: "db", CredentialMode: "subscription", AccountID: "account", Revision: 5}) == nil {
		t.Fatal("subscription notification accepted an API value older than the event")
	}
	value, err := service.LocalCredential(key)
	if err != nil || value.Revision != 2 || service.state.Wanted[key] != 5 {
		t.Fatal("behind API replaced the latest subscription password or lost its revision floor")
	}
}

func TestOutdatedResponseCannotReplaceLatestOrCancelNewerRetry(t *testing.T) {
	_, remote, service := fixture(t)
	ctx := context.Background()
	if err := service.Sync(ctx); err != nil {
		t.Fatal(err)
	}
	remote.metadata = 3
	if service.HandleEvent(ctx, pam.Event{Event: "credential.updated", CredentialKey: "db", Revision: 4}) == nil {
		t.Fatal("behind API was accepted")
	}
	_ = service.HandleEvent(ctx, pam.Event{Event: "credential.updated", CredentialKey: "db", Revision: 3})
	if service.state.Wanted["db"] != 4 || service.state.Latest["db"].Revision != 2 {
		t.Fatal("latest value or newer retry was lost")
	}
	remote.metadata = 4
	remote.value.Revision = 4
	if err := service.Sync(ctx); err != nil {
		t.Fatal(err)
	}
	remote.metadata = 2
	remote.value.Revision = 2
	if service.Sync(ctx) == nil || service.state.Latest["db"].Revision != 4 {
		t.Fatal("older API revision overwrote a newer credential")
	}
}

func TestFailedDeliveryRetainsPasswordAndDoesNotConfirm(t *testing.T) {
	_, remote, service := fixture(t)
	service.deliver = func(context.Context, Config, map[string]Credential, map[string]bool) error {
		return errors.New("failed")
	}
	if service.Sync(context.Background()) == nil {
		t.Fatal("delivery failure ignored")
	}
	if service.state.Latest["db"].Revision != 2 || len(service.state.Delivered) != 0 || remote.confirmed != 0 {
		t.Fatal("failed delivery lost latest or marked it applied")
	}
	service.deliver = Deliver
	if err := service.Sync(context.Background()); err != nil {
		t.Fatal(err)
	}
	if service.state.Delivered["db"] != 2 || remote.confirmed != 0 {
		t.Fatal("delivery was confirmed automatically")
	}
}

func TestConfirmationPersistsBeforeReportingAndRetries(t *testing.T) {
	config, remote, service := fixture(t)
	ctx := context.Background()
	if err := service.Sync(ctx); err != nil {
		t.Fatal(err)
	}
	remote.confirmFault = &pam.PAMError{Code: "NetworkError"}
	value, err := service.Confirm(ctx, "db", 2)
	if err != nil || value.Confirmed {
		t.Fatal("failed confirmation must be retained as pending", err)
	}
	restarted, err := New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	remote.confirmFault = nil
	if err = restarted.Sync(ctx); err != nil {
		t.Fatal(err)
	}
	if !restarted.state.Applied["db"].Confirmed {
		t.Fatal("pending confirmation was not retried")
	}
	if _, err = restarted.Confirm(ctx, "db", 1); err == nil {
		t.Fatal("wrong revision was confirmed")
	}
}

func TestFileTemplateAndScriptDelivery(t *testing.T) {
	config, _, _ := fixture(t)
	root := filepath.Dir(config.StateFile)
	source := filepath.Join(root, "config.tmpl")
	target := filepath.Join(root, "service.json")
	script := filepath.Join(root, "apply.sh")
	input := filepath.Join(root, "received.json")
	if err := os.WriteFile(source, []byte(`{"password": {{json (index .Credentials "db").Secret}}}`), 0600); err != nil {
		t.Fatal(err)
	}
	// A fixed trusted executable reads secrets from stdin, never arguments.
	if err := os.WriteFile(script, []byte("#!/bin/sh\ncat > \"$1\"\n"), 0700); err != nil {
		t.Fatal(err)
	}
	config.Rules = []Rule{{Keys: []string{"db"}, Files: []File{{Path: target, Format: "template", Template: source}}, Action: &Action{Type: "script", Path: script, Args: []string{input}, TimeoutSeconds: 1}}}
	if err := config.Validate(); err != nil {
		t.Fatal(err)
	}
	value := Credential{Key: "db", Revision: 3, Secret: "quote\" and $password"}
	if err := Deliver(context.Background(), config, map[string]Credential{"db": value}, map[string]bool{"db": true}); err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	var rendered map[string]string
	if json.Unmarshal(raw, &rendered) != nil || rendered["password"] != value.Secret {
		t.Fatal("template did not escape the password")
	}
	raw, err = os.ReadFile(input)
	if err != nil {
		t.Fatal(err)
	}
	var payload Payload
	if json.Unmarshal(raw, &payload) != nil || payload.Credentials["db"].Secret != value.Secret {
		t.Fatal("script did not receive JSON on stdin")
	}
	info, _ := os.Stat(target)
	if info.Mode().Perm() != 0600 {
		t.Fatal("credentials must be private")
	}
	value.Secret = "latest-4"
	value.Revision = 4
	if err = Deliver(context.Background(), config, map[string]Credential{"db": value}, map[string]bool{"db": true}); err != nil {
		t.Fatal("atomic update failed", err)
	}
}

func TestTemplateFailureDoesNotMutateFilesAndScriptTimeout(t *testing.T) {
	config, _, _ := fixture(t)
	root := filepath.Dir(config.StateFile)
	target := filepath.Join(root, "config.json")
	source := filepath.Join(root, "invalid.tmpl")
	_ = os.WriteFile(target, []byte("old"), 0600)
	_ = os.WriteFile(source, []byte(`{{(index .Credentials "missing").DoesNotExist}}`), 0600)
	config.Rules = []Rule{{Keys: []string{"db"}, Files: []File{{Path: target, Format: "template", Template: source}}}}
	if Deliver(context.Background(), config, map[string]Credential{"db": {Key: "db", Secret: "new"}}, map[string]bool{"db": true}) == nil {
		t.Fatal("invalid template accepted")
	}
	raw, _ := os.ReadFile(target)
	if string(raw) != "old" {
		t.Fatal("failed render modified the original file")
	}
	script := filepath.Join(root, "hang.sh")
	_ = os.WriteFile(script, []byte("#!/bin/sh\nsleep 30\n"), 0700)
	started := time.Now()
	err := execute(context.Background(), Action{Type: "script", Path: script, TimeoutSeconds: 1}, Payload{})
	if err == nil || time.Since(started) > 4*time.Second {
		t.Fatal("script process group did not time out")
	}
}

func TestConfigCapabilitiesPathsAndLocalAPI(t *testing.T) {
	config, remote, service := fixture(t)
	config.Rules = []Rule{{Keys: []string{"db"}, Action: &Action{Type: "script", Path: "sh -c echo secret"}}}
	if config.Validate() == nil {
		t.Fatal("shell command accepted instead of absolute executable")
	}
	path := filepath.Join(filepath.Dir(config.StateFile), "symlink")
	_ = os.Symlink(config.StateFile, path)
	if atomicWrite(path, []byte("secret"), 0600, -1, -1) == nil {
		t.Fatal("symlink target accepted")
	}
	if err := service.Sync(context.Background()); err != nil {
		t.Fatal(err)
	}
	recorder := httptest.NewRecorder()
	service.ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/v1/credentials/db", nil))
	if recorder.Code != 200 || recorder.Header().Get("Cache-Control") != "no-store" {
		t.Fatal("local credential API failed")
	}
	remote.fault = &pam.PAMError{Code: "client_disabled", StatusCode: 403}
	_ = service.Sync(context.Background())
	recorder = httptest.NewRecorder()
	service.ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/v1/credentials/db", nil))
	if recorder.Code != 503 {
		t.Fatal("disabled identity still served a password")
	}
}

func TestFixedServiceAndPrivateConfig(t *testing.T) {
	config, _, _ := fixture(t)
	path := filepath.Join(filepath.Dir(config.StateFile), "agent.json")
	if err := writeJSON(path, config); err != nil {
		t.Fatal(err)
	}
	if _, err := LoadConfig(path); err != nil {
		t.Fatal(err)
	}
	_ = os.Chmod(path, 0644)
	if _, err := LoadConfig(path); err == nil {
		t.Fatal("public identity file accepted")
	}
	unit := Unit("/usr/local/bin/jms-pam-agent", DefaultConfig)
	if ServiceName != "jms-pam-agent.service" || !strings.Contains(unit, "/etc/jms-pam-agent/agent.json") {
		t.Fatal("service name or path is not fixed")
	}
}

func TestRelativeConfigPathRetainsPrivateFileChecks(t *testing.T) {
	config, _, _ := fixture(t)
	path := filepath.Join(filepath.Dir(config.StateFile), "agent.json")
	if err := writeJSON(path, config); err != nil {
		t.Fatal(err)
	}
	cwd, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	relative, err := filepath.Rel(cwd, path)
	if err != nil {
		t.Fatal(err)
	}
	loaded, err := LoadConfig(relative)
	if err != nil || loaded.InstanceID != config.InstanceID {
		t.Fatal("relative configuration could not be loaded", err)
	}
	link := filepath.Join(filepath.Dir(path), "linked.json")
	if err = os.Symlink(path, link); err != nil {
		t.Fatal(err)
	}
	relativeLink, _ := filepath.Rel(cwd, link)
	if _, err = LoadConfig(relativeLink); err == nil {
		t.Fatal("relative path bypassed the symlink restriction")
	}
	if err = os.Chmod(path, 0644); err != nil {
		t.Fatal(err)
	}
	if _, err = LoadConfig(relative); err == nil {
		t.Fatal("relative path bypassed private file permissions")
	}
}

func TestRetainedStateCannotBeReusedByAnotherIdentity(t *testing.T) {
	config, remote, service := fixture(t)
	if err := service.Sync(context.Background()); err != nil {
		t.Fatal(err)
	}
	config.AppID = "different-app"
	if _, err := New(config, remote); err == nil {
		t.Fatal("another identity reused retained credentials")
	}
}

func TestRunServesRetainedCredentialsOfflineAndStopsCleanly(t *testing.T) {
	config, remote, service := fixture(t)
	if err := service.Sync(context.Background()); err != nil {
		t.Fatal(err)
	}
	remote.fault = &pam.PAMError{Code: "NetworkError"}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan error, 1)
	go func() { done <- service.Run(ctx) }()
	transport := &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, "unix", config.Delivery.Socket)
	}}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: time.Second}
	var response *http.Response
	var err error
	for i := 0; i < 100; i++ {
		response, err = client.Get("http://localhost/v1/credentials/db")
		if err == nil {
			break
		}
		time.Sleep(5 * time.Millisecond)
	}
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	var value Credential
	if json.NewDecoder(response.Body).Decode(&value) != nil || response.StatusCode != 200 || value.Secret != "latest-2" {
		t.Fatal("offline local API did not return retained latest credential")
	}
	cancel()
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("Agent did not join its reader and stop")
	}
	if _, err = os.Lstat(config.Delivery.Socket); !os.IsNotExist(err) {
		t.Fatal("Agent socket was left behind")
	}
}

func TestNativeAgentAutomaticallyRefreshesAndRestartsOffline(t *testing.T) {
	endpoint := os.Getenv("JMS_TEST_ENDPOINT")
	if endpoint == "" {
		t.Skip("Use clients/tests/run.py for the native protocol fixture")
	}
	config, _, _ := fixture(t)
	config.Endpoint = endpoint
	config.AppID = "contract-app"
	config.AppSecret = "contract-secret"
	config.OrgID = "contract-org"
	config.InstanceID = "agent-native-go"
	config.Delivery.Mode = "json"
	config.EventFile = filepath.Join(filepath.Dir(config.StateFile), "events.jsonl")
	control := func(values url.Values) {
		t.Helper()
		values.Set("instance", config.InstanceID)
		response, err := http.Get(strings.TrimSuffix(endpoint, "/prefix") + "/__control?" + values.Encode())
		if err != nil {
			t.Fatal(err)
		}
		response.Body.Close()
		if response.StatusCode != 200 {
			t.Fatal("fixture control failed")
		}
	}
	control(url.Values{"delivery_root": {config.Delivery.Root}, "socket_path": {config.Delivery.Socket}, "app_user": {config.Delivery.User}, "delivery_mode": {"json"}})
	remote, err := config.Client()
	if err != nil {
		t.Fatal(err)
	}
	defer remote.Close()
	service, err := New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- service.Run(ctx) }()
	defer func() {
		cancel()
		select {
		case <-done:
		case <-time.After(3 * time.Second):
			t.Error("native Agent failed to stop")
		}
	}()
	waitRevision := func(revision int64) {
		t.Helper()
		for i := 0; i < 300; i++ {
			value, err := service.LocalCredential("db")
			if err == nil && value.Revision == revision {
				return
			}
			time.Sleep(10 * time.Millisecond)
		}
		t.Fatalf("automatic refresh did not reach revision %d", revision)
	}
	waitRevision(2)
	// Wait for the event connection, then notify without calling Sync or fetching.
	time.Sleep(50 * time.Millisecond)
	control(url.Values{"revision": {"3"}, "event": {"credential.updated"}})
	waitRevision(3)
	// LocalCredential becomes available before delivery completes; queries wait
	// for the serialized update and therefore verify both native query and files.
	queried, err := service.AccountCredential(context.Background(), "account")
	if err != nil || queried.Source != "api" || queried.Revision != 3 {
		t.Fatal("native account query failed", err)
	}
	raw, err := os.ReadFile(filepath.Join(config.Delivery.Root, "db.json"))
	var file Credential
	if err != nil || json.Unmarshal(raw, &file) != nil || file.Revision != 3 || file.Secret != queried.Secret {
		t.Fatal("native notification did not update the latest password file")
	}
	control(url.Values{"fault": {"503"}})
	if service.Sync(context.Background()) == nil {
		t.Fatal("backend outage was ignored")
	}
	queried, err = service.AccountCredential(context.Background(), "account")
	if err != nil || queried.Source != "local" || queried.Revision != 3 {
		t.Fatal("native account query did not fall back during HTTP 503", err)
	}
	restarted, err := New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	retained, err := restarted.LocalCredential("db")
	if err != nil || retained.Secret != "LATEST_SECRET_3" {
		t.Fatal("native offline restart lost the latest credential", err)
	}
}

func TestLocalRuleChangeRedeliversCurrentRevision(t *testing.T) {
	config, remote, service := fixture(t)
	ctx := context.Background()
	if err := service.Sync(ctx); err != nil {
		t.Fatal(err)
	}
	config.Rules = []Rule{{Keys: []string{"db"}, Files: []File{{Path: filepath.Join(filepath.Dir(config.StateFile), "new-service.json"), Format: "json"}}}}
	restarted, err := New(config, remote)
	if err != nil {
		t.Fatal(err)
	}
	if len(restarted.state.Delivered) != 0 {
		t.Fatal("a new local rule reused delivery state for an old target")
	}
	if err = restarted.Sync(ctx); err != nil {
		t.Fatal(err)
	}
	if _, err = os.Stat(config.Rules[0].Files[0].Path); err != nil {
		t.Fatal("new target was not populated with the current revision")
	}
}

func TestRevokedCredentialCannotResumeFromStaleMetadataWithoutLiveFetch(t *testing.T) {
	_, remote, service := fixture(t)
	ctx := context.Background()
	if err := service.Sync(ctx); err != nil {
		t.Fatal(err)
	}
	remote.credentialFault = &pam.PAMError{Code: "credential_not_found", StatusCode: 400}
	if service.HandleEvent(ctx, pam.Event{Event: "credential.updated", CredentialKey: "db", Revision: 2}) == nil {
		t.Fatal("deleted credential was accepted")
	}
	if _, err := service.LocalCredential("db"); err == nil {
		t.Fatal("deleted credential remained accessible")
	}
	// A lagging metadata response still claims revision 2 is available. Requiring
	// a new live fetch prevents that response from restoring the revoked password.
	if service.Sync(ctx) == nil {
		t.Fatal("stale metadata silently restored a revoked credential")
	}
	if _, err := service.LocalCredential("db"); err == nil {
		t.Fatal("revocation was undone without successful retrieval")
	}
	remote.credentialFault = nil
	if err := service.Sync(ctx); err != nil {
		t.Fatal(err)
	}
	if _, err := service.LocalCredential("db"); err != nil {
		t.Fatal("successful live retrieval did not restore authorized access", err)
	}
}
