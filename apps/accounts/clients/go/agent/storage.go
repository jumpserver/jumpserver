//go:build !windows

package agent

import (
	"encoding/json"
	"errors"
	"os"
	"os/user"
	"path/filepath"
	"strconv"
	"syscall"
)

// Paths must be controlled by the Agent user (root in the systemd service).
// Writable ancestors and symlinks are rejected before accessing credential files.
func securePath(path string) error {
	if !absolute(path) {
		return errors.New("an absolute normalized path is required")
	}
	for current := path; ; current = filepath.Dir(current) {
		info, err := os.Lstat(current)
		if err != nil && !os.IsNotExist(err) {
			return err
		}
		if err == nil {
			stat, ok := info.Sys().(*syscall.Stat_t)
			if !ok || (stat.Uid != 0 && int(stat.Uid) != os.Geteuid()) || info.Mode()&os.ModeSymlink != 0 || info.Mode().Perm()&0022 != 0 {
				return errors.New("path must have trusted ownership, no writable ancestors and no symlinks")
			}
			if current != path && !info.IsDir() {
				return errors.New("path ancestor is not a directory")
			}
		}
		if filepath.Dir(current) == current {
			return nil
		}
	}
}

func privateFile(path string) error {
	if err := securePath(path); err != nil {
		return err
	}
	info, err := os.Lstat(path)
	if err != nil {
		return err
	}
	if !info.Mode().IsRegular() || info.Mode().Perm()&0077 != 0 {
		return errors.New("private files must be regular files with mode 0600")
	}
	return nil
}

// A delivered file may belong to the application user. Atomic replacement is
// safe only when its parent remains controlled by the Agent.
func secureTarget(path string) error {
	if !absolute(path) {
		return errors.New("an absolute normalized target path is required")
	}
	if err := securePath(filepath.Dir(path)); err != nil {
		return err
	}
	info, err := os.Lstat(path)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	if !info.Mode().IsRegular() {
		return errors.New("target must be a regular file without symlinks")
	}
	return nil
}

func atomicWrite(path string, data []byte, mode os.FileMode, uid, gid int) error {
	if err := secureTarget(path); err != nil {
		return err
	}
	parent := filepath.Dir(path)
	if err := os.MkdirAll(parent, 0700); err != nil {
		return err
	}
	if err := secureTarget(path); err != nil {
		return err
	}
	file, err := os.CreateTemp(parent, ".jms-pam-*")
	if err != nil {
		return err
	}
	temporary := file.Name()
	defer os.Remove(temporary)
	defer file.Close()
	if err = file.Chmod(mode); err != nil {
		return err
	}
	if uid >= 0 {
		if err = file.Chown(uid, gid); err != nil {
			return err
		}
	}
	if _, err = file.Write(data); err != nil {
		return err
	}
	if err = file.Sync(); err != nil {
		return err
	}
	if err = file.Close(); err != nil {
		return err
	}
	if err = secureTarget(path); err != nil {
		return err
	}
	if err = os.Rename(temporary, path); err != nil {
		return err
	}
	directory, err := os.Open(parent)
	if err != nil {
		return err
	}
	defer directory.Close()
	return directory.Sync()
}

func writeJSON(path string, value any) error {
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return atomicWrite(path, append(data, '\n'), 0600, -1, -1)
}

func accountIDs(uid, gid string) (int, int, error) {
	user, err := strconv.Atoi(uid)
	if err != nil {
		return 0, 0, err
	}
	group, err := strconv.Atoi(gid)
	return user, group, err
}

func ownerIDs(username string) (int, int, error) {
	account, err := user.Lookup(username)
	if err != nil {
		return 0, 0, errors.New("delivery owner does not exist")
	}
	return accountIDs(account.Uid, account.Gid)
}

func fileOwner(info os.FileInfo) (int, int, error) {
	stat, ok := info.Sys().(*syscall.Stat_t)
	if !ok {
		return 0, 0, errors.New("cannot read business configuration ownership")
	}
	return int(stat.Uid), int(stat.Gid), nil
}

func preparePrivateDirectory(path string, mode os.FileMode) error {
	return os.MkdirAll(path, mode)
}

func privateBackupDirectory(path string) error {
	if err := preparePrivateDirectory(path, 0700); err != nil {
		return err
	}
	if err := securePath(path); err != nil {
		return err
	}
	info, err := os.Lstat(path)
	if err != nil {
		return err
	}
	if !info.IsDir() || info.Mode().Perm()&0077 != 0 {
		return errors.New("backup directory must be private")
	}
	return nil
}
