//go:build !windows

package agent

func defaultCredentialFilename(key, suffix string) string { return key + "." + suffix }

func validateSocketPath(string) error { return nil }
