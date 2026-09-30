package org.jumpserver.pam;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Immutable responses; unknown optional fields are tolerated. */
public final class Models {
  private Models() {}

  static JsonNode object(JsonNode value) {
    if (value == null || !value.isObject())
      throw new IllegalArgumentException("Expected an object");
    return value;
  }

  static String string(JsonNode value, String name) {
    JsonNode field = object(value).get(name);
    if (field == null || !field.isTextual() || field.asText().isEmpty())
      throw new IllegalArgumentException("Invalid " + name);
    return field.asText();
  }

  static long revision(JsonNode value) {
    JsonNode field = object(value).get("revision");
    if (field == null
        || !field.isIntegralNumber()
        || !field.canConvertToLong()
        || field.asLong() < 0) throw new IllegalArgumentException("Invalid revision");
    return field.asLong();
  }

  static boolean bool(JsonNode value, String name) {
    JsonNode field = object(value).get(name);
    if (field == null || !field.isBoolean()) throw new IllegalArgumentException("Invalid " + name);
    return field.asBoolean();
  }

  public static final class Platform {
    private final String id, name, category, type;

    Platform(JsonNode value) {
      id = string(value, "id");
      name = string(value, "name");
      category = string(value, "category");
      type = string(value, "type");
    }

    public String getId() {
      return id;
    }

    public String getName() {
      return name;
    }

    public String getCategory() {
      return category;
    }

    public String getType() {
      return type;
    }
  }

  public static final class Asset {
    private final String id, name, address;
    private final Platform platform;

    Asset(JsonNode value) {
      id = string(value, "id");
      name = string(value, "name");
      address = string(value, "address");
      platform = new Platform(value.get("platform"));
    }

    public String getId() {
      return id;
    }

    public String getName() {
      return name;
    }

    public String getAddress() {
      return address;
    }

    public Platform getPlatform() {
      return platform;
    }
  }

  public static final class Account {
    private final String id, name, username, secretType, secret;

    Account(JsonNode value) {
      id = string(value, "id");
      name = string(value, "name");
      username = string(value, "username");
      secretType = string(value, "secret_type");
      secret = string(value, "secret");
    }

    public String getId() {
      return id;
    }

    public String getName() {
      return name;
    }

    public String getUsername() {
      return username;
    }

    public String getSecretType() {
      return secretType;
    }

    public String getSecret() {
      return secret;
    }

    @Override
    public String toString() {
      return "Account{id=" + id + ", secret=[REDACTED]}";
    }
  }

  public static final class Credential {
    private final String key;
    private final long revision;
    private final Asset asset;
    private final Account account;
    private final boolean fromLocal;

    Credential(JsonNode value) {
      key = string(value, "key");
      revision = revision(value);
      asset = new Asset(value.get("asset"));
      account = new Account(value.get("account"));
      fromLocal = false;
    }

    private Credential(Credential value) {
      key = value.key;
      revision = value.revision;
      asset = value.asset;
      account = value.account;
      fromLocal = true;
    }

    Credential localCopy() {
      return new Credential(this);
    }

    public boolean isFromLocal() {
      return fromLocal;
    }

    public String getKey() {
      return key;
    }

    public long getRevision() {
      return revision;
    }

    public Asset getAsset() {
      return asset;
    }

    public Account getAccount() {
      return account;
    }

    @Override
    public String toString() {
      return "Credential{key=" + key + ", revision=" + revision + "}";
    }
  }

  public static final class CredentialConfirmation {
    private final String key;
    private final long revision;

    CredentialConfirmation(JsonNode value) {
      key = string(value, "key");
      revision = revision(value);
    }

    public String getKey() {
      return key;
    }

    public long getRevision() {
      return revision;
    }
  }

  public static final class KnownRevision {
    private final String key;
    private final long revision;

    public KnownRevision(String key, long revision) {
      if (key == null || key.isEmpty() || revision < 0)
        throw new IllegalArgumentException("Invalid known revision");
      this.key = key;
      this.revision = revision;
    }

    public String getKey() {
      return key;
    }

    public long getRevision() {
      return revision;
    }
  }

  public static final class CredentialRevision {
    private final String key;
    private final long revision;
    private final boolean available, changed;

    CredentialRevision(JsonNode value) {
      key = string(value, "key");
      revision = revision(value);
      available = bool(value, "available");
      changed = bool(value, "changed");
    }

    public String getKey() {
      return key;
    }

    public long getRevision() {
      return revision;
    }

    public boolean isAvailable() {
      return available;
    }

    public boolean isChanged() {
      return changed;
    }
  }

  public static final class AgentSync {
    private final String configDigest, dateLastSynced;
    private final List<CredentialRevision> credentials;
    private final List<String> removedKeys;
    private final Map<String, Object> scope;

    AgentSync(JsonNode value, ObjectMapper mapper) {
      configDigest = string(value, "config_digest");
      dateLastSynced = string(value, "date_last_synced");
      if (!value.path("credentials").isArray() || !value.path("removed_keys").isArray())
        throw new IllegalArgumentException("Invalid sync metadata");
      List<CredentialRevision> revisions = new ArrayList<>();
      Set<String> keys = new HashSet<>();
      for (JsonNode item : value.get("credentials")) {
        CredentialRevision entry = new CredentialRevision(item);
        if (!keys.add(entry.key)) throw new IllegalArgumentException("Duplicate revision keys");
        revisions.add(entry);
      }
      credentials = Collections.unmodifiableList(revisions);
      List<String> removed = new ArrayList<>();
      for (JsonNode key : value.get("removed_keys")) {
        if (!key.isTextual() || key.asText().isEmpty())
          throw new IllegalArgumentException("Invalid removed key");
        removed.add(key.asText());
      }
      removedKeys = Collections.unmodifiableList(removed);
      JsonNode config = value.get("scope");
      scope =
          config == null || config.isNull()
              ? null
              : Collections.unmodifiableMap(
                  mapper.convertValue(object(config), new TypeReference<Map<String, Object>>() {}));
    }

    public String getConfigDigest() {
      return configDigest;
    }

    public String getDateLastSynced() {
      return dateLastSynced;
    }

    public List<CredentialRevision> getCredentials() {
      return credentials;
    }

    public List<String> getRemovedKeys() {
      return removedKeys;
    }

    public Map<String, Object> getScope() {
      return scope;
    }
  }

  public static final class CommandResult {
    private final boolean accepted;
    private final String status;

    CommandResult(JsonNode value) {
      accepted = bool(value, "accepted");
      status = string(value, "status");
    }

    public boolean isAccepted() {
      return accepted;
    }

    public String getStatus() {
      return status;
    }
  }

  public static final class Event {
    private final JsonNode data;

    Event(JsonNode data) {
      this.data = object(data).deepCopy();
    }

    public String getEvent() {
      return data.path("event").asText("");
    }

    public String getEventId() {
      return data.path("event_id").asText("");
    }

    public String getCommandId() {
      return data.path("command_id").asText("");
    }

    public String getKey() {
      return data.path("credential_key").asText(data.path("key").asText(""));
    }

    public String getCredentialMode() {
      return data.path("credential_mode").asText("");
    }

    public String getAccountId() {
      return data.path("account_id").asText("");
    }

    public long getRevision() {
      return revision(data);
    }

    public List<Event> getCredentials() {
      List<Event> items = new ArrayList<>();
      JsonNode credentials = data.get("credentials");
      if (credentials != null) {
        if (!credentials.isArray()) throw new IllegalArgumentException("Invalid snapshot");
        for (JsonNode item : credentials) items.add(new Event(item));
      }
      return Collections.unmodifiableList(items);
    }

    public JsonNode getData() {
      return data.deepCopy();
    }
  }
}
