//go:build windows

package agent

import "os"

func configureSocketDirectory(path, username string) error {
	if _, _, err := ownerIDs(username); err != nil {
		return err
	}
	return preparePrivateDirectory(path, 0700)
}

func configureSocketFile(path, username string) error {
	if _, _, err := ownerIDs(username); err != nil {
		return err
	}
	if err := protectPrivate(path); err != nil {
		return err
	}
	if info, err := os.Lstat(path); err != nil || info.Mode()&os.ModeSocket == 0 {
		return os.ErrInvalid
	}
	return nil
}
