package agent

import (
	"context"
	"errors"
	"sort"

	pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
)

type AccountsResult struct {
	Accounts []pam.AuthorizedAccount `json:"accounts"`
	Source   string                  `json:"source"`
}

type CredentialResult struct {
	Credential
	Source string `json:"source"`
}

func temporary(ctx context.Context, err error) bool {
	var failure *pam.PAMError
	return ctx.Err() == nil && errors.As(err, &failure) && (failure.Code == "NetworkError" || (failure.StatusCode >= 500 && failure.StatusCode < 600))
}

// Accounts lists metadata without fetching passwords. Offline results contain
// only the accounts with retained credentials still authorized by the Agent.
func (a *Agent) Accounts(ctx context.Context) (AccountsResult, error) {
	a.syncMu.Lock()
	defer a.syncMu.Unlock()
	return a.accounts(ctx)
}

func (a *Agent) accounts(ctx context.Context) (AccountsResult, error) {
	accounts, err := a.remote.ListAuthorizedAccounts(ctx)
	if err != nil {
		if !temporary(ctx, err) {
			return AccountsResult{}, a.failure(err, true)
		}
		a.mu.Lock()
		defer a.mu.Unlock()
		if a.state.Denied {
			return AccountsResult{}, errors.New("agent_access_denied")
		}
		byAccount := map[string]*pam.AuthorizedAccount{}
		for _, key := range sortedKeys(a.state.Latest) {
			value := a.state.Latest[key]
			if !a.state.Authorized[key] {
				continue
			}
			account := byAccount[value.AccountID]
			if account == nil {
				account = &pam.AuthorizedAccount{ID: value.AccountID, Name: value.Account, Username: value.Username, SecretType: value.SecretType, Asset: pam.Asset{ID: value.AssetID, Name: value.Asset, Address: value.Address}}
				byAccount[value.AccountID] = account
			}
			mode := "subscription"
			if contains(a.state.Scope.ConfirmationKeys, key) {
				mode = "alternating_rotation"
			}
			account.Credentials = append(account.Credentials, pam.AccountPolicy{Key: key, Revision: value.Revision, Mode: mode})
		}
		result := AccountsResult{Accounts: []pam.AuthorizedAccount{}, Source: "local"}
		for _, value := range byAccount {
			result.Accounts = append(result.Accounts, *value)
		}
		sort.Slice(result.Accounts, func(i, j int) bool { return result.Accounts[i].ID < result.Accounts[j].ID })
		return result, nil
	}
	// A signed list may revoke an account or change the active rotation account.
	// Metadata alone never restores access to a previously revoked password.
	allowed := map[string]string{}
	for _, account := range accounts {
		for _, policy := range account.Credentials {
			allowed[policy.Key] = account.ID
		}
	}
	a.mu.Lock()
	for key := range a.state.Authorized {
		if allowed[key] != a.state.Latest[key].AccountID {
			delete(a.state.Authorized, key)
			if allowed[key] == "" {
				delete(a.state.Wanted, key)
			}
		}
	}
	err = a.persist()
	a.mu.Unlock()
	return AccountsResult{Accounts: accounts, Source: "api"}, err
}

func (a *Agent) retainedAccount(accountID string) (CredentialResult, error) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.state.Denied {
		return CredentialResult{}, errors.New("agent_access_denied")
	}
	for _, key := range sortedKeys(a.state.Latest) {
		value := a.state.Latest[key]
		if a.state.Authorized[key] && value.AccountID == accountID {
			return CredentialResult{Credential: value, Source: "local"}, nil
		}
	}
	return CredentialResult{}, errors.New("credential_not_authorized")
}

// AccountCredential requires live authorization and a current API value first.
// Only a temporary backend failure permits the retained, still-authorized value.
func (a *Agent) AccountCredential(ctx context.Context, accountID string) (CredentialResult, error) {
	a.syncMu.Lock()
	defer a.syncMu.Unlock()
	if accountID == "" {
		return CredentialResult{}, errors.New("account_id_required")
	}
	value, err := a.remote.GetCredentialFresh(ctx, pam.CredentialSelector{AccountID: accountID})
	if err != nil {
		if temporary(ctx, err) {
			return a.retainedAccount(accountID)
		}
		var failure *pam.PAMError
		if errors.As(err, &failure) && (failure.StatusCode == 403 || failure.StatusCode == 404) {
			a.mu.Lock()
			for key, retained := range a.state.Latest {
				if retained.AccountID == accountID {
					delete(a.state.Authorized, key)
					delete(a.state.Wanted, key)
				}
			}
			persistence := a.persist()
			a.mu.Unlock()
			return CredentialResult{}, errors.Join(a.failure(err, false), persistence)
		}
		return CredentialResult{}, a.failure(err, true)
	}
	if value.Account.ID != accountID || value.Key != "account:"+accountID {
		return CredentialResult{}, errors.New("invalid_credential_response")
	}
	a.mu.Lock()
	for key, retained := range a.state.Latest {
		if retained.AccountID == accountID && retained.Secret != value.Account.Secret {
			delete(a.state.Authorized, key)
			delete(a.state.Wanted, key)
		}
	}
	err = a.persist()
	a.mu.Unlock()
	if err != nil {
		return CredentialResult{}, err
	}
	return CredentialResult{Credential: flatten(value), Source: "api"}, nil
}
