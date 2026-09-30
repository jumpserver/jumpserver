package main

import (
	"errors"
	"fmt"
	"strings"
	"testing"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

func TestDiagnosticsExplainLocalFailuresWithoutBackendDetails(t *testing.T) {
	local := errors.New("private files must be regular files with mode 0600")
	if got := diagnostic(fmt.Errorf("cannot load Agent configuration: %w", local)); !strings.Contains(got, "configuration") || !strings.Contains(got, "0600") {
		t.Fatal("local diagnostic hid the cause")
	}
	for _, code := range []string{"NetworkError", "ResponseError", "untrusted-secret-value"} {
		failure := &pam.PAMError{Code: code, StatusCode: 403, Detail: "DO_NOT_LOG_PASSWORD", Err: errors.New("DO_NOT_LOG_PAYLOAD")}
		got := diagnostic(fmt.Errorf("initialization failed: %w", failure))
		if strings.Contains(got, "DO_NOT_LOG") || strings.Contains(got, "untrusted-secret-value") {
			t.Fatal("diagnostic exposed a backend response")
		}
		if got == "" {
			t.Fatal("missing backend diagnostic")
		}
	}
}

func TestForegroundModeUsesCurrentUserOutsideLinuxRoot(t *testing.T) {
	for _, test := range []struct {
		platform string
		euid     int
		forced   bool
		want     bool
	}{
		{"linux", 0, false, false},
		{"linux", 1000, false, true},
		{"darwin", 0, false, true},
		{"windows", -1, false, true},
		{"linux", 0, true, true},
	} {
		if got := currentUserMode(test.forced, test.platform, test.euid); got != test.want {
			t.Fatalf("currentUserMode(%t, %q, %d) = %t, want %t", test.forced, test.platform, test.euid, got, test.want)
		}
	}
}
