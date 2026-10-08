//go:build windows

package agent

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/user"
	"path/filepath"
	"strings"
	"unsafe"

	"golang.org/x/sys/windows"
)

// Windows local mode keeps every credential path below the current user's home.
// Its files and directories must have a private ACL granting access only to
// that user, SYSTEM and Administrators. Reparse points are never followed.
func securePath(path string) error {
	if !absolute(path) {
		return errors.New("an absolute normalized path is required")
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return err
	}
	home, err = filepath.Abs(home)
	if err != nil {
		return err
	}
	rel, err := filepath.Rel(home, path)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return errors.New("Windows Agent paths must stay below the current user's home directory")
	}
	for current := path; ; current = filepath.Dir(current) {
		info, statErr := os.Lstat(current)
		if statErr != nil && !os.IsNotExist(statErr) {
			return statErr
		}
		if statErr == nil {
			name, err := windows.UTF16PtrFromString(current)
			if err != nil {
				return err
			}
			attributes, err := windows.GetFileAttributes(name)
			if err != nil {
				return err
			}
			if attributes&windows.FILE_ATTRIBUTE_REPARSE_POINT != 0 || info.Mode()&os.ModeSymlink != 0 {
				return errors.New("Agent paths cannot contain links or reparse points")
			}
			if current != path && !info.IsDir() {
				return errors.New("path ancestor is not a directory")
			}
			if current != home {
				if err := trustedACL(current); err != nil {
					return err
				}
			}
		}
		if strings.EqualFold(current, home) {
			return nil
		}
		if filepath.Dir(current) == current {
			return errors.New("Agent path is outside the current user's home directory")
		}
	}
}

func trustedACL(path string) error {
	sd, err := windows.GetNamedSecurityInfo(path, windows.SE_FILE_OBJECT,
		windows.OWNER_SECURITY_INFORMATION|windows.DACL_SECURITY_INFORMATION)
	if err != nil {
		return err
	}
	current, err := currentSID()
	if err != nil {
		return err
	}
	owner, _, err := sd.Owner()
	if err != nil || owner == nil || !trustedSID(owner, current) {
		return errors.New("Agent path must have trusted Windows ownership")
	}
	dacl, _, err := sd.DACL()
	if err != nil || dacl == nil {
		return errors.New("Agent path must have a private Windows ACL")
	}
	for i := uint32(0); i < uint32(dacl.AceCount); i++ {
		var ace *windows.ACCESS_ALLOWED_ACE
		if err := windows.GetAce(dacl, i, &ace); err != nil {
			return err
		}
		if ace.Header.AceType == windows.ACCESS_DENIED_ACE_TYPE {
			continue
		}
		if ace.Header.AceType != windows.ACCESS_ALLOWED_ACE_TYPE || !trustedSID((*windows.SID)(unsafe.Pointer(&ace.SidStart)), current) {
			return errors.New("Agent path must have a private Windows ACL")
		}
	}
	return nil
}

func currentSID() (*windows.SID, error) {
	account, err := user.Current()
	if err != nil {
		return nil, err
	}
	return windows.StringToSid(account.Uid)
}

func trustedSID(sid, current *windows.SID) bool {
	if sid.Equals(current) {
		return true
	}
	return sid.String() == "S-1-5-18" || sid.String() == "S-1-5-32-544"
}

func protectPrivate(path string) error {
	current, err := currentSID()
	if err != nil {
		return err
	}
	sd, err := windows.SecurityDescriptorFromString(
		fmt.Sprintf("D:P(A;OICI;GA;;;SY)(A;OICI;GA;;;BA)(A;OICI;GA;;;%s)", current.String()),
	)
	if err != nil {
		return err
	}
	dacl, _, err := sd.DACL()
	if err != nil {
		return err
	}
	return windows.SetNamedSecurityInfo(path, windows.SE_FILE_OBJECT,
		windows.DACL_SECURITY_INFORMATION|windows.PROTECTED_DACL_SECURITY_INFORMATION,
		nil, nil, dacl, nil)
}

func privateFile(path string) error {
	if err := securePath(path); err != nil {
		return err
	}
	info, err := os.Lstat(path)
	if err != nil {
		return err
	}
	if !info.Mode().IsRegular() {
		return errors.New("private files must be regular files")
	}
	return trustedACL(path)
}

func secureTarget(path string) error {
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
		return errors.New("target must be a regular file without links")
	}
	return securePath(path)
}

func preparePrivateDirectory(path string, mode os.FileMode) error {
	if err := securePath(path); err != nil {
		return err
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return err
	}
	home, err = filepath.Abs(home)
	if err != nil {
		return err
	}
	rel, err := filepath.Rel(home, path)
	if err != nil {
		return err
	}
	current := home
	if rel == "." {
		return nil
	}
	for _, component := range strings.Split(rel, string(filepath.Separator)) {
		current = filepath.Join(current, component)
		if err := os.Mkdir(current, mode); err == nil {
			if err := protectPrivate(current); err != nil {
				return err
			}
		} else if !os.IsExist(err) {
			return err
		}
		info, err := os.Lstat(current)
		if err != nil || !info.IsDir() {
			return errors.New("Agent directory path is not a private directory")
		}
		if err := securePath(current); err != nil {
			return err
		}
	}
	return securePath(path)
}

func privateBackupDirectory(path string) error {
	if err := preparePrivateDirectory(path, 0700); err != nil {
		return err
	}
	info, err := os.Lstat(path)
	if err != nil {
		return err
	}
	if !info.IsDir() {
		return errors.New("backup directory must be private")
	}
	return securePath(path)
}

func atomicWrite(path string, data []byte, mode os.FileMode, uid, gid int) error {
	if uid >= 0 || gid >= 0 {
		return errors.New("Windows Agent delivery can only use the current user")
	}
	if err := secureTarget(path); err != nil {
		return err
	}
	parent := filepath.Dir(path)
	if err := preparePrivateDirectory(parent, 0700); err != nil {
		return err
	}
	file, err := os.CreateTemp(parent, ".jms-pam-*")
	if err != nil {
		return err
	}
	temporary := file.Name()
	defer os.Remove(temporary)
	defer file.Close()
	if err = protectPrivate(temporary); err != nil {
		return err
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
	return os.Rename(temporary, path)
}

func writeJSON(path string, value any) error {
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return atomicWrite(path, append(data, '\n'), 0600, -1, -1)
}

func ownerIDs(username string) (int, int, error) {
	account, err := user.Lookup(username)
	if err != nil {
		return 0, 0, errors.New("delivery owner does not exist")
	}
	current, err := user.Current()
	if err != nil {
		return 0, 0, err
	}
	if account.Uid != current.Uid {
		return 0, 0, errors.New("Windows Agent delivery requires the current user")
	}
	return -1, -1, nil
}

func fileOwner(info os.FileInfo) (int, int, error) {
	return -1, -1, nil
}
