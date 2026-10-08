package agent

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

const backupLimit = 10
const maxBackupFileSize = 32 << 20
const backupDateFormat = "2006-01-02_15-04-05.000000000Z"

// backupTargets saves the contents that are about to be replaced. A target
// appears only once per delivery, even when several account rules update it.
func backupTargets(stateFile string, targets []string) error {
	root := filepath.Join(filepath.Dir(stateFile), "backups")
	seen := map[string]bool{}
	for _, target := range targets {
		if seen[target] {
			continue
		}
		seen[target] = true
		if target == root || strings.HasPrefix(target, root+string(filepath.Separator)) {
			return errors.New("business configuration cannot be inside the Agent backup directory")
		}
		if err := backupTarget(root, target); err != nil {
			return err
		}
	}
	return nil
}

func backupTarget(root, target string) error {
	if err := secureTarget(target); err != nil {
		return err
	}
	info, err := os.Lstat(target)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	if !info.Mode().IsRegular() || info.Size() > maxBackupFileSize {
		return errors.New("business configuration backup requires a regular file under 32 MiB")
	}
	file, err := os.Open(target)
	if err != nil {
		return err
	}
	data, err := io.ReadAll(io.LimitReader(file, maxBackupFileSize+1))
	closeErr := file.Close()
	if err != nil {
		return err
	}
	if closeErr != nil {
		return closeErr
	}
	if len(data) > maxBackupFileSize {
		return errors.New("business configuration backup exceeds 32 MiB")
	}
	if err := privateBackupDirectory(root); err != nil {
		return err
	}
	pathHash := sha256.Sum256([]byte(target))
	base := backupBaseName(target)
	directory := filepath.Join(root, base+"-"+hex.EncodeToString(pathHash[:]))
	if err := privateBackupDirectory(directory); err != nil {
		return err
	}
	namePrefix := base + "."
	entries, err := os.ReadDir(directory)
	if err != nil {
		return err
	}
	var history []string
	for _, entry := range entries {
		if strings.HasPrefix(entry.Name(), namePrefix) && strings.HasSuffix(entry.Name(), ".bak") {
			stamp := strings.TrimSuffix(strings.TrimPrefix(entry.Name(), namePrefix), ".bak")
			if _, err := time.Parse(backupDateFormat, stamp); err == nil {
				history = append(history, entry.Name())
			}
		}
	}
	sort.Strings(history)
	stampTime := time.Now().UTC()
	if len(history) > 0 {
		latest := filepath.Join(directory, history[len(history)-1])
		if err := privateFile(latest); err != nil {
			return err
		}
		previous, err := os.ReadFile(latest)
		if err != nil {
			return err
		}
		if bytes.Equal(data, previous) {
			return pruneBackupHistory(directory, history)
		}
		latestStamp := strings.TrimSuffix(strings.TrimPrefix(history[len(history)-1], namePrefix), ".bak")
		lastTime, _ := time.Parse(backupDateFormat, latestStamp)
		if !stampTime.After(lastTime) {
			stampTime = lastTime.Add(time.Nanosecond)
		}
	}
	var backup string
	for attempt := 0; attempt < 10; attempt++ {
		stamp := stampTime.Add(time.Duration(attempt) * time.Nanosecond).Format(backupDateFormat)
		backup = filepath.Join(directory, namePrefix+stamp+".bak")
		if _, err := os.Lstat(backup); os.IsNotExist(err) {
			break
		} else if err != nil {
			return err
		}
		backup = ""
	}
	if backup == "" {
		return errors.New("cannot allocate a unique backup name")
	}
	if err := atomicWrite(backup, data, 0600, -1, -1); err != nil {
		return err
	}
	history = append(history, filepath.Base(backup))
	sort.Strings(history)
	if err := pruneBackupHistory(directory, history); err != nil {
		_ = os.Remove(backup)
		return err
	}
	return nil
}

func pruneBackupHistory(directory string, history []string) error {
	for len(history) > backupLimit {
		oldest := filepath.Join(directory, history[0])
		if err := privateFile(oldest); err != nil {
			return err
		}
		if err := os.Remove(oldest); err != nil {
			return fmt.Errorf("cannot prune old business configuration backup: %w", err)
		}
		history = history[1:]
	}
	return nil
}

// Keep room for the hash and date even when the business filename is long.
func backupBaseName(target string) string {
	base := filepath.Base(target)
	if len(base) <= 80 {
		return base
	}
	end := 0
	for index := range base {
		if index > 80 {
			break
		}
		end = index
	}
	return base[:end]
}
