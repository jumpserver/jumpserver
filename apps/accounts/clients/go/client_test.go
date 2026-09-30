package pam

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"strings"
	"testing"
	"time"
)

func contractClient(t *testing.T, instance, source string) *Client {
	t.Helper()
	endpoint := os.Getenv("JMS_TEST_ENDPOINT")
	if endpoint == "" {
		t.Skip("Run clients/tests/run.py to start the shared protocol fixture")
	}
	client, err := NewClient(Options{Endpoint: endpoint, AppID: "contract-app", AppSecret: "contract-secret", InstanceID: instance, OrgID: "contract-org", Source: source})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { client.Close() })
	return client
}
func TestSignedCredentialOperations(t *testing.T) {
	client := contractClient(t, "go", "jms-pam")
	ctx := context.Background()
	for _, selector := range []CredentialSelector{{AccountID: "account"}, {Key: "db/空 格?=&"}} {
		credential, err := client.GetCredential(ctx, selector)
		if err != nil {
			t.Fatal(err)
		}
		if credential.Account.Secret != "DO_NOT_LOG_SECRET" || credential.Account.SecretType != "password" || credential.Asset.Platform.Type != "postgresql" {
			t.Fatal("Invalid structured response")
		}
		if strings.Contains(fmt.Sprintf("%+v %#v", credential, credential), credential.Account.Secret) {
			t.Fatal("Secret leaked in representation")
		}
	}
	confirmation, err := client.ConfirmCredential(ctx, "db", 2, "account")
	if err != nil || confirmation.Revision != 2 {
		t.Fatalf("Confirmation failed: %v", err)
	}
}
func TestValidationAndErrors(t *testing.T) {
	client := contractClient(t, "go-errors", "jms-pam")
	ctx := context.Background()
	for _, selector := range []CredentialSelector{{}, {Key: "db", AccountID: "account"}} {
		if _, err := client.GetCredential(ctx, selector); err == nil {
			t.Fatal("Invalid selector accepted")
		}
	}
	for _, revision := range []int64{0, -1} {
		if _, err := client.ConfirmCredential(ctx, "db", revision, "account"); err == nil {
			t.Fatal("Invalid revision accepted")
		}
	}
	for _, item := range []struct{ key, code string }{{"forbidden", "credential_not_authorized"}, {"upgrade", "client_upgrade_required"}, {"invalid-json", "ResponseError"}, {"invalid-revision", "ResponseError"}, {"redirect", "HTTPError"}} {
		_, err := client.GetCredential(ctx, CredentialSelector{Key: item.key})
		var failure *PAMError
		if !errors.As(err, &failure) || failure.Code != item.code {
			t.Fatalf("Expected %s, received %v", item.code, err)
		}
	}
}
func TestSynchronization(t *testing.T) {
	client := contractClient(t, "go-agent", "jms-pam-agent")
	options := AgentSyncOptions{Credentials: []KnownRevision{{Key: "db", Revision: 2}}}
	sync, err := client.SyncAgent(context.Background(), options)
	if err != nil || sync.Credentials[0].Changed || len(sync.Scope.Keys) != 1 || sync.Scope.Keys[0] != "db" {
		t.Fatalf("Sync failed: %v", err)
	}
	options.SyncError = "invalid-flag"
	_, err = client.SyncAgent(context.Background(), options)
	var failure *PAMError
	if !errors.As(err, &failure) || failure.Code != "ResponseError" {
		t.Fatal("Malformed boolean accepted")
	}
}
func TestCommandLifecycle(t *testing.T) {
	client := contractClient(t, "go-command", "jms-pam")
	ctx := context.Background()
	commands, err := client.ListApplicationCommands(ctx)
	if err != nil {
		t.Fatal(err)
	}
	event := commands[0]
	executed := 0
	result, err := client.ExecuteApplicationCommand(ctx, event, func(Event) error { executed++; return nil })
	if err != nil || result.Status != "success" || executed != 1 {
		t.Fatal("Command did not complete")
	}
	event.CommandID = "duplicate"
	result, err = client.ExecuteApplicationCommand(ctx, event, func(Event) error { executed++; return nil })
	if err != nil || result.Accepted || executed != 1 {
		t.Fatal("Duplicate command executed")
	}
	sentinel := errors.New("business failure")
	event.CommandID = "report-failure"
	_, err = client.ExecuteApplicationCommand(ctx, event, func(Event) error { return sentinel })
	if err != sentinel {
		t.Fatal("Handler exception was replaced")
	}
}
func TestEventsAndCancellation(t *testing.T) {
	client := contractClient(t, "go-events", "jms-pam")
	ctx, cancel := context.WithTimeout(context.Background(), 6*time.Second)
	defer cancel()
	events := []Event{}
	sentinel := errors.New("finished")
	err := client.WatchCredentialEvents(ctx, func(event Event) error {
		events = append(events, event)
		if len(events) == 4 {
			return sentinel
		}
		return nil
	})
	if err != sentinel || len(events) != 4 || events[0].Event != "snapshot" || events[1].Event != "credential.updated" || events[2].Event != "future.notification" || events[3].Credentials[0].Revision != 3 {
		t.Fatalf("Stream failed: %v", err)
	}
	var future map[string]string
	if err := json.Unmarshal(events[2].Data["future_payload"], &future); err != nil || future["notice"] != "preserved" {
		t.Fatal("Future notification fields were lost")
	}
	response, err := http.Get(strings.TrimSuffix(os.Getenv("JMS_TEST_ENDPOINT"), "/prefix") + "/__stats")
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	var stats struct {
		Receipts []struct {
			Instance string `json:"instance"`
			EventID  string `json:"eventId"`
		}
	}
	if err = json.NewDecoder(response.Body).Decode(&stats); err != nil {
		t.Fatal(err)
	}
	received := map[string]bool{}
	for _, receipt := range stats.Receipts {
		if receipt.Instance == "go-events" {
			received[receipt.EventID] = true
		}
	}
	if !received["updated-1"] || !received["future-1"] {
		t.Fatal("Business receipts missing")
	}
	stopped, stop := context.WithCancel(context.Background())
	stop()
	if err = client.WatchCredentialEvents(stopped, func(Event) error { return nil }); !errors.Is(err, context.Canceled) {
		t.Fatal("Cancellation was ignored")
	}
	clone, err := client.Clone()
	if err != nil {
		t.Fatal(err)
	}
	defer clone.Close()
	client.Close()
	if _, err = clone.GetCredential(context.Background(), CredentialSelector{Key: "db"}); err != nil {
		t.Fatal("Clone was closed with original")
	}
}
