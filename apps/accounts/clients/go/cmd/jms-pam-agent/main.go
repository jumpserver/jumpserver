// jms-pam-agent is the standalone Go service; Python is not required.
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
	"github.com/jumpserver/jumpserver/apps/accounts/clients/go/agent"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"runtime"
	"syscall"
	"time"
)

func main() {
	if err := run(os.Args[1:]); err != nil && !errors.Is(err, context.Canceled) && !errors.Is(err, flag.ErrHelp) {
		log.Printf("jms-pam-agent failed: %s", diagnostic(err))
		os.Exit(1)
	}
}

// Local validation errors are actionable. Remote response details may contain
// credentials or arbitrary payloads, so report only their status/category.
func diagnostic(err error) string {
	var failure *pam.PAMError
	if errors.As(err, &failure) {
		switch failure.Code {
		case "NetworkError":
			return "cannot reach the backend; check its address and availability"
		case "ResponseError":
			return "the backend returned an invalid response"
		default:
			return fmt.Sprintf("backend request rejected (HTTP %d); check identity, authorization and protocol compatibility", failure.StatusCode)
		}
	}
	return err.Error()
}

func currentUserMode(requested bool, platform string, euid int) bool {
	return requested || platform != "linux" || euid != 0
}

func run(args []string) error {
	if len(args) > 0 && (args[0] == "help" || args[0] == "--help" || args[0] == "-h") {
		fmt.Print(`jms-pam-agent commands:
  run [--local] --config PATH                Run the Agent; non-root/other OS uses local mode
  init-local --bootstrap PATH --directory PATH --instance-id ID
                                            Prepare local foreground configuration
  install --bootstrap PATH --instance-id ID  Install the fixed Linux service
  get_accounts [--config PATH | --socket PATH]
                                            List authorized account metadata
  get_secret ACCOUNT_ID [--config PATH | --socket PATH]
                                            Get account secret JSON, with API/local source
  confirm KEY --revision N --socket PATH     Confirm application of an exact revision
  check-config [--local] --config PATH       Validate private configuration
  version                                   Show version and platform
`)
		return nil
	}
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	command := "run"
	if len(args) > 0 && args[0] != "" && args[0][0] != '-' {
		command, args = args[0], args[1:]
	}
	if command == "version" {
		fmt.Println("jms-pam-agent", pam.Version, runtime.GOOS, runtime.GOARCH)
		return nil
	}
	flags := flag.NewFlagSet("jms-pam-agent "+command, flag.ContinueOnError)
	config := flags.String("config", agent.DefaultConfig, "local Agent configuration")
	switch command {
	case "run", "check-config":
		local := flags.Bool("local", false, "foreground local development with current user and local delivery paths")
		if err := flags.Parse(args); err != nil {
			return err
		}
		settings, err := agent.LoadConfig(*config)
		if err != nil {
			return fmt.Errorf("cannot load Agent configuration: %w", err)
		}
		settings.Local = currentUserMode(*local, runtime.GOOS, os.Geteuid())
		if err = settings.Validate(); err != nil {
			return err
		}
		if command == "check-config" {
			fmt.Println("Agent configuration is valid")
			return nil
		}
		remote, err := settings.Client()
		if err != nil {
			return err
		}
		defer remote.Close()
		service, err := agent.New(settings, remote)
		if err != nil {
			return err
		}
		log.Printf("Agent started: instance=%s local=%t", settings.InstanceID, settings.Local)
		return service.Run(ctx)
	case "init-local":
		bootstrap := flags.String("bootstrap", "", "private application access bootstrap JSON")
		directory := flags.String("directory", "", "absolute private local output directory")
		instance := flags.String("instance-id", "", "stable local instance ID")
		if err := flags.Parse(args); err != nil {
			return err
		}
		path, err := agent.PrepareLocal(ctx, *bootstrap, *directory, *instance)
		if err != nil {
			return err
		}
		fmt.Println("Local Agent configuration:", path)
		return nil
	case "get_accounts", "get-accounts", "get_secret", "get-secret", "get_credential", "get-credential":
		path := "/v1/accounts"
		if command != "get_accounts" && command != "get-accounts" {
			if len(args) == 0 || args[0] == "" || args[0][0] == '-' {
				return errors.New("get_secret requires an account ID before options")
			}
			path = "/v1/credential?account_id=" + url.QueryEscape(args[0])
			args = args[1:]
		}
		socket := flags.String("socket", "", "running Agent socket; otherwise read --config")
		if err := flags.Parse(args); err != nil {
			return err
		}
		if len(flags.Args()) != 0 {
			return errors.New("unexpected query arguments")
		}
		if *socket == "" {
			settings, err := agent.LoadConfig(*config)
			if err != nil {
				return fmt.Errorf("cannot load Agent configuration: %w", err)
			}
			*socket = settings.Delivery.Socket
		}
		return query(ctx, *socket, path)
	case "install":
		options := agent.InstallOptions{}
		flags.StringVar(&options.Bootstrap, "bootstrap", "", "application access bootstrap JSON")
		flags.StringVar(&options.InstanceID, "instance-id", "", "stable instance ID")
		if err := flags.Parse(args); err != nil {
			return err
		}
		options.ConfigFile = *config
		if runtime.GOOS != "linux" || os.Geteuid() != 0 {
			return errors.New("Agent installation requires Linux and root")
		}
		return agent.Install(ctx, options)
	case "confirm":
		if len(args) == 0 {
			return errors.New("credential key is required")
		}
		key := args[0]
		args = args[1:]
		revision := flags.Int64("revision", -1, "exact applied revision")
		socket := flags.String("socket", "", "local Agent socket")
		if err := flags.Parse(args); err != nil {
			return err
		}
		if *socket == "" || *revision < 0 {
			return errors.New("socket and applied revision are required")
		}
		body, _ := json.Marshal(map[string]any{"key": key, "revision": *revision})
		transport := &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
			return (&net.Dialer{}).DialContext(ctx, "unix", *socket)
		}}
		defer transport.CloseIdleConnections()
		client := &http.Client{Transport: transport, Timeout: 15 * time.Second}
		request, _ := http.NewRequestWithContext(ctx, http.MethodPost, "http://localhost/v1/confirm", bytes.NewReader(body))
		request.Header.Set("Content-Type", "application/json")
		response, err := client.Do(request)
		if err != nil {
			return errors.New("local confirmation request failed")
		}
		defer response.Body.Close()
		if response.StatusCode != 200 {
			return errors.New("local confirmation rejected")
		}
		_, err = io.Copy(os.Stdout, io.LimitReader(response.Body, 4096))
		return err
	default:
		return errors.New("use run, init-local, install, get_accounts, get_secret, check-config, confirm or version")
	}
}

func query(ctx context.Context, socket, path string) error {
	transport := &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, "unix", socket)
	}}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: 30 * time.Second}
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, "http://localhost"+path, nil)
	if err != nil {
		return err
	}
	response, err := client.Do(request)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) || errors.Is(err, syscall.ECONNREFUSED) {
			return fmt.Errorf("cannot reach Agent socket %q; start the Agent with run --config or check the service", socket)
		}
		if errors.Is(err, os.ErrPermission) {
			return fmt.Errorf("permission denied for Agent socket %q; use its application user or root", socket)
		}
		if errors.Is(err, context.DeadlineExceeded) {
			return errors.New("Agent query timed out; check Agent and backend availability")
		}
		return fmt.Errorf("cannot reach Agent socket %q; check the running Agent", socket)
	}
	defer response.Body.Close()
	if response.StatusCode != 200 {
		return fmt.Errorf("Agent query rejected (HTTP %d); check authorization and backend availability", response.StatusCode)
	}
	var payload json.RawMessage
	if err = json.NewDecoder(io.LimitReader(response.Body, 4<<20)).Decode(&payload); err != nil {
		return errors.New("invalid Agent query response")
	}
	var output bytes.Buffer
	if err = json.Indent(&output, payload, "", "  "); err != nil {
		return err
	}
	_, err = fmt.Fprintln(os.Stdout, output.String())
	return err
}
