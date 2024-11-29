package main

import (
    "encoding/json"
    "fmt"
    "net/http"
    "net/url"

    "github.com/google/uuid"
    "gopkg.in/twindagger/httpsig.v1"
)

const DefaultOrgId = "00000000-0000-0000-0000-000000000002"

type RequestParamsError struct {
	Params []string
}

func (e *RequestParamsError) Error() string {
	return fmt.Sprintf("At least one of the following fields must be provided: %v.", e.Params)
}

type SecretRequest struct {
	AccountID string
	AssetID   string
	Asset     string
	Account   string
	Method    string
}

func NewSecretRequest(asset, assetID, account, accountID string) (*SecretRequest, error) {
	req := &SecretRequest{
		Asset:     asset,
		AssetID:   assetID,
		Account:   account,
		AccountID: accountID,
		Method:    http.MethodGet,
	}

	return req, req.validate()
}

func (r *SecretRequest) validate() error {
	if r.AccountID != "" {
        if _, err := uuid.Parse(r.AccountID); err != nil {
            return fmt.Errorf("invalid UUID: %s. Value must be a valid UUID", r.AccountID)
        }
		return nil
	}

	if r.AssetID == "" && r.Asset == "" {
		return &RequestParamsError{Params: []string{"asset", "asset_id"}}
	}

	if r.Account == "" {
		return &RequestParamsError{Params: []string{"account", "account_id"}}
	}

	if r.AssetID != "" {
		if _, err := uuid.Parse(r.AssetID); err != nil {
			return fmt.Errorf("invalid UUID: %s. Value must be a valid UUID", r.AssetID)
		}
	}
	return nil
}

func (r *SecretRequest) GetURL() string {
	return "/api/v1/accounts/service-integrations/account-secret/"
}

func (r *SecretRequest) GetQuery() url.Values {
	query := url.Values{}
	if r.AccountID != "" {
		query.Add("account_id", r.AccountID)
	}
	if r.AssetID != "" {
		query.Add("asset_id", r.AssetID)
	}
	if r.Asset != "" {
		query.Add("asset", r.Asset)
	}
	if r.Account != "" {
		query.Add("account", r.Account)
	}
	return query
}

type Secret struct {
	Secret string          `json:"secret,omitempty"`
	Desc   json.RawMessage `json:"desc,omitempty"`
	Valid  bool            `json:"valid"`
}

func FromResponse(response *http.Response) Secret {
	var secret Secret
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		var raw json.RawMessage
		if err := json.NewDecoder(response.Body).Decode(&raw); err == nil {
			secret.Desc = raw
		} else {
			secret.Desc = json.RawMessage(`{"error": "Unknown error occurred"}`)
		}
	} else {
		_ = json.NewDecoder(response.Body).Decode(&secret)
		secret.Valid = true
	}
	return secret
}

type JumpServerPAM struct {
	Endpoint   string
	KeyID      string
	KeySecret  string
	OrgID      string
	httpClient *http.Client
}

func NewJumpServerPAM(endpoint, keyID, keySecret, orgID string) *JumpServerPAM {
	if orgID == "" {
		orgID = DefaultOrgId
	}
	return &JumpServerPAM{
		Endpoint:   endpoint,
		KeyID:      keyID,
		KeySecret:  keySecret,
		OrgID:      orgID,
		httpClient: &http.Client{},
	}
}

func (c *JumpServerPAM) SignRequest(r *http.Request) error {
	headers := []string{"(request-target)", "date"}
	signer, err := httpsig.NewRequestSigner(c.KeyID, c.KeySecret, "hmac-sha256")
	if err != nil {
		return err
	}
	return signer.SignRequest(r, headers, nil)
}

func (c *JumpServerPAM) Send(req *SecretRequest) (Secret, error) {
	fullUrl := c.Endpoint + req.GetURL()
	query := req.GetQuery()
	fullURL := fmt.Sprintf("%s?%s", fullUrl, query.Encode())

	request, err := http.NewRequest(req.Method, fullURL, nil)
	if err != nil {
		return Secret{}, err
	}
	request.Header.Set("Accept", "application/json")
	request.Header.Set("X-Source", "jms-pam")
	err = c.SignRequest(request)
	if err != nil {
		return Secret{Desc: json.RawMessage(`{"error": "` + err.Error() + `"}`)}, nil
	}
	response, err := c.httpClient.Do(request)
	if err != nil {
		return Secret{Desc: json.RawMessage(`{"error": "` + err.Error() + `"}`)}, nil
	}

	return FromResponse(response), nil
}
