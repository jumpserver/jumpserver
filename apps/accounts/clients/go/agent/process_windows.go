//go:build windows

package agent

import (
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

func validateExecutable(path string, info os.FileInfo) error {
	if !info.Mode().IsRegular() || !strings.EqualFold(filepath.Ext(path), ".exe") {
		return errors.New("Windows Agent actions require a trusted .exe file")
	}
	return nil
}

func prepareActionProcess(command *exec.Cmd) {
	root := os.Getenv("SystemRoot")
	command.Env = []string{"SystemRoot=" + root, "WINDIR=" + root, "PATH=" + root + `\System32`}
}
