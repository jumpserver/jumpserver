// Package agent implements local credential delivery using the Go SDK.
package agent

import (
	"bytes"
	"encoding/json"
	"errors"
	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
	"io"
	"os"
	"os/user"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

const DefaultConfig = "/etc/jms-pam-agent/agent.json"
const ServiceName = "jms-pam-agent.service"
const DefaultState = "/var/lib/jms-pam-agent/state.json"
const DefaultEvent = "/var/lib/jms-pam-agent/events.jsonl"
const DefaultSocket = "/run/jms-pam-agent/agent.sock"

var unitPattern = regexp.MustCompile(`^[A-Za-z0-9_.@:-]+\.service$`)
var configFieldPattern = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]*$`)

type DeliveryConfiguration struct {
	Mode      string `json:"delivery_mode"`
	Root      string `json:"delivery_root"`
	Socket    string `json:"socket_path,omitempty"`
	User      string `json:"app_user"`
	Unit      string `json:"systemd_unit"`
	Operation string `json:"systemd_action"`
}

type File struct {
	Path     string `json:"path"`
	Format   string `json:"format,omitempty"`
	Template string `json:"template_file,omitempty"`
	Owner    string `json:"owner,omitempty"`
}

func (f File) format() string {
	if f.Format != "" {
		return f.Format
	}
	if f.Template != "" {
		return "template"
	}
	return "json"
}

type Action struct {
	Type           string   `json:"type,omitempty"`
	Unit           string   `json:"unit,omitempty"`
	Operation      string   `json:"operation,omitempty"`
	Path           string   `json:"path,omitempty"`
	Args           []string `json:"args,omitempty"`
	TimeoutSeconds int      `json:"timeout_seconds,omitempty"`
}

func (a Action) kind() string {
	if a.Type != "" {
		return a.Type
	}
	if a.Path != "" && a.Unit == "" {
		return "script"
	}
	if a.Unit != "" && a.Path == "" {
		return "systemd"
	}
	return ""
}

func (a Action) operation() string {
	if a.Operation == "" && a.kind() == "systemd" {
		return "restart"
	}
	return a.Operation
}

// ConfigUpdate edits declared fields, renders complete files, or runs a trusted
// local updater for business formats that need one.
type ConfigUpdate struct {
	File      string            `json:"file,omitempty"`
	Format    string            `json:"format,omitempty"`
	Owner     string            `json:"owner,omitempty"`
	FieldsMap map[string]string `json:"fields_map,omitempty"`
	Files     []File            `json:"files,omitempty"`
	Script    *Action           `json:"script,omitempty"`
	Target    string            `json:"target,omitempty"`
	Targets   []string          `json:"targets,omitempty"`
}

func (u ConfigUpdate) patchFormat() string {
	if u.Format != "" {
		return u.Format
	}
	switch strings.ToLower(filepath.Ext(u.File)) {
	case ".txt", ".env", ".properties":
		return "env"
	case ".yml", ".yaml":
		return "yaml"
	default:
		return ""
	}
}

func (u ConfigUpdate) targetPaths() []string {
	if u.Target != "" {
		return []string{u.Target}
	}
	return u.Targets
}

// An application check may opt into confirming an alternating rotation only
// after its trusted local script has verified the running application.
type ApplicationCheck struct {
	Action
	ConfirmOnSuccess bool `json:"confirm_on_success,omitempty"`
}

type AccountSelector struct {
	AccountID          string `json:"account_id"`
	AllowAccountSwitch bool   `json:"allow_account_switch,omitempty"`
}

// Rules and their file/script paths are trusted local configuration. Core cannot supply them.
type Rule struct {
	Keys             []string          `json:"keys,omitempty"`
	Accounts         []AccountSelector `json:"accounts,omitempty"`
	ConfigUpdate     *ConfigUpdate     `json:"config_update,omitempty"`
	CredentialCheck  *Action           `json:"credential_check,omitempty"`
	ServiceAction    *Action           `json:"service_action,omitempty"`
	ApplicationCheck *ApplicationCheck `json:"application_check,omitempty"`
	// Files and Action are retained for existing local configurations.
	Files  []File  `json:"files,omitempty"`
	Action *Action `json:"action,omitempty"`
}

type Config struct {
	// Local is chosen by the CLI for current-user foreground runs, never by Core.
	Local            bool                  `json:"-"`
	Endpoint         string                `json:"endpoint"`
	AppID            string                `json:"app_id"`
	AppSecret        string                `json:"app_secret"`
	OrgID            string                `json:"org_id"`
	InstanceID       string                `json:"instance_id"`
	StateFile        string                `json:"state_file,omitempty"`
	EventFile        string                `json:"event_file,omitempty"`
	ReconcileSeconds int                   `json:"reconcile_interval,omitempty"`
	Delivery         DeliveryConfiguration `json:"delivery"`
	Rules            []Rule                `json:"rules,omitempty"`
}

func LoadConfig(path string) (Config, error) {
	var config Config
	config, err := loadBootstrapConfig(path)
	if err != nil {
		return config, err
	}
	return config, config.Validate()
}

// The wizard's bootstrap carries Linux delivery defaults. Local preparation
// replaces them before validating platform-specific paths and capabilities.
func loadBootstrapConfig(path string) (Config, error) {
	var config Config
	resolved, err := filepath.Abs(path)
	if err != nil {
		return config, errors.New("cannot resolve Agent configuration path")
	}
	if err := privateFile(resolved); err != nil {
		return config, err
	}
	raw, err := os.ReadFile(resolved)
	if err != nil {
		return config, err
	}
	config, err = decodeConfig(raw)
	if err != nil {
		return config, err
	}
	if config.StateFile == "" {
		config.StateFile = DefaultState
	}
	if config.EventFile == "" {
		config.EventFile = DefaultEvent
	}
	if config.ReconcileSeconds == 0 {
		config.ReconcileSeconds = 300
	}
	if config.Delivery.Socket == "" {
		config.Delivery.Socket = DefaultSocket
	}
	return config, nil
}

func (c Config) compactDefaults() Config {
	if c.StateFile == DefaultState {
		c.StateFile = ""
	}
	if c.EventFile == DefaultEvent {
		c.EventFile = ""
	}
	if c.ReconcileSeconds == 300 {
		c.ReconcileSeconds = 0
	}
	if c.Delivery.Socket == DefaultSocket {
		c.Delivery.Socket = ""
	}
	return c
}

func absolute(path string) bool {
	return filepath.IsAbs(path) && filepath.Clean(path) == path && filepath.Dir(path) != path && !strings.ContainsAny(path, "\x00\r\n")
}
func validKey(key string) bool {
	return key != "" && key != "." && key != ".." && !strings.ContainsAny(key, "/\\\x00\r\n")
}

func (c Config) Validate() error {
	if c.Endpoint == "" || c.AppID == "" || c.AppSecret == "" || c.InstanceID == "" || !absolute(c.StateFile) || c.ReconcileSeconds < 1 {
		return errors.New("identity, stable instance ID, state path and positive reconcile interval are required")
	}
	if err := validateDelivery(c.Delivery); err != nil {
		return err
	}
	if err := validateSocketPath(c.Delivery.Socket); err != nil {
		return err
	}
	if c.Local {
		account, err := user.Current()
		if err != nil || c.Delivery.User != account.Username || c.Delivery.Mode == "environment" || c.Delivery.Unit != "" {
			return errors.New("local mode requires the current user and file or socket delivery without systemd")
		}
	}
	if c.EventFile != "" && (!absolute(c.EventFile) || c.EventFile == c.StateFile || c.EventFile == c.Delivery.Socket || c.EventFile == c.Delivery.Root || strings.HasPrefix(c.EventFile, c.Delivery.Root+string(filepath.Separator))) {
		return errors.New("event_file must be separate from state, socket and credential files")
	}
	targets := map[string]bool{}
	type mappedTarget struct {
		format string
		owner  string
		fields map[string]bool
	}
	mappedTargets := map[string]mappedTarget{}
	for _, rule := range c.Rules {
		if (len(rule.Keys) == 0) == (len(rule.Accounts) == 0) {
			return errors.New("delivery rules require either keys or accounts")
		}
		modern := rule.ConfigUpdate != nil || rule.CredentialCheck != nil || rule.ServiceAction != nil || rule.ApplicationCheck != nil
		if modern && (len(rule.Files) > 0 || rule.Action != nil) {
			return errors.New("legacy files/action cannot be mixed with staged delivery blocks")
		}
		if !modern && len(rule.Files) == 0 && rule.Action == nil {
			return errors.New("delivery rules require files or an action")
		}
		if modern && rule.ConfigUpdate == nil && rule.ServiceAction == nil {
			return errors.New("staged delivery requires config_update or service_action")
		}
		keys := map[string]bool{}
		for _, key := range rule.Keys {
			if !validKey(key) || keys[key] {
				return errors.New("invalid or duplicate rule key")
			}
			keys[key] = true
		}
		for _, account := range rule.Accounts {
			if !validKey(account.AccountID) || keys[account.AccountID] {
				return errors.New("invalid or duplicate rule account_id")
			}
			keys[account.AccountID] = true
		}
		files := rule.Files
		if rule.ConfigUpdate != nil {
			update := rule.ConfigUpdate
			choices := 0
			if update.File != "" {
				choices++
			}
			if len(update.Files) > 0 {
				choices++
			}
			if update.Script != nil {
				choices++
			}
			if choices != 1 {
				return errors.New("config_update requires one file mapping, rendered files or script")
			}
			files = update.Files
			if update.File != "" {
				if !absolute(update.File) || (update.patchFormat() != "env" && update.patchFormat() != "yaml") || len(rule.Keys) > 0 || len(rule.Accounts) != 1 {
					return errors.New("file mapping requires an absolute env/YAML file and exactly one account selector")
				}
				if c.Local && update.Owner != "" && update.Owner != c.Delivery.User {
					return errors.New("local files must belong to the current user")
				}
			}
			if update.File == "" && (update.Format != "" || update.Owner != "" || update.FieldsMap != nil) {
				return errors.New("format, owner and fields_map require config_update.file")
			}
			if update.Script != nil && update.Script.kind() != "script" {
				return errors.New("config_update script must be a fixed local executable")
			}
			if update.Target != "" && len(update.Targets) > 0 {
				return errors.New("config_update accepts target or targets, not both")
			}
			if update.Script != nil && len(update.targetPaths()) == 0 {
				return errors.New("config_update scripts must declare their target paths")
			}
			if (len(files) > 0 || update.File != "") && len(update.targetPaths()) > 0 {
				return errors.New("config_update files already declare their target paths")
			}
			if update.File != "" {
				if len(update.FieldsMap) == 0 {
					return errors.New("file mapping requires fields_map")
				}
				for name, source := range update.FieldsMap {
					if !configFieldPattern.MatchString(name) || (source != "username" && source != "secret" && source != "account_id" && source != "revision") {
						return errors.New("invalid mapped configuration field")
					}
				}
			}
		}
		if rule.ConfigUpdate != nil {
			if path := rule.ConfigUpdate.File; path != "" {
				if path == c.StateFile || path == c.EventFile || path == c.Delivery.Socket || targets[path] {
					return errors.New("invalid config_update file")
				}
				update := rule.ConfigUpdate
				mapped, exists := mappedTargets[path]
				if exists && (mapped.format != update.patchFormat() || mapped.owner != update.Owner) {
					return errors.New("shared config_update file requires the same format and owner")
				}
				if !exists {
					mapped = mappedTarget{format: update.patchFormat(), owner: update.Owner, fields: map[string]bool{}}
				}
				for field := range update.FieldsMap {
					if mapped.fields[field] {
						return errors.New("shared config_update file has duplicate mapped fields")
					}
					mapped.fields[field] = true
				}
				mappedTargets[path] = mapped
			}
			for _, path := range rule.ConfigUpdate.targetPaths() {
				if !absolute(path) || path == c.StateFile || path == c.EventFile || path == c.Delivery.Socket || targets[path] || mappedTargets[path].fields != nil {
					return errors.New("invalid or duplicate config_update target path")
				}
				targets[path] = true
			}
		}
		for _, file := range files {
			format := file.format()
			if !absolute(file.Path) || file.Path == c.StateFile || file.Path == c.EventFile || file.Path == c.Delivery.Socket || (format != "json" && format != "environment" && format != "template") {
				return errors.New("invalid delivery file path or format")
			}
			if targets[file.Path] || mappedTargets[file.Path].fields != nil {
				return errors.New("a delivery target must belong to one rule")
			}
			targets[file.Path] = true
			if format == "environment" && len(rule.Keys)+len(rule.Accounts) != 1 {
				return errors.New("EnvironmentFile rules require exactly one selected credential")
			}
			if format == "template" && !absolute(file.Template) {
				return errors.New("templates require an absolute local template_file")
			}
			if c.Local && file.Owner != "" && file.Owner != c.Delivery.User {
				return errors.New("local files must belong to the current user")
			}
		}
		for _, action := range []*Action{rule.Action, rule.CredentialCheck, rule.ServiceAction} {
			if action == nil {
				continue
			}
			if c.Local && action.kind() == "systemd" {
				return errors.New("systemd actions require the Linux service")
			}
			if err := action.Validate(); err != nil {
				return err
			}
		}
		if rule.CredentialCheck != nil && rule.CredentialCheck.kind() != "script" {
			return errors.New("credential checks require fixed local scripts")
		}
		if rule.ApplicationCheck != nil {
			if rule.ApplicationCheck.kind() != "script" {
				return errors.New("application checks require fixed local scripts")
			}
			if err := rule.ApplicationCheck.Action.Validate(); err != nil {
				return err
			}
		}
		if rule.ConfigUpdate != nil && rule.ConfigUpdate.Script != nil {
			if err := rule.ConfigUpdate.Script.Validate(); err != nil {
				return err
			}
		}
	}
	return nil
}

// Local rules advertise which authorized credentials this instance can use.
// An empty rules list uses default delivery for every application binding.
func (c Config) DeliveryScope() *pam.DeliveryScope {
	if len(c.Rules) == 0 {
		return nil
	}
	keys, accounts := map[string]bool{}, map[string]bool{}
	for _, rule := range c.Rules {
		for _, key := range rule.Keys {
			keys[key] = true
		}
		for _, account := range rule.Accounts {
			accounts[account.AccountID] = true
		}
	}
	scope := &pam.DeliveryScope{Keys: make([]string, 0, len(keys)), AccountIDs: make([]string, 0, len(accounts))}
	for key := range keys {
		scope.Keys = append(scope.Keys, key)
	}
	for id := range accounts {
		scope.AccountIDs = append(scope.AccountIDs, id)
	}
	sort.Strings(scope.Keys)
	sort.Strings(scope.AccountIDs)
	return scope
}

func validateDelivery(d DeliveryConfiguration) error {
	if d.Mode != "json" && d.Mode != "environment" && d.Mode != "socket" {
		return errors.New("unsupported delivery mode")
	}
	if !absolute(d.Root) || !absolute(d.Socket) || filepath.Base(d.Socket) != "agent.sock" || d.User == "" {
		return errors.New("invalid delivery root, socket path or application user")
	}
	if d.Mode != "environment" && (d.Unit != "" || d.Operation != "") {
		return errors.New("use rules.service_action for JSON/socket service actions")
	}
	if d.Mode == "environment" && (!unitPattern.MatchString(d.Unit) || (d.Operation != "reload" && d.Operation != "restart")) {
		return errors.New("EnvironmentFile delivery requires a pinned systemd unit and action")
	}
	return nil
}

func (a Action) Validate() error {
	if a.TimeoutSeconds < 0 || a.TimeoutSeconds > 300 {
		return errors.New("action timeout must be between 1 and 300 seconds, or omitted")
	}
	switch a.kind() {
	case "systemd":
		if !unitPattern.MatchString(a.Unit) || (a.operation() != "reload" && a.operation() != "restart") || a.Path != "" || len(a.Args) != 0 {
			return errors.New("invalid systemd action")
		}
	case "script":
		if !absolute(a.Path) || a.Unit != "" || a.Operation != "" {
			return errors.New("script action requires one absolute local executable")
		}
		for _, arg := range a.Args {
			if strings.ContainsAny(arg, "\x00\r\n") {
				return errors.New("invalid fixed script argument")
			}
		}
	default:
		return errors.New("unsupported action type")
	}
	return nil
}

func (a Action) timeout() time.Duration {
	if a.TimeoutSeconds == 0 {
		return 120 * time.Second
	}
	return time.Duration(a.TimeoutSeconds) * time.Second
}

func decodeConfig(raw []byte) (Config, error) {
	var config Config
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&config); err != nil {
		return config, errors.New("invalid Agent configuration JSON or unknown field")
	}
	if decoder.Decode(new(any)) != io.EOF {
		return config, errors.New("Agent configuration must contain one JSON object")
	}
	return config, nil
}
func validateScope(scope pam.AgentScope) error {
	seen := map[string]bool{}
	for _, key := range scope.Keys {
		if !validKey(key) || seen[key] {
			return errors.New("invalid authorized scope")
		}
		seen[key] = true
	}
	for _, key := range scope.ConfirmationKeys {
		if !seen[key] {
			return errors.New("confirmation keys must belong to the authorized scope")
		}
	}
	return nil
}

func contains(values []string, value string) bool {
	for _, item := range values {
		if item == value {
			return true
		}
	}
	return false
}
