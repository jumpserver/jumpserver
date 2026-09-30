package pam

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/url"
	"os"
	"strings"
	"testing"
	"time"
)

func controlBackend(t *testing.T, instance string, values url.Values) {
	t.Helper()
	values.Set("instance", instance)
	response, err := http.Get(strings.TrimSuffix(os.Getenv("JMS_TEST_ENDPOINT"), "/prefix") + "/__control?" + values.Encode())
	if err != nil {
		t.Fatal(err)
	}
	response.Body.Close()
	if response.StatusCode != 200 {
		t.Fatal("Backend control failed")
	}
}

func TestAccountPullRequiresLiveBackendEvenAfterSuccessfulFetch(t *testing.T) {
	instance := "go-live-pull"
	client := contractClient(t, instance, "jms-pam")
	selector := CredentialSelector{AccountID: "account"}
	if _, err := client.GetCredential(context.Background(), selector); err != nil {
		t.Fatal(err)
	}
	controlBackend(t, instance, url.Values{"fault": {"503"}})
	if _, err := client.GetCredential(context.Background(), selector); err == nil {
		t.Fatal("application pull returned a cached secret during backend outage")
	}
}

func TestUpdateEventRefreshesLatestAndOnlyBackendOutageUsesLocal(t *testing.T) {
	instance := "latest-go-events"
	client := contractClient(t, instance, "jms-pam")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	updates := make(chan Credential, 16)
	watcher, err := client.StartEvents(ctx, EventHandlers{
		OnCredentialChanged: func(ctx context.Context, value Credential) error { updates <- value; return nil },
		OnError:             func(context.Context, error, *Event) {},
	})
	if err != nil {
		t.Fatal(err)
	}
	defer func() { watcher.Stop(); watcher.Wait() }()
	select {
	case <-updates:
	case <-ctx.Done():
		t.Fatal("Initial fetch did not complete")
	}
	controlBackend(t, instance, url.Values{"revision": {"3"}, "event": {"credential.updated"}})
	for {
		select {
		case value := <-updates:
			if value.Revision < 3 {
				continue
			}
			if value.FromLocal || value.Account.Secret != "LATEST_SECRET_3" {
				t.Fatal("Update did not fetch current password")
			}
		case <-ctx.Done():
			t.Fatal("Update did not trigger a fetch")
		}
		break
	}
	selector := CredentialSelector{Key: "db"}
	controlBackend(t, instance, url.Values{"fault": {"503"}})
	retained, err := client.GetCredential(ctx, selector)
	if err != nil || !retained.FromLocal || retained.Revision != 3 {
		t.Fatalf("Latest retention failed: %v", err)
	}
	controlBackend(t, instance, url.Values{"fault": {"0"}, "revision": {"4"}})
	live, err := client.GetCredential(ctx, selector)
	if err != nil || live.FromLocal || live.Revision != 4 {
		t.Fatalf("Online API was not preferred: %v", err)
	}
	controlBackend(t, instance, url.Values{"revision": {"2"}})
	if _, err := client.GetCredential(ctx, selector); err == nil {
		t.Fatal("Older backend response accepted")
	}
	controlBackend(t, instance, url.Values{"fault": {"503"}})
	retained, err = client.GetCredential(ctx, selector)
	if err != nil || retained.Revision != 4 {
		t.Fatal("Older response replaced latest credential")
	}
}

func TestCredentialCacheBoundaries(t *testing.T) {
	for _, fault := range []string{"503", "timeout", "401", "403", "404", "426", "revoked", "invalid"} {
		t.Run(fault, func(t *testing.T) {
			client := contractClient(t, "go-cache-"+fault, "jms-pam")
			client.http.Timeout = 300 * time.Millisecond
			selector := CredentialSelector{Key: "cache-" + fault}
			live, err := client.GetCredential(context.Background(), selector)
			if err != nil || live.FromLocal {
				t.Fatalf("Live fetch failed: %v", err)
			}
			cached, err := client.GetCredential(context.Background(), selector)
			temporary := fault == "503" || fault == "timeout"
			if temporary {
				if err != nil || !cached.FromLocal || cached.Account.Secret != live.Account.Secret {
					t.Fatalf("Cache fallback failed: %v", err)
				}
				if _, err := client.GetCredentialFresh(context.Background(), selector); err == nil {
					t.Fatal("Fresh fetch used cache")
				}
			} else if err == nil {
				t.Fatal("Non-transient failure used cache")
			}
			if fault == "401" || fault == "403" || fault == "404" || fault == "426" || fault == "revoked" {
				if len(client.latestCredentials) != 0 {
					t.Fatal("Denied cache retained")
				}
			}
		})
	}
}

func TestLatestCredentialRetentionRevocationAndClone(t *testing.T) {
	for _, change := range []string{"retain", "revoked", "scope", "configuration"} {
		t.Run(change, func(t *testing.T) {
			client := contractClient(t, "go-latest-"+change, "jms-pam")
			selector := CredentialSelector{Key: "cache-503"}
			if _, err := client.GetCredential(context.Background(), selector); err != nil {
				t.Fatal(err)
			}
			switch change {
			case "revoked":
				client.reconcileLatestCredentials(Event{Event: "credential.revoked"})
			case "scope":
				client.reconcileLatestCredentials(Event{Event: "snapshot"})
			case "configuration":
				client.reconcileLatestCredentials(Event{Event: "configuration.updated"})
			}
			retained, err := client.GetCredential(context.Background(), selector)
			if change == "retain" || change == "configuration" {
				if err != nil || !retained.FromLocal {
					t.Fatalf("Latest credential lost: %v", err)
				}
			} else if err == nil {
				t.Fatal("Revoked credential used")
			}
			clone, err := client.Clone()
			if err != nil {
				t.Fatal(err)
			}
			defer clone.Close()
			if len(clone.latestCredentials) != 0 {
				t.Fatal("Clone inherited retained credentials")
			}
		})
	}
}

func TestPolicyRevocationPreservesIndependentAccountPull(t *testing.T) {
	client := contractClient(t, "go-revoked-alias", "jms-pam")
	value := Credential{Key: "policy:account", Account: Account{ID: "account"}}
	client.latestCredentials[CredentialSelector{Key: value.Key}] = value
	client.latestCredentials[CredentialSelector{AccountID: "account"}] = Credential{Key: "account:account", Account: Account{ID: "account"}}
	client.latestCredentials[CredentialSelector{Key: "other"}] = Credential{Key: "other"}
	client.reconcileLatestCredentials(Event{Event: "credential.revoked", CredentialKey: "policy"})
	if len(client.latestCredentials) != 2 || client.latestCredentials[CredentialSelector{Key: "other"}].Key != "other" ||
		client.latestCredentials[CredentialSelector{AccountID: "account"}].Account.ID != "account" {
		t.Fatal("Policy revocation did not remove the push key or cleared independent pull")
	}
}

func TestPushSnapshotDoesNotRevokeIndependentPullCache(t *testing.T) {
	client := contractClient(t, "go-pull-snapshot", "jms-pam")
	value := Credential{Key: "account:account", Account: Account{ID: "account"}}
	client.latestCredentials[CredentialSelector{Key: value.Key}] = value
	client.latestCredentials[CredentialSelector{AccountID: "account"}] = value
	client.reconcileLatestCredentials(Event{Event: "snapshot", Credentials: []Event{}})
	if _, exists := client.latestCredentials[CredentialSelector{Key: value.Key}]; exists {
		t.Fatal("revoked push credential remains cached")
	}
	if _, exists := client.latestCredentials[CredentialSelector{AccountID: "account"}]; !exists {
		t.Fatal("push snapshot revoked application pull access")
	}
}

func TestManagedEventsReconnectAndSelfClose(t *testing.T) {
	client := contractClient(t, "hooks-go", "jms-pam")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	var revisions []int64
	var failures []error
	err := client.WatchEvents(ctx, EventHandlers{
		OnCredentialChanged: func(ctx context.Context, c Credential) error {
			if c.FromLocal {
				t.Error("Managed handler received cached data")
			}
			revisions = append(revisions, c.Revision)
			if c.Revision >= 3 {
				client.Close()
			}
			return nil
		},
		OnError: func(ctx context.Context, err error, event *Event) { failures = append(failures, err) },
	})
	if !errors.Is(err, context.Canceled) || len(revisions) < 2 || revisions[len(revisions)-1] != 3 || len(failures) != 0 {
		t.Fatalf("Managed reconnect failed: %v, %v, %v", err, revisions, failures)
	}
}

func TestManagedRetryWithoutNewEvent(t *testing.T) {
	client := contractClient(t, "retry-go", "jms-pam")
	ctx, cancel := context.WithTimeout(context.Background(), 4*time.Second)
	defer cancel()
	calls, reports := 0, 0
	err := client.WatchEvents(ctx, EventHandlers{
		OnCredentialChanged: func(ctx context.Context, c Credential) error {
			calls++
			if calls == 1 {
				return errors.New("temporary business failure")
			}
			cancel()
			return nil
		},
		OnError: func(context.Context, error, *Event) { reports++ },
	})
	if !errors.Is(err, context.Canceled) || calls != 2 || reports != 1 {
		t.Fatalf("Retry failed: %v, %d, %d", err, calls, reports)
	}
}

func TestSlowManagedHandlerKeepsReadingAndStops(t *testing.T) {
	client := contractClient(t, "hooks-go-slow", "jms-pam")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	entered, release := make(chan struct{}), make(chan struct{})
	watcher, err := client.StartEvents(ctx, EventHandlers{
		OnCredentialChanged: func(ctx context.Context, c Credential) error {
			select {
			case <-entered:
			default:
				close(entered)
			}
			select {
			case <-release:
			case <-ctx.Done():
			}
			return nil
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	defer func() { watcher.Stop(); close(release); watcher.Wait() }()
	select {
	case <-entered:
	case <-ctx.Done():
		t.Fatal("Handler did not start")
	}
	if _, err = client.StartEvents(ctx, EventHandlers{}); err == nil {
		t.Fatal("Duplicate listener accepted")
	}
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		response, err := http.Get(strings.TrimSuffix(os.Getenv("JMS_TEST_ENDPOINT"), "/prefix") + "/__stats")
		if err != nil {
			t.Fatal(err)
		}
		var stats struct {
			Connections map[string]int `json:"connections"`
		}
		err = json.NewDecoder(response.Body).Decode(&stats)
		response.Body.Close()
		if err != nil {
			t.Fatal(err)
		}
		if stats.Connections["hooks-go-slow"] >= 2 {
			return
		}
		time.Sleep(25 * time.Millisecond)
	}
	t.Fatal("Reader waited for the business handler")
}

func TestManagedRejectsOutdatedRevision(t *testing.T) {
	client := contractClient(t, "go-stale", "jms-pam")
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	watcher := &EventWatcher{client: client, ctx: ctx, cancel: cancel, pending: make(map[CredentialSelector]pendingCredential)}
	called := false
	watcher.handlers = EventHandlers{OnCredentialChanged: func(context.Context, Credential) error { called = true; return nil }, OnError: func(context.Context, error, *Event) {}}
	watcher.dispatch(Event{Event: "credential.updated", CredentialMode: "alternating_rotation", Key: "db", Revision: 3})
	if called || len(watcher.pending) != 1 {
		t.Fatal("Outdated credential was applied")
	}
	watcher.dispatch(Event{Event: "credential.updated", CredentialMode: "alternating_rotation", Key: "db", Revision: 2})
	if called || watcher.pending[CredentialSelector{Key: "db"}].update.Revision != 3 {
		t.Fatal("An older event cancelled the newer revision retry")
	}
}
