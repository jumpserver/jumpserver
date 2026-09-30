package pam

import (
	"context"
	"errors"
	"fmt"
	"log"
	"strings"
	"time"
)

// EventHandlers run serially, independently of the WebSocket reader. Credential
// handlers must be idempotent. Only the application may confirm a successful switch.
type EventHandlers struct {
	OnEvent             func(context.Context, Event) error
	OnCredentialChanged func(context.Context, Credential) error
	OnCredentialRevoked func(context.Context, Event) error
	OnError             func(context.Context, error, *Event)
}

// EventWatcher owns one managed event listener. Stop requests cancellation;
// Wait waits for handlers and the reader. Do not call Wait from a handler.
type EventWatcher struct {
	client   *Client
	ctx      context.Context
	cancel   context.CancelFunc
	handlers EventHandlers
	done     chan struct{}
	err      error
	pending  map[CredentialSelector]pendingCredential
}

type pendingCredential struct {
	update Event
	event  Event
	delay  time.Duration
	due    time.Time
}

func (c *Client) StartEvents(ctx context.Context, handlers EventHandlers) (*EventWatcher, error) {
	if ctx == nil {
		return nil, fmt.Errorf("context is required")
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.closed {
		return nil, errors.New("client is closed")
	}
	if c.watcher != nil {
		select {
		case <-c.watcher.done:
		default:
			return nil, errors.New("an event listener is already running")
		}
	}
	ctx, cancel := context.WithCancel(ctx)
	w := &EventWatcher{client: c, ctx: ctx, cancel: cancel, handlers: handlers,
		done: make(chan struct{}), pending: make(map[CredentialSelector]pendingCredential)}
	c.watcher = w
	go w.run()
	return w, nil
}

// WatchEvents blocks until ctx is canceled, Client.Close is called, or the reader
// fails. Credential handler errors are reported and retried, not returned here.
func (c *Client) WatchEvents(ctx context.Context, handlers EventHandlers) error {
	w, err := c.StartEvents(ctx, handlers)
	if err != nil {
		return err
	}
	return w.Wait()
}

func (w *EventWatcher) Stop() { w.cancel() }
func (w *EventWatcher) Wait() error {
	<-w.done
	return w.err
}

func (w *EventWatcher) report(err error, event *Event) {
	if w.ctx.Err() != nil {
		return
	}
	if w.handlers.OnError != nil {
		w.handlers.OnError(w.ctx, err, event)
	} else {
		// Exception messages and event payloads can contain credential material.
		log.Printf("Credential event handler failed: %T", err)
	}
}

func eventSelector(event Event) (CredentialSelector, bool) {
	key := event.CredentialKey
	if key == "" {
		key = event.Key
	}
	if event.CredentialMode == "subscription" && key != "" && event.AccountID != "" {
		if !strings.HasSuffix(key, ":"+event.AccountID) {
			key += ":" + event.AccountID
		}
		return CredentialSelector{Key: key}, true
	}
	if event.CredentialMode == "alternating_rotation" && key != "" {
		return CredentialSelector{Key: key}, true
	}
	return CredentialSelector{}, false
}

func (w *EventWatcher) refresh(update, event Event, delay time.Duration) {
	selector, valid := eventSelector(update)
	if !valid || w.ctx.Err() != nil {
		return
	}
	if previous, exists := w.pending[selector]; exists && previous.update.Revision > update.Revision {
		return
	}
	credential, err := w.client.GetCredentialFresh(w.ctx, selector)
	if err == nil && credential.Revision < update.Revision {
		err = errors.New("credential API revision is behind the event")
	}
	if err == nil && w.ctx.Err() == nil && w.handlers.OnCredentialChanged != nil {
		err = w.handlers.OnCredentialChanged(w.ctx, credential)
	}
	if w.ctx.Err() != nil {
		return
	}
	if err != nil {
		w.report(err, &event)
		delay *= 2
		if delay < time.Second {
			delay = time.Second
		}
		if delay > 30*time.Second {
			delay = 30 * time.Second
		}
		w.pending[selector] = pendingCredential{update, event, delay, time.Now().Add(delay)}
	} else {
		delete(w.pending, selector)
	}
}

func (w *EventWatcher) dispatch(event Event) {
	if event.Event == "snapshot" || event.Event == "credential.revoked" || event.Event == "configuration.updated" {
		clear(w.pending)
	}
	if w.handlers.OnEvent != nil {
		if err := w.handlers.OnEvent(w.ctx, event); err != nil {
			w.report(err, &event)
		}
	}
	if w.ctx.Err() != nil {
		return
	}
	switch event.Event {
	case "snapshot":
		for _, update := range event.Credentials {
			w.refresh(update, event, 0)
		}
	case "credential.updated":
		if event.CommandID == "" {
			w.refresh(event, event, 0)
		}
	case "credential.revoked":
		if w.handlers.OnCredentialRevoked != nil {
			if err := w.handlers.OnCredentialRevoked(w.ctx, event); err != nil {
				w.report(err, &event)
			}
		}
	}
}

func (w *EventWatcher) retry() {
	var earliest *pendingCredential
	for _, item := range w.pending {
		if earliest == nil || item.due.Before(earliest.due) {
			copy := item
			earliest = &copy
		}
	}
	if earliest != nil && !earliest.due.After(time.Now()) {
		w.refresh(earliest.update, earliest.event, earliest.delay)
	}
}

func (w *EventWatcher) run() {
	release := context.AfterFunc(w.client.stop, w.cancel)
	defer release()
	if w.client.stop.Err() != nil {
		w.cancel()
	}
	events := make(chan Event, 128)
	readerDone := make(chan struct{})
	var readerErr error
	go func() {
		readerErr = w.client.WatchCredentialEvents(w.ctx, func(event Event) error {
			select {
			case events <- event:
				return nil
			case <-w.ctx.Done():
				return w.ctx.Err()
			}
		})
		close(events)
		close(readerDone)
	}()
	defer func() {
		w.cancel()
		<-readerDone
		clear(w.pending)
		close(w.done)
	}()
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()
	for {
		select {
		case <-w.ctx.Done():
			w.err = w.ctx.Err()
			return
		case event, open := <-events:
			if !open {
				<-readerDone
				w.err = readerErr
				if w.err != nil {
					w.report(w.err, nil)
				}
				return
			}
			w.dispatch(event)
			w.retry()
		case <-ticker.C:
			w.retry()
		}
	}
}
