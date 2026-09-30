//go:build !windows

package agent

import (
	"errors"
	"io"
	"os"
	"path/filepath"
	"syscall"
)

func appendPrivate(path string, data []byte) error {
	if err := securePath(path); err != nil {
		return err
	}
	if err := preparePrivateDirectory(filepath.Dir(path), 0700); err != nil {
		return err
	}
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_APPEND|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0600)
	if err != nil {
		return err
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil {
		return err
	}
	stat, ok := info.Sys().(*syscall.Stat_t)
	if !ok || !info.Mode().IsRegular() || info.Mode().Perm()&0077 != 0 || (stat.Uid != 0 && int(stat.Uid) != os.Geteuid()) {
		return errors.New("event journal must be a trusted regular private file")
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
