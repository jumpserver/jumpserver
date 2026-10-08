package agent

import (
	"bytes"
	"encoding/json"
	"errors"
	"os"
	"regexp"
	"strconv"
	"strings"
	"unicode/utf8"
)

var envFieldLine = regexp.MustCompile(`^[ \t]*([A-Za-z_][A-Za-z0-9_]*)=`)
var yamlFieldLine = regexp.MustCompile(`^([A-Za-z_][A-Za-z0-9_]*)[ \t]*:`)

func credentialField(value Credential, source string) string {
	switch source {
	case "username":
		return value.Username
	case "secret":
		return value.Secret
	case "account_id":
		return value.AccountID
	case "revision":
		return strconv.FormatInt(value.Revision, 10)
	default:
		return ""
	}
}

// patchFlatConfig changes only declared, existing top-level fields. Complex
// formats remain the responsibility of a trusted local update script.
func patchFlatConfig(original []byte, format string, values map[string]string) ([]byte, error) {
	if bytes.IndexByte(original, 0) >= 0 || !utf8.Valid(original) {
		return nil, errors.New("business configuration is not UTF-8 text")
	}
	pattern := envFieldLine
	if format == "yaml" {
		pattern = yamlFieldLine
	}
	seen := map[string]bool{}
	lines := strings.SplitAfter(string(original), "\n")
	for index, line := range lines {
		ending := ""
		if strings.HasSuffix(line, "\n") {
			ending, line = "\n", strings.TrimSuffix(line, "\n")
		}
		if strings.HasSuffix(line, "\r") {
			ending, line = "\r"+ending, strings.TrimSuffix(line, "\r")
		}
		match := pattern.FindStringSubmatchIndex(line)
		if match == nil {
			continue
		}
		name := line[match[2]:match[3]]
		value, wanted := values[name]
		if !wanted {
			continue
		}
		if seen[name] {
			return nil, errors.New("business configuration contains duplicate mapped fields")
		}
		seen[name] = true
		if strings.ContainsAny(value, "\x00\r\n") {
			return nil, errors.New("credential cannot be represented in a single configuration line")
		}
		if format == "env" && strings.ContainsAny(value, "'\"") {
			return nil, errors.New("credential requires a custom updater for this environment file")
		}
		if format == "yaml" {
			quoted, err := json.Marshal(value)
			if err != nil {
				return nil, err
			}
			value = " " + string(quoted)
		}
		lines[index] = line[:match[1]] + value + ending
	}
	if len(seen) != len(values) {
		return nil, errors.New("business configuration is missing a mapped field")
	}
	return []byte(strings.Join(lines, "")), nil
}

func renderMappedConfig(update ConfigUpdate, account AccountSelector, payload Payload) ([]byte, os.FileMode, int, int, error) {
	if err := secureTarget(update.File); err != nil {
		return nil, 0, 0, 0, err
	}
	info, err := os.Lstat(update.File)
	if err != nil {
		return nil, 0, 0, 0, err
	}
	if !info.Mode().IsRegular() || info.Size() > 1<<20 {
		return nil, 0, 0, 0, errors.New("mapped business configuration must be a regular file under 1 MiB")
	}
	raw, err := os.ReadFile(update.File)
	if err != nil {
		return nil, 0, 0, 0, err
	}
	credential, ok := payload.Credentials[account.AccountID]
	if !ok {
		return nil, 0, 0, 0, errors.New("mapped account is unavailable")
	}
	values := map[string]string{}
	for name, source := range update.FieldsMap {
		values[name] = credentialField(credential, source)
	}
	updated, err := patchFlatConfig(raw, update.patchFormat(), values)
	if err != nil {
		return nil, 0, 0, 0, err
	}
	uid, gid, err := fileOwner(info)
	if err != nil {
		return nil, 0, 0, 0, err
	}
	if update.Owner != "" {
		uid, gid, err = ownerIDs(update.Owner)
		if err != nil {
			return nil, 0, 0, 0, err
		}
	}
	return updated, info.Mode().Perm(), uid, gid, nil
}
