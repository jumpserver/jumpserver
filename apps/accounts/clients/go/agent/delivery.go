package agent

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"text/template"
	"time"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

type Credential struct {
	Key           string             `json:"key"`
	Revision      int64              `json:"revision"`
	AssetID       string             `json:"asset_id"`
	Asset         string             `json:"asset"`
	Address       string             `json:"address"`
	AccountID     string             `json:"account_id"`
	Account       string             `json:"account"`
	Username      string             `json:"username"`
	SecretType    string             `json:"secret_type"`
	Secret        string             `json:"secret"`
	AccountSwitch *pam.AccountSwitch `json:"account_switch,omitempty"`
}

func (c Credential) String() string {
	return "Credential{Key:" + strconv.Quote(c.Key) + " Secret:[REDACTED]}"
}
func (c Credential) GoString() string { return c.String() }
func flatten(c pam.Credential) Credential {
	return Credential{Key: c.Key, Revision: c.Revision, AssetID: c.Asset.ID, Asset: c.Asset.Name, Address: c.Asset.Address, AccountID: c.Account.ID, Account: c.Account.Name, Username: c.Account.Username, SecretType: c.Account.SecretType, Secret: c.Account.Secret, AccountSwitch: c.AccountSwitch}
}

type Payload struct {
	Event       string                `json:"event"`
	Credentials map[string]Credential `json:"credentials"`
}

// Rule payload keys are the administrator's selectors. For an account rule the
// selector stays A even when the server selects B as the current account.
func resolveRule(rule Rule, latest map[string]Credential) (Payload, []string, bool, error) {
	payload := Payload{Event: "credentials.updated", Credentials: map[string]Credential{}}
	matched := []string{}
	complete := true
	selectors := make([]AccountSelector, 0, len(rule.Keys)+len(rule.Accounts))
	for _, key := range rule.Keys {
		selectors = append(selectors, AccountSelector{AccountID: key})
	}
	selectors = append(selectors, rule.Accounts...)
	for _, account := range selectors {
		selector := account.AccountID
		if len(rule.Keys) > 0 {
			value, ok := latest[selector]
			if !ok {
				complete = false
				continue
			}
			payload.Credentials[selector] = value
			matched = append(matched, selector)
			continue
		}
		candidate := ""
		for key, value := range latest {
			matches := value.AccountID == selector
			if account.AllowAccountSwitch {
				matches = value.AccountSwitch != nil && contains(value.AccountSwitch.AccountIDs, selector)
			}
			if !matches {
				continue
			}
			if candidate != "" {
				return Payload{}, nil, false, errors.New("account rule matches multiple credentials")
			}
			candidate = key
			payload.Credentials[selector] = value
		}
		if candidate == "" {
			complete = false
			continue
		}
		if contains(matched, candidate) {
			return Payload{}, nil, false, errors.New("one rotating credential matches multiple account selectors")
		}
		matched = append(matched, candidate)
	}
	return payload, matched, complete, nil
}

func environment(c Credential) ([]byte, error) {
	values := []struct {
		name  string
		value string
	}{
		{"JMS_PAM_CREDENTIAL_KEY", c.Key}, {"JMS_PAM_CREDENTIAL_REVISION", strconv.FormatInt(c.Revision, 10)},
		{"JMS_PAM_ASSET_ID", c.AssetID}, {"JMS_PAM_ASSET_ADDRESS", c.Address}, {"JMS_PAM_ACCOUNT_ID", c.AccountID},
		{"JMS_PAM_USERNAME", c.Username}, {"JMS_PAM_SECRET_TYPE", c.SecretType}, {"JMS_PAM_SECRET", c.Secret},
	}
	var out strings.Builder
	for _, item := range values {
		if strings.ContainsAny(item.value, "\x00\r\n") {
			return nil, errors.New("EnvironmentFile values cannot contain NUL or newlines")
		}
		out.WriteString(item.name + "=\"")
		out.WriteString(strings.NewReplacer("\\", "\\\\", "\"", "\\\"", "`", "\\`", "$", "\\$").Replace(item.value))
		out.WriteString("\"\n")
	}
	return []byte(out.String()), nil
}

func render(file File, payload Payload) ([]byte, error) {
	switch file.format() {
	case "json":
		if len(payload.Credentials) == 1 {
			for _, value := range payload.Credentials {
				return json.MarshalIndent(value, "", "  ")
			}
		}
		return json.MarshalIndent(payload.Credentials, "", "  ")
	case "environment":
		if len(payload.Credentials) != 1 {
			return nil, errors.New("EnvironmentFile requires one credential")
		}
		for _, value := range payload.Credentials {
			return environment(value)
		}
	case "template":
		if err := securePath(file.Template); err != nil {
			return nil, err
		}
		raw, err := os.ReadFile(file.Template)
		if err != nil {
			return nil, err
		}
		functions := template.FuncMap{"json": func(value any) (string, error) { data, err := json.Marshal(value); return string(data), err }}
		source, err := template.New("config").Option("missingkey=error").Funcs(functions).Parse(string(raw))
		if err != nil {
			return nil, errors.New("invalid local configuration template")
		}
		var buffer bytes.Buffer
		if err = source.Execute(&buffer, payload); err != nil {
			return nil, errors.New("configuration template rendering failed")
		}
		return buffer.Bytes(), nil
	}
	return nil, errors.New("unsupported file format")
}

// execute never invokes a shell or logs script output. Scripts must complete only
// after validating and applying their update; cancellation kills their process group.
func execute(ctx context.Context, action Action, payload Payload) error {
	if err := action.Validate(); err != nil {
		return err
	}
	var path string
	var args []string
	if action.kind() == "script" {
		if err := securePath(action.Path); err != nil {
			return err
		}
		info, err := os.Lstat(action.Path)
		if err != nil {
			return err
		}
		if err := validateExecutable(action.Path, info); err != nil {
			return err
		}
		path, args = action.Path, action.Args
	} else {
		path = "/usr/bin/systemctl"
		args = []string{action.operation(), action.Unit}
	}
	bounded, cancel := context.WithTimeout(ctx, action.timeout())
	defer cancel()
	command := exec.CommandContext(bounded, path, args...)
	prepareActionProcess(command)
	command.WaitDelay = 2 * time.Second
	raw, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	command.Stdin = bytes.NewReader(raw)
	if err = command.Run(); err != nil {
		return errors.New("credential action failed or timed out")
	}
	if action.kind() == "systemd" {
		return checkService(ctx, action.Unit)
	}
	return nil
}

// Deliver renders every file before mutation. Delivered revisions are recorded
// only after all writes and actions succeed. Retried actions must be idempotent.
func Deliver(ctx context.Context, config Config, latest map[string]Credential, changed map[string]bool) error {
	rules := config.Rules
	if len(rules) == 0 {
		for key := range changed {
			if config.Delivery.Mode == "socket" {
				continue
			}
			suffix, format := "json", "json"
			if config.Delivery.Mode == "environment" {
				suffix, format = "env", "environment"
			}
			rules = append(rules, Rule{Keys: []string{key}, Files: []File{{Path: filepath.Join(config.Delivery.Root, defaultCredentialFilename(key, suffix)), Format: format, Owner: config.Delivery.User}}})
		}
		if config.Delivery.Mode == "environment" && len(changed) > 0 {
			rules = append(rules, Rule{Keys: mapKeys(changed), Action: &Action{Type: "systemd", Unit: config.Delivery.Unit, Operation: config.Delivery.Operation}})
		}
	}
	type write struct {
		file     File
		data     []byte
		preserve bool
		mode     os.FileMode
		uid, gid int
		mapping  *ConfigUpdate
		account  AccountSelector
	}
	type job struct {
		writes           []write
		backupTargets    []string
		credentialCheck  *Action
		updateScript     *Action
		serviceAction    *Action
		applicationCheck *ApplicationCheck
		payload          Payload
	}
	var jobs []job
	covered := map[string]bool{}
	for _, rule := range rules {
		payload, matched, complete, err := resolveRule(rule, latest)
		if err != nil {
			return err
		}
		relevant := false
		for _, key := range matched {
			relevant = relevant || changed[key]
		}
		if !relevant {
			continue
		}
		if !complete {
			return errors.New("delivery rule references an unavailable credential")
		}
		item := job{serviceAction: rule.Action, credentialCheck: rule.CredentialCheck, applicationCheck: rule.ApplicationCheck, payload: payload}
		files := rule.Files
		if rule.ConfigUpdate != nil {
			files = rule.ConfigUpdate.Files
			item.updateScript = rule.ConfigUpdate.Script
			item.backupTargets = append(item.backupTargets, rule.ConfigUpdate.targetPaths()...)
			if rule.ConfigUpdate.File != "" {
				data, mode, uid, gid, err := renderMappedConfig(*rule.ConfigUpdate, rule.Accounts[0], payload)
				if err != nil {
					return err
				}
				item.writes = append(item.writes, write{
					file: File{Path: rule.ConfigUpdate.File}, data: data,
					preserve: true, mode: mode, uid: uid, gid: gid,
					mapping: rule.ConfigUpdate, account: rule.Accounts[0],
				})
			}
			for _, path := range rule.ConfigUpdate.targetPaths() {
				if err := secureTarget(path); err != nil {
					return err
				}
			}
		}
		if rule.ServiceAction != nil {
			item.serviceAction = rule.ServiceAction
		}
		for _, file := range files {
			if err := secureTarget(file.Path); err != nil {
				return err
			}
			data, err := render(file, payload)
			if err != nil {
				return err
			}
			item.writes = append(item.writes, write{file: file, data: data})
		}
		for _, key := range matched {
			covered[key] = true
		}
		jobs = append(jobs, item)
	}
	if len(config.Rules) > 0 {
		for key := range changed {
			if !covered[key] {
				return errors.New("changed credential has no local delivery rule")
			}
		}
	}
	// Verify every candidate credential before changing any business file.
	for _, job := range jobs {
		if job.credentialCheck != nil {
			if err := execute(ctx, *job.credentialCheck, job.payload); err != nil {
				return fmt.Errorf("credential_check failed: %w", err)
			}
		}
	}
	// Preserve the original contents before any update script or file write.
	// One delivery can update the same file through several account rules.
	if len(config.Rules) > 0 {
		var targets []string
		for _, job := range jobs {
			targets = append(targets, job.backupTargets...)
			for _, item := range job.writes {
				targets = append(targets, item.file.Path)
			}
		}
		if err := backupTargets(config.StateFile, targets); err != nil {
			return fmt.Errorf("business configuration backup failed: %w", err)
		}
	}
	for _, job := range jobs {
		if job.updateScript != nil {
			if err := execute(ctx, *job.updateScript, job.payload); err != nil {
				return fmt.Errorf("config_update failed: %w", err)
			}
		}
	}
	for _, job := range jobs {
		for _, item := range job.writes {
			if item.mapping != nil {
				var err error
				item.data, item.mode, item.uid, item.gid, err = renderMappedConfig(*item.mapping, item.account, job.payload)
				if err != nil {
					return err
				}
			}
			if err := preparePrivateDirectory(filepath.Dir(item.file.Path), 0711); err != nil {
				return err
			}
			mode, uid, gid := os.FileMode(0600), item.uid, item.gid
			if item.preserve {
				mode = item.mode
			} else {
				owner := item.file.Owner
				if owner == "" {
					owner = config.Delivery.User
				}
				var err error
				uid, gid, err = ownerIDs(owner)
				if err != nil {
					return err
				}
			}
			if err := atomicWrite(item.file.Path, item.data, mode, uid, gid); err != nil {
				return err
			}
		}
	}
	for _, job := range jobs {
		if job.serviceAction != nil {
			if err := execute(ctx, *job.serviceAction, job.payload); err != nil {
				return fmt.Errorf("service_action failed: %w", err)
			}
		}
	}
	for _, job := range jobs {
		if job.applicationCheck != nil {
			if err := execute(ctx, job.applicationCheck.Action, job.payload); err != nil {
				return fmt.Errorf("application_check failed: %w", err)
			}
		}
	}
	return nil
}

func mapKeys(values map[string]bool) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	return keys
}
