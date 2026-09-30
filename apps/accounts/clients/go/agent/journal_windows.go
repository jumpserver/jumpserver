//go:build windows

package agent

import (
	"io"
	"os"
	"path/filepath"
)

func appendPrivate(path string, data []byte) error {
	if err := securePath(path); err != nil {
		return err
	}
	if err := preparePrivateDirectory(filepath.Dir(path), 0700); err != nil {
		return err
	}
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0600)
	if err != nil {
		return err
	}
	defer file.Close()
	if err = protectPrivate(path); err != nil {
		return err
	}
	if err = privateFile(path); err != nil {
		return err
	}
	count, err := file.Write(data)
	if err != nil {
		return err
	}
	if count != len(data) {
		return io.ErrShortWrite
	}
	return file.Sync()
}
