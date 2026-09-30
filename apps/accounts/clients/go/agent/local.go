package agent

import (
	"context"
	"errors"
	"os"
	"os/user"
	"path/filepath"
)

// PrepareLocal rewrites default paths for an explicitly requested foreground run.
func PrepareLocal(ctx context.Context, bootstrapFile, directory, instanceID string) (string, error) {
	if instanceID == "" || !absolute(directory) {
		return "", errors.New("local initialization requires an absolute directory and stable instance ID")
	}
	if err := securePath(directory); err != nil {
		return "", err
	}
	configFile := filepath.Join(directory, "agent.json")
	if _, err := os.Lstat(configFile); !os.IsNotExist(err) {
		return "", errors.New("local Agent configuration already exists; run it or choose another directory")
	}
	config, err := loadBootstrapConfig(bootstrapFile)
	if err != nil {
		return "", err
	}
	account, err := user.Current()
	if err != nil {
		return "", err
	}
	config.Local, config.InstanceID = true, instanceID
	config.StateFile = filepath.Join(directory, "state.json")
	config.EventFile = filepath.Join(directory, "events.jsonl")
	config.ReconcileSeconds = 30
	config.Delivery.Root = filepath.Join(directory, "credentials")
	config.Delivery.Socket = filepath.Join(directory, "run", "agent.sock")
	config.Delivery.User = account.Username
	if err = config.Validate(); err != nil {
		return "", err
	}
	if err = verifyAccess(ctx, config); err != nil {
		return "", err
	}
	if err = preparePrivateDirectory(directory, 0700); err != nil {
		return "", err
	}
	if err = writeJSON(configFile, config); err != nil {
		return "", err
	}
	return configFile, nil
}
