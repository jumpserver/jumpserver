package agent

import (
	"context"
	"errors"
	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

type InstallOptions struct{ Bootstrap, ConfigFile, InstanceID string }

// Unit always installs the fixed jms-pam-agent service.
func Unit(binary, config string) string {
	quote := func(value string) string { return strconv.Quote(strings.ReplaceAll(value, "%", "%%")) }
	return "[Unit]\nDescription=JumpServer PAM Agent\nAfter=network-online.target\nWants=network-online.target\n\n[Service]\nType=simple\nUser=root\nUMask=0077\nExecStart=" + quote(binary) + " run --config " + quote(config) + "\nRestart=on-failure\nRestartSec=5\nKillMode=control-group\n\n[Install]\nWantedBy=multi-user.target\n"
}

// Prepare verifies application access and installs an explicitly supplied local configuration.
func Prepare(ctx context.Context, options InstallOptions) (Config, error) {
	if options.ConfigFile == "" {
		options.ConfigFile = DefaultConfig
	}
	resolved, err := filepath.Abs(options.ConfigFile)
	if err != nil {
		return Config{}, errors.New("cannot resolve installation config path")
	}
	options.ConfigFile = resolved
	existing, err := LoadConfig(options.ConfigFile)
	if err == nil {
		if options.InstanceID != "" && options.InstanceID != existing.InstanceID {
			return Config{}, errors.New("existing installation belongs to another instance")
		}
		if options.Bootstrap != "" {
			bootstrap, err := LoadConfig(options.Bootstrap)
			if err != nil {
				return Config{}, err
			}
			if bootstrap.Endpoint != existing.Endpoint || bootstrap.AppID != existing.AppID || bootstrap.OrgID != existing.OrgID {
				return Config{}, errors.New("existing installation belongs to another application")
			}
		}
		if err := verifyAccess(ctx, existing); err != nil {
			return Config{}, err
		}
		return existing, nil
	}
	if _, statErr := os.Lstat(options.ConfigFile); !os.IsNotExist(statErr) {
		return Config{}, errors.New("existing Agent configuration is invalid; repair it before installation")
	}
	if options.Bootstrap == "" {
		return Config{}, errors.New("install requires --bootstrap with the complete local Agent configuration")
	}
	config, err := LoadConfig(options.Bootstrap)
	if err != nil {
		return Config{}, err
	}
	if options.InstanceID != "" {
		config.InstanceID = options.InstanceID
	}
	if config.InstanceID == "<instance-id>" {
		return Config{}, errors.New("set a stable instance_id or pass --instance-id")
	}
	if err = config.Validate(); err != nil {
		return Config{}, err
	}
	if err = verifyAccess(ctx, config); err != nil {
		return Config{}, err
	}
	if err = writeJSON(options.ConfigFile, config.compactDefaults()); err != nil {
		return Config{}, err
	}
	return config, nil
}
func verifyAccess(ctx context.Context, config Config) error {
	remote, err := config.Client()
	if err != nil {
		return err
	}
	defer remote.Close()
	response, err := remote.SyncAgent(ctx, pam.AgentSyncOptions{RestartSupported: config.Delivery.Mode == "environment" && config.Delivery.Operation == "restart"})
	if err != nil {
		return err
	}
	return validateScope(response.Scope)
}
func (c Config) clientOptions() pam.Options {
	return pam.Options{Endpoint: c.Endpoint, AppID: c.AppID, AppSecret: c.AppSecret, OrgID: c.OrgID, InstanceID: c.InstanceID, Source: "jms-pam-agent"}
}
func (c Config) Client() (*pam.Client, error) { return pam.NewClient(c.clientOptions()) }
func Install(ctx context.Context, options InstallOptions) error {
	if options.ConfigFile == "" {
		options.ConfigFile = DefaultConfig
	}
	resolved, err := filepath.Abs(options.ConfigFile)
	if err != nil {
		return errors.New("cannot resolve installation config path")
	}
	options.ConfigFile = resolved

	if os.Geteuid() != 0 {
		return errors.New("install requires root")
	}
	if _, err := Prepare(ctx, options); err != nil {
		return err
	}
	if options.ConfigFile == "" {
		options.ConfigFile = DefaultConfig
	}
	executable, err := os.Executable()
	if err != nil {
		return err
	}
	if err = securePath(executable); err != nil {
		return err
	}
	if err = atomicWrite("/etc/systemd/system/"+ServiceName, []byte(Unit(executable, options.ConfigFile)), 0644, -1, -1); err != nil {
		return err
	}
	for _, args := range [][]string{{"daemon-reload"}, {"enable", ServiceName}, {"restart", ServiceName}, {"is-active", "--quiet", ServiceName}} {
		bounded, cancel := context.WithTimeout(ctx, 30*time.Second)
		err = exec.CommandContext(bounded, "/usr/bin/systemctl", args...).Run()
		cancel()
		if err != nil {
			return errors.New("systemd Agent installation failed")
		}
	}
	return nil
}
