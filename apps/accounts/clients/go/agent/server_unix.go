//go:build !windows

package agent

import (
	"errors"
	"os"
	"os/user"
)

func configureSocketDirectory(path, username string) error {
	if err := os.MkdirAll(path, 0750); err != nil {
		return err
	}
	account, err := user.Lookup(username)
	if err != nil {
		return errors.New("application user does not exist")
	}
	_, gid, err := accountIDs(account.Uid, account.Gid)
	if err != nil {
		return err
	}
	if err := os.Chown(path, os.Geteuid(), gid); err != nil {
		return err
	}
	return os.Chmod(path, 0750)
}

func configureSocketFile(path, username string) error {
	account, err := user.Lookup(username)
	if err != nil {
		return errors.New("application user does not exist")
	}
	uid, gid, err := accountIDs(account.Uid, account.Gid)
	if err != nil {
		return err
	}
	if err := os.Chown(path, uid, gid); err != nil {
		return err
	}
	return os.Chmod(path, 0600)
}
