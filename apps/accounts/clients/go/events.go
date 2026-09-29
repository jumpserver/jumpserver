package pam

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"time"

	"github.com/coder/websocket"
)

// WatchCredentialEvents reconciles reconnect snapshots, sends received receipts,
// and calls handler sequentially. A receipt does not confirm application use.
// Cancel ctx or Close the client to stop; handler errors are returned unchanged.
func (c *Client) WatchCredentialEvents(ctx context.Context, handler func(Event) error) error {
	if handler == nil {
		return fmt.Errorf("handler is required")
	}
	c.mu.Lock()
	closed := c.closed
	c.mu.Unlock()
	if closed {
		return errors.New("client is closed")
	}
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	release := context.AfterFunc(c.stop, cancel)
	defer release()
	delay := time.Second
	for ctx.Err() == nil {
		endpoint, err := url.Parse(c.options.Endpoint + "/ws/accounts/credential-events/")
		if err != nil {
			return err
		}
		if endpoint.Scheme == "https" {
			endpoint.Scheme = "wss"
		} else {
			endpoint.Scheme = "ws"
		}
		query := endpoint.Query()
		query.Set("instance_id", c.options.InstanceID)
		if c.options.ConfigurationID != "" {
			query.Set("configuration_id", c.options.ConfigurationID)
		}
		endpoint.RawQuery = query.Encode()
		request, err := http.NewRequest(http.MethodGet, endpoint.String(), nil)
		if err != nil {
			return err
		}
		if err = c.sign(request, nil); err != nil {
			return err
		}
		request.Header.Set("X-JMS-Event-Receipts", "1")
		dialContext, dialCancel := context.WithTimeout(ctx, c.options.Timeout)
		connection, response, err := websocket.Dial(dialContext, endpoint.String(), &websocket.DialOptions{HTTPClient: c.http, HTTPHeader: request.Header})
		dialCancel()
		if err != nil && response != nil {
			response.Body.Close()
		}
		if err == nil {
			received, handlerError := c.readEvents(ctx, connection, handler)
			if received {
				delay = time.Second
			}
			if handlerError != nil {
				return handlerError
			}
		}
		timer := time.NewTimer(delay)
		select {
		case <-ctx.Done():
			timer.Stop()
			return ctx.Err()
		case <-timer.C:
		}
		delay *= 2
		if delay > 30*time.Second {
			delay = 30 * time.Second
		}
	}
	return ctx.Err()
}

func (c *Client) readEvents(ctx context.Context, connection *websocket.Conn, handler func(Event) error) (received bool, err error) {
	connection.SetReadLimit(16 * 1024 * 1024)
	pingCtx, pingCancel := context.WithCancel(ctx)
	pingDone := make(chan struct{})
	go func() {
		defer close(pingDone)
		ticker := time.NewTicker(10 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-pingCtx.Done():
				return
			case <-ticker.C:
				writeCtx, done := context.WithTimeout(pingCtx, c.options.Timeout)
				connection.Write(writeCtx, websocket.MessageText, []byte(`{"event":"ping"}`))
				done()
			}
		}
	}()
	defer func() {
		pingCancel()
		connection.CloseNow()
		<-pingDone
	}()
	for ctx.Err() == nil {
		_, raw, readErr := connection.Read(ctx)
		if readErr != nil {
			break
		}
		var event Event
		if json.Unmarshal(raw, &event) != nil || event.Event == "" {
			break
		}
		received = true
		if event.Event == "pong" {
			continue
		}
		if event.Event != "snapshot" && event.EventID != "" {
			receipt, _ := json.Marshal(map[string]string{"event": "received", "event_id": event.EventID})
			writeCtx, done := context.WithTimeout(ctx, c.options.Timeout)
			connection.Write(writeCtx, websocket.MessageText, receipt)
			done()
		}
		if err = handler(event); err != nil {
			break
		}
	}
	return received, err
}
