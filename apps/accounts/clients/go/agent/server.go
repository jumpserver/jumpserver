package agent

import (
	"context"
	"encoding/json"
	"errors"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type localServer struct {
	*http.Server
	path string
}

func (s *localServer) Close() error { err := s.Server.Close(); _ = os.Remove(s.path); return err }

func (a *Agent) startServer() (*localServer, error) {
	path := a.Config.Delivery.Socket
	if err := securePath(filepath.Dir(path)); err != nil {
		return nil, err
	}
	if err := configureSocketDirectory(filepath.Dir(path), a.Config.Delivery.User); err != nil {
		return nil, err
	}
	if info, err := os.Lstat(path); err == nil {
		if info.Mode()&os.ModeSocket == 0 {
			return nil, errors.New("socket path is occupied by another file")
		}
		connection, dialErr := net.DialTimeout("unix", path, time.Second)
		if dialErr == nil {
			_ = connection.Close()
			return nil, errors.New("an Agent already owns the socket")
		}
		if err = os.Remove(path); err != nil {
			return nil, err
		}
	} else if !os.IsNotExist(err) {
		return nil, err
	}
	listener, err := net.Listen("unix", path)
	if err != nil {
		return nil, err
	}
	err = configureSocketFile(path, a.Config.Delivery.User)
	if err != nil {
		listener.Close()
		os.Remove(path)
		return nil, err
	}
	server := &localServer{Server: &http.Server{Handler: a, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 30 * time.Second}, path: path}
	go func() { _ = server.Serve(listener) }()
	return server, nil
}

func (a *Agent) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	reply := func(status int, payload any) { w.WriteHeader(status); _ = json.NewEncoder(w).Encode(payload) }
	switch {
	case r.Method == http.MethodGet && r.URL.Path == "/v1/health":
		reply(200, a.Health())
	case r.Method == http.MethodGet && r.URL.Path == "/v1/accounts":
		value, err := a.Accounts(r.Context())
		if err != nil {
			reply(503, map[string]string{"code": "account_query_failed"})
			return
		}
		reply(200, value)
	case r.Method == http.MethodGet && r.URL.Path == "/v1/credential":
		accountID := r.URL.Query().Get("account_id")
		if accountID == "" {
			reply(400, map[string]string{"code": "account_id_required"})
			return
		}
		value, err := a.AccountCredential(r.Context(), accountID)
		if err != nil {
			reply(403, map[string]string{"code": "credential_query_failed"})
			return
		}
		reply(200, value)
	case r.Method == http.MethodGet && strings.HasPrefix(r.URL.Path, "/v1/credentials/"):
		value, err := a.LocalCredential(strings.TrimPrefix(r.URL.Path, "/v1/credentials/"))
		if err != nil {
			status := 404
			if err.Error() == "agent_access_denied" {
				status = 503
			}
			reply(status, map[string]string{"code": err.Error()})
			return
		}
		reply(200, value)
	case r.Method == http.MethodPost && r.URL.Path == "/v1/confirm":
		var request struct {
			Key      string `json:"key"`
			Revision int64  `json:"revision"`
		}
		decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 4096))
		decoder.DisallowUnknownFields()
		if decoder.Decode(&request) != nil || request.Key == "" || request.Revision < 0 {
			reply(400, map[string]string{"code": "invalid_confirmation"})
			return
		}
		applied, err := a.Confirm(r.Context(), request.Key, request.Revision)
		if err != nil {
			reply(400, map[string]string{"code": "confirmation_rejected"})
			return
		}
		status := "pending"
		if applied.Confirmed {
			status = "confirmed"
		}
		reply(200, map[string]any{"key": applied.Key, "revision": applied.Revision, "account_id": applied.AccountID, "status": status})
	default:
		reply(404, map[string]string{"code": "not_found"})
	}
}

func checkService(ctx context.Context, unit string) error {
	bounded, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()
	command := exec.CommandContext(bounded, "/usr/bin/systemctl", "is-active", "--quiet", unit)
	if command.Run() != nil {
		return errors.New("application service is not active")
	}
	return nil
}
