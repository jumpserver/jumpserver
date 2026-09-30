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
	"strings"
	"time"
)

const DefaultConfig = "/etc/jms-pam-agent/agent.json"
const ServiceName = "jms-pam-agent.service"
const DefaultState = "/var/lib/jms-pam-agent/state.json"

var unitPattern = regexp.MustCompile(`^[A-Za-z0-9_.@:-]+\.service$`)

type DeliveryConfiguration struct {
	Mode      string `json:"delivery_mode"`
	Root      string `json:"delivery_root"`
	Socket    string `json:"socket_path"`
	User      string `json:"app_user"`
	Unit      string `json:"systemd_unit"`
	Operation string `json:"systemd_action"`
}

type File struct {
	Path     string `json:"path"`
	Format   string `json:"format"`
	Template string `json:"template_file,omitempty"`
	Owner    string `json:"owner,omitempty"`
}

type Action struct {
	Type           string   `json:"type"`
	Unit           string   `json:"unit,omitempty"`
	Operation      string   `json:"operation,omitempty"`
	Path           string   `json:"path,omitempty"`
	Args           []string `json:"args,omitempty"`
	TimeoutSeconds int      `json:"timeout_seconds,omitempty"`
}

// Rules and their file/script paths are trusted local configuration. Core cannot supply them.
type Rule struct {
	Keys   []string `json:"keys"`
	Files  []File   `json:"files,omitempty"`
	Action *Action  `json:"action,omitempty"`
}

type Config struct {
	// Local is chosen by the CLI for current-user foreground runs, never by Core.
	Local            bool                  `json:"-"`
	Endpoint         string                `json:"endpoint"`
	AppID            string                `json:"app_id"`
	AppSecret        string                `json:"app_secret"`
	OrgID            string                `json:"org_id"`
	InstanceID       string                `json:"instance_id"`
	StateFile        string                `json:"state_file"`
	EventFile        string                `json:"event_file,omitempty"`
	ReconcileSeconds int                   `json:"reconcile_interval"`
	Delivery         DeliveryConfiguration `json:"delivery"`
	Rules            []Rule                `json:"rules,omitempty"`
}

func LoadConfig(path string) (Config, error) {
	var config Config
	config, err := loadBootstrapConfig(path)
	if err != nil {
		return config, err
	}
	if config.StateFile == "" {
		config.StateFile = DefaultState
	}
	if config.ReconcileSeconds == 0 {
		config.ReconcileSeconds = 300
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
	return decodeConfig(raw)
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
	for _, rule := range c.Rules {
		if len(rule.Keys) == 0 || (len(rule.Files) == 0 && rule.Action == nil) {
			return errors.New("delivery rules require keys and files or an action")
		}
		for _, key := range rule.Keys {
			if !validKey(key) {
				return errors.New("invalid rule key")
			}
		}
		for _, file := range rule.Files {
			if !absolute(file.Path) || file.Path == c.StateFile || file.Path == c.EventFile || file.Path == c.Delivery.Socket || (file.Format != "json" && file.Format != "environment" && file.Format != "template") {
				return errors.New("invalid delivery file path or format")
			}
			if file.Format == "environment" && len(rule.Keys) != 1 {
				return errors.New("EnvironmentFile rules require exactly one credential key")
			}
			if file.Format == "template" && !absolute(file.Template) {
				return errors.New("templates require an absolute local template_file")
			}
			if c.Local && file.Owner != "" && file.Owner != c.Delivery.User {
				return errors.New("local files must belong to the current user")
			}
		}
		if rule.Action != nil {
			if c.Local && rule.Action.Type == "systemd" {
				return errors.New("systemd actions require the Linux service")
			}
			if err := rule.Action.Validate(); err != nil {
				return err
			}
		}
	}
	return nil
}

func validateDelivery(d DeliveryConfiguration) error {
	if d.Mode != "json" && d.Mode != "environment" && d.Mode != "socket" {
		return errors.New("unsupported delivery mode")
	}
	if !absolute(d.Root) || !absolute(d.Socket) || filepath.Base(d.Socket) != "agent.sock" || d.User == "" {
		return errors.New("invalid delivery root, socket path or application user")
	}
	if d.Mode != "environment" && (d.Unit != "" || d.Operation != "") {
		return errors.New("use rules.action for JSON/socket service actions")
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
	switch a.Type {
	case "systemd":
		if !unitPattern.MatchString(a.Unit) || (a.Operation != "reload" && a.Operation != "restart") || a.Path != "" || len(a.Args) != 0 {
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
