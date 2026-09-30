package agent

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
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
	Key        string `json:"key"`
	Revision   int64  `json:"revision"`
	AssetID    string `json:"asset_id"`
	Asset      string `json:"asset"`
	Address    string `json:"address"`
	AccountID  string `json:"account_id"`
	Account    string `json:"account"`
	Username   string `json:"username"`
	SecretType string `json:"secret_type"`
	Secret     string `json:"secret"`
}

func (c Credential) String() string {
	return "Credential{Key:" + strconv.Quote(c.Key) + " Secret:[REDACTED]}"
}
func (c Credential) GoString() string { return c.String() }
func flatten(c pam.Credential) Credential {
	return Credential{c.Key, c.Revision, c.Asset.ID, c.Asset.Name, c.Asset.Address, c.Account.ID, c.Account.Name, c.Account.Username, c.Account.SecretType, c.Account.Secret}
}

type Payload struct {
	Event       string                `json:"event"`
	Credentials map[string]Credential `json:"credentials"`
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
	switch file.Format {
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
	if action.Type == "script" {
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
		args = []string{action.Operation, action.Unit}
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
	if action.Type == "systemd" {
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
		file File
		data []byte
	}
	type job struct {
		writes  []write
		action  *Action
		payload Payload
	}
	var jobs []job
	covered := map[string]bool{}
	for _, rule := range rules {
		relevant := false
		for _, key := range rule.Keys {
			relevant = relevant || changed[key]
		}
		if !relevant {
			continue
		}
		payload := Payload{Event: "credentials.updated", Credentials: map[string]Credential{}}
		for _, key := range rule.Keys {
			value, ok := latest[key]
			if !ok {
				return errors.New("delivery rule references an unavailable credential")
			}
			payload.Credentials[key] = value
		}
		item := job{action: rule.Action, payload: payload}
		for _, file := range rule.Files {
			if err := secureTarget(file.Path); err != nil {
				return err
			}
			data, err := render(file, payload)
			if err != nil {
				return err
			}
			item.writes = append(item.writes, write{file, data})
		}
		for _, key := range rule.Keys {
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
	for _, job := range jobs {
		for _, item := range job.writes {
			if err := preparePrivateDirectory(filepath.Dir(item.file.Path), 0711); err != nil {
				return err
			}
			owner := item.file.Owner
			if owner == "" {
				owner = config.Delivery.User
			}
			uid, gid, err := ownerIDs(owner)
			if err != nil {
				return err
			}
			if err = atomicWrite(item.file.Path, item.data, 0600, uid, gid); err != nil {
				return err
			}
		}
		if job.action != nil {
			if err := execute(ctx, *job.action, job.payload); err != nil {
				return err
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
