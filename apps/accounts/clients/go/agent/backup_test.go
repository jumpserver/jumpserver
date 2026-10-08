//go:build !windows

package agent

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"testing"
)

func TestBusinessConfigurationBackupsKeepTenDatedPrivateVersions(t *testing.T) {
	config, _, _ := fixture(t)
	root := filepath.Dir(config.StateFile)
	state := config.StateFile
	target := filepath.Join(root, "config.txt")
	backupRoot := filepath.Join(root, "backups")
	for version := 0; version < 12; version++ {
		oldContent := fmt.Sprintf("VERSION=%d\n", version)
		if err := os.WriteFile(target, []byte(oldContent), 0600); err != nil {
			t.Fatal(err)
		}
		if err := backupTargets(state, []string{target, target}); err != nil {
			t.Fatal(err)
		}
	}
	entries, err := os.ReadDir(backupRoot)
	if err != nil || len(entries) != 1 {
		t.Fatalf("expected one target backup directory: %v, %v", entries, err)
	}
	backups, err := os.ReadDir(filepath.Join(backupRoot, entries[0].Name()))
	if err != nil || len(backups) != backupLimit {
		t.Fatalf("expected %d backups: %v, %v", backupLimit, backups, err)
	}
	var contents []string
	for _, entry := range backups {
		if !strings.Contains(entry.Name(), "config.txt.20") || !strings.HasSuffix(entry.Name(), "Z.bak") {
			t.Fatalf("backup name lacks a UTC date: %q", entry.Name())
		}
		path := filepath.Join(backupRoot, entries[0].Name(), entry.Name())
		if err := privateFile(path); err != nil {
			t.Fatalf("backup is not private: %v", err)
		}
		if runtime.GOOS != "windows" {
			info, err := os.Stat(path)
			if err != nil || info.Mode().Perm() != 0600 {
				t.Fatalf("backup mode: %v, %v", info, err)
			}
		}
		data, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		contents = append(contents, string(data))
	}
	sort.Strings(contents)
	for version := 2; version < 12; version++ {
		want := fmt.Sprintf("VERSION=%d\n", version)
		found := false
		for _, got := range contents {
			found = found || got == want
		}
		if !found {
			t.Fatalf("missing retained version %d: %v", version, contents)
		}
	}
	if err := backupTargets(state, []string{target}); err != nil {
		t.Fatal(err)
	}
	again, err := os.ReadDir(filepath.Join(backupRoot, entries[0].Name()))
	if err != nil || len(again) != backupLimit {
		t.Fatalf("unchanged content created a duplicate backup: %v, %v", again, err)
	}
}

func TestBusinessConfigurationBackupFailureStopsDelivery(t *testing.T) {
	config, _, _ := fixture(t)
	root := filepath.Dir(config.StateFile)
	target := filepath.Join(root, "config.txt")
	if err := os.WriteFile(target, []byte("DB_USER=old\n"), 0600); err != nil {
		t.Fatal(err)
	}
	config.Rules = []Rule{{Accounts: []AccountSelector{{AccountID: "account"}}, ConfigUpdate: &ConfigUpdate{File: target, FieldsMap: map[string]string{"DB_USER": "username"}}}}
	if err := os.WriteFile(filepath.Join(root, "backups"), []byte("blocked"), 0600); err != nil {
		t.Fatal(err)
	}
	err := Deliver(context.Background(), config, map[string]Credential{"account": {AccountID: "account", Username: "new"}}, map[string]bool{"account": true})
	if err == nil || !strings.Contains(err.Error(), "backup failed") {
		t.Fatalf("expected backup failure before delivery, got %v", err)
	}
	data, err := os.ReadFile(target)
	if err != nil || string(data) != "DB_USER=old\n" {
		t.Fatalf("business file changed after backup failure: %v", err)
	}
}
