//go:build windows

package agent

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
)

func defaultCredentialFilename(key, suffix string) string {
	digest := sha256.Sum256([]byte(key))
	return "key-" + hex.EncodeToString(digest[:]) + "." + suffix
}

func validateSocketPath(path string) error {
	if len(path) >= 108 {
		return errors.New("Windows Agent socket path is too long; choose a shorter local directory")
	}
	return nil
}
