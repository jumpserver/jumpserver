package pam

import "strings"

// Retain the latest successfully fetched credentials until authorization changes.

func (c *Client) reconcileLatestCredentials(event Event) {
	if event.Event != "snapshot" && event.Event != "credential.revoked" && event.Event != "configuration.updated" {
		return
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	c.credentialGeneration++
	if event.Event == "configuration.updated" {
		return
	}
	if event.Event != "snapshot" {
		key := event.CredentialKey
		if key == "" {
			key = event.Key
		}
		if key == "" && event.AccountID == "" {
			clear(c.latestCredentials)
		} else {
			for selector, credential := range c.latestCredentials {
				if (key != "" && (selector.Key == key || credential.Key == key || strings.HasPrefix(credential.Key, key+":"))) ||
					(event.AccountID != "" && (key == "" || strings.HasPrefix(key, "account:")) && (selector.AccountID == event.AccountID || credential.Account.ID == event.AccountID)) {
					delete(c.latestCredentials, selector)
				}
			}
		}
		return
	}
	keys := make(map[string]bool)
	for _, update := range event.Credentials {
		key := update.CredentialKey
		if key == "" {
			key = update.Key
		}
		keys[key] = true
	}
	for selector := range c.latestCredentials {
		// A push snapshot does not describe application pull authorization.
		if selector.Key != "" && !keys[selector.Key] {
			delete(c.latestCredentials, selector)
		}
	}
}
