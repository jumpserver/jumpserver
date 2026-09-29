package org.jumpserver.pam;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.WebSocket;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;
import java.util.function.Function;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.jumpserver.pam.Models.*;

/** Signed credential client for one stable application replica. */
public final class Client implements AutoCloseable {
  public static final String VERSION = "1.0.0";
  public static final int PROTOCOL_VERSION = 1, CONFIG_SCHEMA_VERSION = 1;
  private static final String PATH = "/api/v1/accounts/credential-client";
  private static final List<String> SIGNED =
      Arrays.asList(
          "(request-target)",
          "accept",
          "date",
          "digest",
          "x-jms-request-id",
          "x-jms-org",
          "x-jms-client-version",
          "x-jms-protocol-version",
          "x-jms-config-schema-version");
  private final Options options;
  private final ObjectMapper mapper = new ObjectMapper();
  private final ExecutorService executor =
      Executors.newCachedThreadPool(
          task -> {
            Thread thread = new Thread(task, "jms-pam-http");
            thread.setDaemon(true);
            return thread;
          });
  private final HttpClient http;
  private final Set<CompletableFuture<?>> requests = ConcurrentHashMap.newKeySet();
  private final Set<EventStream> streams = ConcurrentHashMap.newKeySet();
  private boolean closed;

  public static final class Options {
    private final String endpoint, appId, appSecret, instanceId;
    private String orgId = "00000000-0000-0000-0000-000000000002",
        configurationId,
        source = "jms-pam";
    private Duration timeout = Duration.ofSeconds(10);

    public Options(String endpoint, String appId, String appSecret, String instanceId) {
      this.endpoint = endpoint;
      this.appId = appId;
      this.appSecret = appSecret;
      this.instanceId = instanceId;
    }

    public Options orgId(String value) {
      if (value != null && !value.isEmpty()) orgId = value;
      return this;
    }

    public Options configurationId(String value) {
      configurationId = value;
      return this;
    }

    public Options source(String value) {
      source = value;
      return this;
    }

    public Options timeout(Duration value) {
      timeout = value;
      return this;
    }

    private Options copy() {
      return new Options(endpoint, appId, appSecret, instanceId)
          .orgId(orgId)
          .configurationId(configurationId)
          .source(source)
          .timeout(timeout);
    }
  }

  public Client(Options options) {
    this.options = options.copy();
    URI endpoint = URI.create(nonempty(options.endpoint, "endpoint"));
    if (!("http".equals(endpoint.getScheme()) || "https".equals(endpoint.getScheme()))
        || endpoint.getHost() == null
        || endpoint.getUserInfo() != null
        || endpoint.getRawQuery() != null
        || endpoint.getFragment() != null)
      throw new IllegalArgumentException("Invalid HTTP(S) endpoint");
    nonempty(options.appId, "appId");
    nonempty(options.appSecret, "appSecret");
    nonempty(options.instanceId, "instanceId");
    if (!options.instanceId.equals(options.instanceId.trim())
        || options.instanceId.length() > 128
        || options.timeout == null
        || options.timeout.isNegative()
        || options.timeout.isZero())
      throw new IllegalArgumentException("Invalid instanceId or timeout");
    http =
        HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(options.timeout)
            .followRedirects(HttpClient.Redirect.NEVER)
            .executor(executor)
            .build();
  }

  static String nonempty(String value, String name) {
    if (value == null || value.isEmpty()) throw new IllegalArgumentException(name + " is required");
    return value;
  }

  private Map<String, Object> identity(Map<String, Object> fields) {
    Map<String, Object> data = new LinkedHashMap<>(fields);
    data.put("instance_id", options.instanceId);
    if (options.configurationId != null && !options.configurationId.isEmpty())
      data.put("configuration_id", options.configurationId);
    return data;
  }

  private URI url(String path, Map<String, Object> query) {
    String endpoint = options.endpoint.replaceAll("/+$", "");
    List<String> params = new ArrayList<>();
    query.forEach(
        (name, value) ->
            params.add(
                URLEncoder.encode(name, StandardCharsets.UTF_8)
                    + "="
                    + URLEncoder.encode(value.toString(), StandardCharsets.UTF_8)));
    return URI.create(endpoint + path + (params.isEmpty() ? "" : "?" + String.join("&", params)));
  }

  Map<String, String> headers(String method, URI url, byte[] body) {
    try {
      Map<String, String> headers = new LinkedHashMap<>();
      headers.put("accept", "application/json");
      headers.put(
          "date",
          DateTimeFormatter.ofPattern("EEE, dd MMM yyyy HH:mm:ss 'GMT'", java.util.Locale.US)
              .format(ZonedDateTime.now(ZoneOffset.UTC)));
      headers.put(
          "digest",
          "SHA-256="
              + Base64.getEncoder()
                  .encodeToString(MessageDigest.getInstance("SHA-256").digest(body)));
      headers.put("x-jms-request-id", UUID.randomUUID().toString());
      headers.put("x-jms-org", options.orgId);
      headers.put("x-jms-client-version", VERSION);
      headers.put("x-jms-protocol-version", "1");
      headers.put(
          "x-jms-config-schema-version", "jms-pam-agent".equals(options.source) ? "1" : "0");
      headers.put("x-source", options.source);
      List<String> parts = new ArrayList<>();
      for (String name : SIGNED) {
        String value = headers.get(name);
        if (name.equals("(request-target)"))
          value =
              method.toLowerCase(java.util.Locale.ROOT)
                  + " "
                  + url.getRawPath()
                  + (url.getRawQuery() == null ? "" : "?" + url.getRawQuery());
        parts.add(name + ": " + value);
      }
      Mac mac = Mac.getInstance("HmacSHA256");
      mac.init(new SecretKeySpec(options.appSecret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
      String signature =
          Base64.getEncoder()
              .encodeToString(
                  mac.doFinal(String.join("\n", parts).getBytes(StandardCharsets.UTF_8)));
      headers.put(
          "authorization",
          "Signature keyId=\""
              + options.appId
              + "\",algorithm=\"hmac-sha256\",signature=\""
              + signature
              + "\",headers=\""
              + String.join(" ", SIGNED)
              + "\"");
      return headers;
    } catch (java.security.GeneralSecurityException error) {
      throw new IllegalStateException("Cannot sign request", error);
    }
  }

  private synchronized <T> CompletableFuture<T> track(CompletableFuture<T> future) {
    if (closed) {
      future.cancel(true);
      throw new IllegalStateException("Client is closed");
    }
    requests.add(future);
    future.whenComplete((result, error) -> requests.remove(future));
    return future;
  }

  private <T> T request(
      String method, String path, Map<String, Object> fields, Function<JsonNode, T> parse) {
    synchronized (this) {
      if (closed) throw new IllegalStateException("Client is closed");
    }
    Map<String, Object> data = identity(fields);
    byte[] body;
    try {
      body = method.equals("GET") ? new byte[0] : mapper.writeValueAsBytes(data);
    } catch (java.io.IOException error) {
      throw new IllegalArgumentException("Invalid request", error);
    }
    URI endpoint = url(PATH + path, method.equals("GET") ? data : Collections.emptyMap());
    HttpRequest.Builder builder = HttpRequest.newBuilder(endpoint).timeout(options.timeout);
    headers(method, endpoint, body).forEach(builder::header);
    if (method.equals("GET")) builder.GET();
    else
      builder
          .header("Content-Type", "application/json")
          .method(method, HttpRequest.BodyPublishers.ofByteArray(body));
    CompletableFuture<HttpResponse<byte[]>> future =
        track(http.sendAsync(builder.build(), HttpResponse.BodyHandlers.ofByteArray()));
    HttpResponse<byte[]> response;
    try {
      response = future.get(options.timeout.toMillis(), TimeUnit.MILLISECONDS);
    } catch (InterruptedException error) {
      future.cancel(true);
      Thread.currentThread().interrupt();
      throw new PAMException("NetworkError", 0, "HTTP request interrupted", null, error);
    } catch (Exception error) {
      future.cancel(true);
      throw new PAMException("NetworkError", 0, "HTTP request failed", null, error);
    }
    JsonNode payload;
    try {
      payload = Models.object(mapper.readTree(response.body()));
    } catch (Exception error) {
      throw new PAMException(
          "ResponseError", response.statusCode(), "The server returned invalid JSON", null, error);
    }
    if (response.statusCode() < 200 || response.statusCode() >= 300) {
      String code = payload.path("code").isTextual() ? payload.get("code").asText() : "HTTPError";
      String detail =
          payload.path("detail").isTextual()
              ? payload.get("detail").asText()
              : "HTTP request failed";
      String requestId =
          payload.path("request_id").isTextual() ? payload.get("request_id").asText() : null;
      throw new PAMException(
          code.isEmpty() ? "HTTPError" : code, response.statusCode(), detail, requestId, null);
    }
    try {
      return parse.apply(payload);
    } catch (RuntimeException error) {
      throw new PAMException(
          "ResponseError",
          response.statusCode(),
          "The server returned an invalid response",
          null,
          error);
    }
  }

  public Credential getCredential(String key) {
    return request("GET", "/credential/", Map.of("key", nonempty(key, "key")), Credential::new);
  }

  public Credential getCredentialByAccountId(String accountId) {
    return request(
        "GET",
        "/credential/",
        Map.of("account_id", nonempty(accountId, "accountId")),
        Credential::new);
  }

  public CredentialConfirmation confirmCredential(String key, long revision, String accountId) {
    if (revision < 1) throw new IllegalArgumentException("revision must be positive");
    return request(
        "POST",
        "/confirm/",
        Map.of(
            "key",
            nonempty(key, "key"),
            "revision",
            revision,
            "account_id",
            nonempty(accountId, "accountId")),
        CredentialConfirmation::new);
  }

  public AgentSync syncAgent(
      List<KnownRevision> credentials,
      List<KnownRevision> deliveredCredentials,
      String configDigest,
      String syncStatus,
      String syncError) {
    Map<String, Object> data = new LinkedHashMap<>();
    data.put("credentials", credentials);
    data.put("delivered_credentials", deliveredCredentials);
    data.put("config_digest", configDigest);
    data.put("sync_status", syncStatus);
    data.put("sync_error", syncError);
    if (credentials == null
        || deliveredCredentials == null
        || credentials.stream().anyMatch(java.util.Objects::isNull)
        || deliveredCredentials.stream().anyMatch(java.util.Objects::isNull))
      throw new IllegalArgumentException("Known revision lists are required");
    return request("POST", "/agent/sync/", data, payload -> new AgentSync(payload, mapper));
  }

  public List<Event> listApplicationCommands() {
    return request(
        "GET",
        "/commands/",
        Collections.emptyMap(),
        payload -> {
          if (!payload.path("commands").isArray())
            throw new IllegalArgumentException("commands must be an array");
          List<Event> commands = new ArrayList<>();
          for (JsonNode event : payload.get("commands")) commands.add(new Event(event));
          return Collections.unmodifiableList(commands);
        });
  }

  public CommandResult reportApplicationCommandResult(
      String commandId, String status, String errorCode) {
    if (!Arrays.asList("running", "success", "failed").contains(status))
      throw new IllegalArgumentException("Invalid command status");
    Map<String, Object> data = new LinkedHashMap<>();
    data.put("command_id", nonempty(commandId, "commandId"));
    data.put("status", status);
    if (errorCode != null) data.put("error_code", errorCode);
    return request("POST", "/command-result/", data, CommandResult::new);
  }

  public CommandResult executeApplicationCommand(Event event, Consumer<Event> handler) {
    if (handler == null) throw new IllegalArgumentException("handler is required");
    CommandResult claim = reportApplicationCommandResult(event.getCommandId(), "running", null);
    if (!claim.isAccepted()) return claim;
    try {
      handler.accept(event);
    } catch (RuntimeException error) {
      try {
        reportApplicationCommandResult(event.getCommandId(), "failed", "execution_failed");
      } catch (RuntimeException ignored) {
      }
      throw error;
    }
    return reportApplicationCommandResult(event.getCommandId(), "success", null);
  }

  public synchronized EventStream watchCredentialEvents() {
    if (closed) throw new IllegalStateException("Client is closed");
    EventStream stream = new EventStream(this, options.timeout, mapper);
    streams.add(stream);
    stream.start();
    return stream;
  }

  CompletableFuture<WebSocket> connectEvents(WebSocket.Listener listener) {
    URI httpUrl = url("/ws/accounts/credential-events/", identity(Collections.emptyMap()));
    URI url =
        URI.create(
            (httpUrl.getScheme().equals("https") ? "wss" : "ws")
                + httpUrl.toString().substring(httpUrl.getScheme().length()));
    WebSocket.Builder builder = http.newWebSocketBuilder().connectTimeout(options.timeout);
    headers("GET", url, new byte[0]).forEach(builder::header);
    builder.header("X-JMS-Event-Receipts", "1");
    return track(builder.buildAsync(url, listener));
  }

  void removeStream(EventStream stream) {
    streams.remove(stream);
  }

  public Client clone() {
    return new Client(options);
  }

  @Override
  public void close() {
    List<EventStream> activeStreams;
    synchronized (this) {
      if (closed) return;
      closed = true;
      activeStreams = new ArrayList<>(streams);
    }
    for (EventStream stream : activeStreams) stream.close();
    for (CompletableFuture<?> request : requests) request.cancel(true);
    executor.shutdownNow();
  }
}
