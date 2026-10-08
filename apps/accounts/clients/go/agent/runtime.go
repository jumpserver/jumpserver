package agent

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"log"
	"os"
	"path/filepath"
	"slices"
	"sort"
	"strings"
	"sync"
	"time"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

// Remote is implemented by the signed Go SDK; tests can replace the transport.
type Remote interface {
	ListAuthorizedAccounts(context.Context) ([]pam.AuthorizedAccount, error)
	SyncAgent(context.Context, pam.AgentSyncOptions) (pam.AgentSync, error)
	GetCredentialFresh(context.Context, pam.CredentialSelector) (pam.Credential, error)
	WatchCredentialEvents(context.Context, func(pam.Event) error) error
	ConfirmCredential(context.Context, string, int64, string) (pam.CredentialConfirmation, error)
	ListApplicationCommands(context.Context) ([]pam.Event, error)
	ReportApplicationCommandResult(context.Context, string, string, string) (pam.CommandResult, error)
}

type Applied struct {
	Key       string `json:"key"`
	Revision  int64  `json:"revision"`
	AccountID string `json:"account_id"`
	Confirmed bool   `json:"confirmed"`
}

type State struct {
	Identity          string                `json:"identity"`
	LocalDeliveryHash string                `json:"local_delivery_hash"`
	Latest            map[string]Credential `json:"credentials"`
	Delivered         map[string]int64      `json:"delivered"`
	Applied           map[string]Applied    `json:"applied"`
	Authorized        map[string]bool       `json:"authorized"`
	Wanted            map[string]int64      `json:"wanted_revisions"`
	Commands          map[string]pam.Event  `json:"pending_commands"`
	Scope             pam.AgentScope        `json:"scope"`
	Digest            string                `json:"config_digest"`
	Denied            bool                  `json:"access_denied"`
	Status            string                `json:"sync_status"`
}

type Agent struct {
	Config  Config
	remote  Remote
	mu      sync.Mutex
	syncMu  sync.Mutex
	state   State
	deliver func(context.Context, Config, map[string]Credential, map[string]bool) error
}

func New(config Config, remote Remote) (*Agent, error) {
	if err := config.Validate(); err != nil {
		return nil, err
	}
	state := State{Latest: map[string]Credential{}, Delivered: map[string]int64{}, Applied: map[string]Applied{}, Authorized: map[string]bool{}, Wanted: map[string]int64{}, Commands: map[string]pam.Event{}}
	identity, _ := json.Marshal([]string{config.Endpoint, config.AppID, config.OrgID, config.InstanceID})
	if config.Local {
		identity = append(identity, []byte("local")...)
	}
	digest := sha256.Sum256(identity)
	expectedIdentity := hex.EncodeToString(digest[:])
	state.Identity = expectedIdentity
	localDelivery, _ := json.Marshal(struct {
		Delivery DeliveryConfiguration
		Rules    []Rule
	}{config.Delivery, config.Rules})
	localDigest := sha256.Sum256(localDelivery)
	expectedLocalHash := hex.EncodeToString(localDigest[:])
	state.LocalDeliveryHash = expectedLocalHash
	if _, err := os.Stat(config.StateFile); err == nil {
		if err = privateFile(config.StateFile); err != nil {
			return nil, err
		}
		raw, err := os.ReadFile(config.StateFile)
		if err != nil {
			return nil, err
		}
		if err = json.Unmarshal(raw, &state); err != nil {
			return nil, errors.New("invalid retained Agent state")
		}
	} else if !os.IsNotExist(err) {
		return nil, err
	}
	if state.Identity != expectedIdentity {
		return nil, errors.New("retained Agent state belongs to another identity or instance")
	}
	if state.Latest == nil {
		state.Latest = map[string]Credential{}
	}
	if state.Delivered == nil {
		state.Delivered = map[string]int64{}
	}
	if state.Applied == nil {
		state.Applied = map[string]Applied{}
	}
	if state.Authorized == nil {
		state.Authorized = map[string]bool{}
	}
	if state.Wanted == nil {
		state.Wanted = map[string]int64{}
	}
	if state.Commands == nil {
		state.Commands = map[string]pam.Event{}
	}
	if state.LocalDeliveryHash != expectedLocalHash {
		state.Delivered = map[string]int64{}
		state.LocalDeliveryHash = expectedLocalHash
	}
	if err := validateScope(state.Scope); err != nil {
		return nil, err
	}
	return &Agent{Config: config, remote: remote, state: state, deliver: Deliver}, nil
}

func (a *Agent) persist() error { return writeJSON(a.Config.StateFile, a.state) }

func denied(err error) bool {
	var failure *pam.PAMError
	return errors.As(err, &failure) && (failure.StatusCode == 401 || failure.StatusCode == 403 || failure.StatusCode == 404 || failure.StatusCode == 426 || failure.Code == "client_upgrade_required")
}

func (a *Agent) failure(err error, identity bool) error {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.state.Status = "error"
	if identity && denied(err) {
		a.state.Denied = true
	}
	if persistence := a.persist(); persistence != nil {
		return persistence
	}
	return err
}

func (a *Agent) LocalCredential(key string) (Credential, error) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.state.Denied {
		return Credential{}, errors.New("agent_access_denied")
	}
	if !a.state.Authorized[key] {
		return Credential{}, errors.New("credential_not_authorized")
	}
	value, found := a.state.Latest[key]
	if !found {
		return value, errors.New("credential_not_available")
	}
	return value, nil
}

func (a *Agent) Health() map[string]string {
	a.mu.Lock()
	defer a.mu.Unlock()
	status := "ok"
	if a.state.Denied {
		status = "denied"
	}
	return map[string]string{"status": status, "sync_status": a.state.Status}
}

// HandleEvent reduces local authorization before any HTTP work. A failed refresh
// preserves the latest password and its required revision for later retries.
func (a *Agent) HandleEvent(ctx context.Context, event pam.Event) error {
	a.syncMu.Lock()
	defer a.syncMu.Unlock()
	if event.CommandID != "" {
		return errors.Join(a.recordEvent("received", event), a.command(ctx, event))
	}
	switch event.Event {
	case "snapshot", "credential.revoked", "credential.updated", "configuration.updated":
	default:
		return a.recordEvent("received", event)
	}
	a.mu.Lock()
	switch event.Event {
	case "snapshot":
		scope := map[string]bool{}
		for _, item := range event.Credentials {
			key := eventKey(item)
			scope[key] = true
			if item.Revision > a.state.Wanted[key] {
				a.state.Wanted[key] = item.Revision
			}
		}
		for key := range a.state.Authorized {
			if !scope[key] {
				delete(a.state.Authorized, key)
				delete(a.state.Wanted, key)
			}
		}
	case "credential.revoked":
		key := eventKey(event)
		for candidate := range a.state.Authorized {
			if (key == "" && event.AccountID == "") || (key != "" && (candidate == key || strings.HasPrefix(candidate, key+":"))) ||
				(event.AccountID != "" && (key == "" || strings.HasPrefix(key, "account:")) && a.state.Latest[candidate].AccountID == event.AccountID) {
				delete(a.state.Authorized, candidate)
				delete(a.state.Wanted, candidate)
			}
		}
	case "credential.updated":
		key := eventKey(event)
		if key != "" && event.Revision >= a.state.Wanted[key] {
			a.state.Wanted[key] = event.Revision
		}
	}
	err := a.persist()
	a.mu.Unlock()
	if err != nil {
		return err
	}
	return errors.Join(a.recordEvent("received", event), a.synchronize(ctx))
}
func eventKey(event pam.Event) string {
	key := event.Key
	if event.CredentialKey != "" {
		key = event.CredentialKey
	}
	if event.CredentialMode == "subscription" && event.AccountID != "" && !strings.Contains(key, ":") && key != "" {
		return key + ":" + event.AccountID
	}
	return key
}

func (a *Agent) Sync(ctx context.Context) error {
	a.syncMu.Lock()
	defer a.syncMu.Unlock()
	return a.synchronize(ctx)
}

func (a *Agent) synchronize(ctx context.Context) error {
	a.mu.Lock()
	legacyConfirmationKeys := append([]string(nil), a.state.Scope.ConfirmationKeys...)
	options := pam.AgentSyncOptions{ConfigDigest: a.state.Digest, SyncStatus: a.state.Status, DeliveryScope: a.Config.DeliveryScope(), RestartSupported: a.Config.Delivery.Mode == "environment" && a.Config.Delivery.Operation == "restart"}
	for key, value := range a.state.Latest {
		options.Credentials = append(options.Credentials, pam.KnownRevision{Key: key, Revision: value.Revision})
	}
	for key, revision := range a.state.Delivered {
		if a.state.Authorized[key] {
			options.DeliveredCredentials = append(options.DeliveredCredentials, pam.KnownRevision{Key: key, Revision: revision})
		}
	}
	a.mu.Unlock()
	response, err := a.remote.SyncAgent(ctx, options)
	if err != nil {
		return a.failure(err, true)
	}
	metadata := map[string]pam.CredentialRevision{}
	for _, item := range response.Credentials {
		if !validKey(item.Key) {
			return a.failure(errors.New("invalid credential metadata key"), false)
		}
		if err := validateAccountSwitch(item.AccountSwitch, ""); err != nil {
			return a.failure(err, false)
		}
		metadata[item.Key] = item
	}
	// Signed scope reductions apply even when the delivery configuration is invalid.
	a.mu.Lock()
	for key := range a.state.Authorized {
		if item, ok := metadata[key]; !ok || !item.Available {
			delete(a.state.Authorized, key)
			delete(a.state.Wanted, key)
		}
	}
	a.mu.Unlock()
	if err := validateScope(response.Scope); err != nil {
		return a.failure(err, false)
	}
	for key := range metadata {
		if !contains(response.Scope.Keys, key) {
			return a.failure(errors.New("credential metadata exceeds authorized scope"), false)
		}
	}
	a.mu.Lock()
	a.state.Scope = response.Scope
	wasDenied := a.state.Denied
	a.state.Denied = false
	for key, item := range metadata {
		if item.Available && (wasDenied || !a.state.Authorized[key]) {
			delete(a.state.Authorized, key)
			if current, wanted := a.state.Wanted[key]; !wanted || current < item.Revision {
				a.state.Wanted[key] = item.Revision
			}
		}
	}
	err = a.persist()
	a.mu.Unlock()
	if err != nil {
		return err
	}
	fetchFailed := false
	for key, item := range metadata {
		if !item.Available {
			continue
		}
		a.mu.Lock()
		previous, exists := a.state.Latest[key]
		expected, wanted := a.state.Wanted[key]
		a.mu.Unlock()
		if item.Revision > expected {
			expected = item.Revision
		}
		if exists && !item.Changed && !wanted && previous.Revision == item.Revision && sameSwitch(previous.AccountSwitch, item.AccountSwitch) {
			continue
		}
		value, fetchErr := a.remote.GetCredentialFresh(ctx, pam.CredentialSelector{Key: key})
		if fetchErr != nil {
			var failure *pam.PAMError
			isPAM := errors.As(fetchErr, &failure)
			revoked := isPAM && (failure.StatusCode == 400 || failure.StatusCode == 403 || failure.StatusCode == 404) && (failure.Code == "credential_not_found" || failure.Code == "credential_not_selected" || failure.Code == "credential_not_authorized" || failure.Code == "credential_not_bound")
			if isPAM && (failure.StatusCode == 401 || failure.StatusCode == 426 || (failure.StatusCode == 403 && !revoked) || failure.Code == "client_upgrade_required") {
				return a.failure(fetchErr, true)
			}
			if revoked || denied(fetchErr) {
				a.mu.Lock()
				delete(a.state.Authorized, key)
				delete(a.state.Wanted, key)
				err = a.persist()
				a.mu.Unlock()
				if err != nil {
					return err
				}
			}
			fetchFailed = true
			continue
		}
		if value.Key != key || value.Revision < expected || value.Revision < previous.Revision ||
			!sameSwitch(value.AccountSwitch, item.AccountSwitch) || validateAccountSwitch(value.AccountSwitch, value.Account.ID) != nil {
			fetchFailed = true
			continue
		}
		a.mu.Lock()
		if previous.AccountID != value.Account.ID || !sameSwitch(previous.AccountSwitch, value.AccountSwitch) {
			delete(a.state.Delivered, key)
		}
		a.state.Latest[key] = flatten(value)
		a.state.Authorized[key] = true
		delete(a.state.Wanted, key)
		if value.Revision > item.Revision {
			fetchFailed = true
		}
		err = a.persist()
		a.mu.Unlock()
		if err != nil {
			return err
		}
		if err = a.recordEvent("saved", pam.Event{Event: "credential.fetched", CredentialKey: key, Revision: value.Revision, AccountID: value.Account.ID}); err != nil {
			return err
		}
	}
	a.mu.Lock()
	latest := map[string]Credential{}
	changed := map[string]bool{}
	for key, item := range metadata {
		value, ok := a.state.Latest[key]
		if a.state.Authorized[key] && item.Available && ok && value.Revision == item.Revision && value.Revision >= a.state.Wanted[key] {
			latest[key] = value
			revision, delivered := a.state.Delivered[key]
			if !delivered || revision != value.Revision {
				changed[key] = true
			}
		}
	}
	deliveryConfig := a.Config
	a.mu.Unlock()
	if len(changed) > 0 {
		if err = a.deliver(ctx, deliveryConfig, latest, changed); err != nil {
			return a.failure(err, false)
		}
		verified := autoConfirmKeys(deliveryConfig.Rules, latest, changed)
		a.mu.Lock()
		for key := range changed {
			a.state.Delivered[key] = latest[key].Revision
			if verified[key] && contains(a.state.Scope.ConfirmationKeys, key) {
				value := latest[key]
				previous := a.state.Applied[key]
				if previous.Revision != value.Revision || previous.AccountID != value.AccountID {
					a.state.Applied[key] = Applied{Key: key, Revision: value.Revision, AccountID: value.AccountID}
				}
			}
		}
		err = a.persist()
		a.mu.Unlock()
		if err != nil {
			return err
		}
		for _, key := range sortedKeys(latest) {
			if changed[key] {
				value := latest[key]
				if err = a.recordEvent("delivered", pam.Event{Event: "credential.delivered", CredentialKey: key, Revision: value.Revision, AccountID: value.AccountID}); err != nil {
					return err
				}
			}
		}
	}
	if fetchFailed {
		return a.failure(errors.New("credential refresh failed; retained latest credentials preserved"), false)
	}
	if err = a.removeLegacySubscriptions(metadata, legacyConfirmationKeys); err != nil {
		return a.failure(err, false)
	}
	a.mu.Lock()
	a.state.Digest = response.ConfigDigest
	a.state.Status = "success"
	err = a.persist()
	a.mu.Unlock()
	if err != nil {
		return err
	}
	return a.reportPending(ctx)
}

// Every destination for a key must explicitly verify application use before
// a completed delivery can also count as an applied rotation revision.
func autoConfirmKeys(rules []Rule, latest map[string]Credential, changed map[string]bool) map[string]bool {
	verified := map[string]bool{}
	for key := range changed {
		seen, ready := false, true
		for _, rule := range rules {
			_, matched, complete, err := resolveRule(rule, latest)
			if err != nil || !complete || !contains(matched, key) {
				continue
			}
			seen = true
			if rule.ApplicationCheck == nil || !rule.ApplicationCheck.ConfirmOnSuccess {
				ready = false
			}
		}
		verified[key] = seen && ready
	}
	return verified
}

func sameSwitch(a, b *pam.AccountSwitch) bool {
	if a == nil || b == nil {
		return a == nil && b == nil
	}
	return slices.Equal(a.AccountIDs, b.AccountIDs)
}

func validateAccountSwitch(value *pam.AccountSwitch, active string) error {
	if value == nil {
		return nil
	}
	if len(value.AccountIDs) < 2 {
		return errors.New("account switch requires at least two accounts")
	}
	seen := map[string]bool{}
	for _, id := range value.AccountIDs {
		if !validKey(id) || seen[id] {
			return errors.New("invalid account switch account_ids")
		}
		seen[id] = true
	}
	if active != "" && !seen[active] {
		return errors.New("active account is not in account switch")
	}
	return nil
}

// Retire pre-account-key subscription state after the signed scope and new
// delivery have succeeded. Only Agent-created default files can be identified
// safely; custom rule destinations remain under the local administrator's control.
func (a *Agent) removeLegacySubscriptions(metadata map[string]pam.CredentialRevision, legacyConfirmationKeys []string) error {
	a.mu.Lock()
	legacy := []string{}
	for key, value := range a.state.Latest {
		if _, current := metadata[key]; current || !validKey(key) || strings.HasPrefix(key, "account:") ||
			contains(legacyConfirmationKeys, key) || value.AccountID == "" ||
			!strings.HasSuffix(key, ":"+value.AccountID) {
			continue
		}
		legacy = append(legacy, key)
	}
	a.mu.Unlock()
	for _, key := range legacy {
		if len(a.Config.Rules) == 0 && a.Config.Delivery.Mode != "socket" {
			suffix := ".json"
			if a.Config.Delivery.Mode == "environment" {
				suffix = ".env"
			}
			path := filepath.Join(a.Config.Delivery.Root, defaultCredentialFilename(key, strings.TrimPrefix(suffix, ".")))
			if _, err := os.Lstat(path); err == nil {
				if err = secureTarget(path); err != nil {
					return err
				}
				if err = os.Remove(path); err != nil {
					return err
				}
			} else if !os.IsNotExist(err) {
				return err
			}
		}
	}
	if len(legacy) == 0 {
		return nil
	}
	a.mu.Lock()
	for _, key := range legacy {
		delete(a.state.Latest, key)
		delete(a.state.Delivered, key)
		delete(a.state.Applied, key)
		delete(a.state.Authorized, key)
		delete(a.state.Wanted, key)
	}
	err := a.persist()
	a.mu.Unlock()
	return err
}

func (a *Agent) Confirm(ctx context.Context, key string, revision int64) (Applied, error) {
	a.syncMu.Lock()
	defer a.syncMu.Unlock()
	a.mu.Lock()
	value, exists := a.state.Latest[key]
	if a.state.Denied || !a.state.Authorized[key] || !exists || value.Revision != revision || !contains(a.state.Scope.ConfirmationKeys, key) {
		a.mu.Unlock()
		return Applied{}, errors.New("confirm an authorized alternating-rotation revision actually applied by the application")
	}
	applied := Applied{Key: key, Revision: revision, AccountID: value.AccountID}
	a.state.Applied[key] = applied
	err := a.persist()
	a.mu.Unlock()
	if err != nil {
		return applied, err
	}
	_ = a.reportPending(ctx)
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.state.Applied[key], nil
}

func (a *Agent) reportPending(ctx context.Context) error {
	a.mu.Lock()
	var applied []Applied
	for key, value := range a.state.Applied {
		current := a.state.Latest[key]
		if !a.state.Denied && a.state.Authorized[key] && contains(a.state.Scope.ConfirmationKeys, key) && !value.Confirmed && current.Revision == value.Revision && current.AccountID == value.AccountID {
			applied = append(applied, value)
		}
	}
	a.mu.Unlock()
	for _, value := range applied {
		if _, err := a.remote.ConfirmCredential(ctx, value.Key, value.Revision, value.AccountID); err != nil {
			return a.failure(err, true)
		}
		a.mu.Lock()
		value.Confirmed = true
		a.state.Applied[value.Key] = value
		err := a.persist()
		a.mu.Unlock()
		if err != nil {
			return err
		}
	}
	a.mu.Lock()
	pending := make([]pam.Event, 0, len(a.state.Commands))
	for _, event := range a.state.Commands {
		pending = append(pending, event)
	}
	a.mu.Unlock()
	for _, event := range pending {
		if err := a.finishSwitch(ctx, event); err != nil {
			return err
		}
	}
	return nil
}

func (a *Agent) finishSwitch(ctx context.Context, event pam.Event) error {
	key := eventKey(event)
	a.mu.Lock()
	applied := a.state.Applied[key]
	latest := a.state.Latest[key]
	ready := !a.state.Denied && a.state.Authorized[key] && applied.Confirmed && applied.Revision == event.Revision && applied.AccountID == event.AccountID && latest.Revision == event.Revision && latest.AccountID == event.AccountID
	a.mu.Unlock()
	if !ready {
		return nil
	}
	if _, err := a.remote.ReportApplicationCommandResult(ctx, event.CommandID, "success", ""); err != nil {
		return err
	}
	a.mu.Lock()
	delete(a.state.Commands, event.CommandID)
	err := a.persist()
	a.mu.Unlock()
	return err
}

func (a *Agent) command(ctx context.Context, event pam.Event) error {
	claim, err := a.remote.ReportApplicationCommandResult(ctx, event.CommandID, "running", "")
	if err != nil {
		return a.failure(err, true)
	}
	if !claim.Accepted {
		if claim.Status == "running" && event.Event == "credential.switch.requested" {
			return a.finishSwitch(ctx, event)
		}
		return nil
	}
	switch event.Event {
	case "application.restart.requested":
		d := a.Config.Delivery
		if d.Mode != "environment" || d.Operation != "restart" {
			err = errors.New("application restart is not locally configured")
			break
		}
		err = execute(ctx, Action{Type: "systemd", Unit: d.Unit, Operation: "restart"}, Payload{})
		if err == nil {
			err = checkService(ctx, d.Unit)
		}
	case "credential.switch.requested":
		key := eventKey(event)
		a.mu.Lock()
		a.state.Wanted[key] = event.Revision
		a.mu.Unlock()
		err = a.synchronize(ctx)
		if err != nil {
			break
		}
		a.mu.Lock()
		current, ok := a.state.Latest[key]
		authorized := a.state.Authorized[key]
		a.mu.Unlock()
		if !ok || !authorized || current.Revision != event.Revision || current.AccountID != event.AccountID {
			err = errors.New("requested account version is superseded")
			break
		}
		a.mu.Lock()
		a.state.Commands[event.CommandID] = event
		err = a.persist()
		a.mu.Unlock()
		if err == nil {
			return a.finishSwitch(ctx, event)
		}
	default:
		err = errors.New("unsupported application command")
	}
	if err != nil {
		_, _ = a.remote.ReportApplicationCommandResult(ctx, event.CommandID, "failed", "execution_failed")
		return err
	}
	_, err = a.remote.ReportApplicationCommandResult(ctx, event.CommandID, "success", "")
	return err
}

func (a *Agent) pollCommands(ctx context.Context) error {
	commands, err := a.remote.ListApplicationCommands(ctx)
	if err != nil {
		return a.failure(err, true)
	}
	var result error
	for _, event := range commands {
		a.syncMu.Lock()
		err = a.command(ctx, event)
		a.syncMu.Unlock()
		if err != nil {
			result = errors.New("one or more application commands failed")
		}
	}
	return result
}

func (a *Agent) Run(ctx context.Context) error {
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	server, err := a.startServer()
	if err != nil {
		return err
	}
	defer server.Close()
	events := make(chan pam.Event, 128)
	readerDone := make(chan error, 1)
	go func() {
		readerDone <- a.remote.WatchCredentialEvents(ctx, func(event pam.Event) error {
			select {
			case events <- event:
				return nil
			case <-ctx.Done():
				return ctx.Err()
			}
		})
	}()
	defer func() { cancel(); <-readerDone }()
	interval := time.Duration(a.Config.ReconcileSeconds) * time.Second
	timer := time.NewTimer(0)
	defer timer.Stop()
	delay := time.Second
	schedule := func(err error) {
		next := interval
		if err != nil {
			log.Printf("Agent synchronization or delivery failed: %T", err)
			next = delay
			delay *= 2
			if delay > 30*time.Second {
				delay = 30 * time.Second
			}
		} else {
			delay = time.Second
		}
		if !timer.Stop() {
			select {
			case <-timer.C:
			default:
			}
		}
		timer.Reset(next)
	}
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case event := <-events:
			schedule(a.HandleEvent(ctx, event))
		case <-timer.C:
			err := a.Sync(ctx)
			if err == nil {
				err = a.pollCommands(ctx)
			}
			schedule(err)
		}
	}
}

func sortedKeys(values map[string]Credential) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}
