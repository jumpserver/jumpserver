package org.jumpserver.pam;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.jumpserver.pam.Models.*;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class ClientTest {
  private static String endpoint;

  @BeforeAll
  static void setup() {
    endpoint = System.getenv("JMS_TEST_ENDPOINT");
    assumeTrue(endpoint != null, "Use clients/tests/run.py for protocol tests");
  }

  private Client client(String instance, String source) {
    return new Client(
        new Client.Options(endpoint, "contract-app", "contract-secret", instance)
            .orgId("contract-org")
            .configurationId("configuration")
            .source(source));
  }

  @Test
  void automaticSigningAndStructuredResponses() {
    try (Client sdk = client("java", "jms-pam")) {
      for (Credential item :
          List.of(sdk.getCredentialByAccountId("account"), sdk.getCredential("db/空 格?=&"))) {
        assertEquals("DO_NOT_LOG_SECRET", item.getAccount().getSecret());
        assertEquals("password", item.getAccount().getSecretType());
        assertEquals("postgresql", item.getAsset().getPlatform().getType());
        assertFalse(item.toString().contains(item.getAccount().getSecret()));
        assertFalse(item.getAccount().toString().contains(item.getAccount().getSecret()));
      }
      assertEquals(2, sdk.confirmCredential("db", 2, "account").getRevision());
      assertThrows(IllegalArgumentException.class, () -> sdk.getCredential(""));
      assertThrows(IllegalArgumentException.class, () -> sdk.confirmCredential("db", 0, "account"));
    }
  }

  @Test
  void errorsAndUpgradeAreExplicit() {
    try (Client sdk = client("java-errors", "jms-pam")) {
      Map<String, String> cases =
          Map.of(
              "forbidden",
              "credential_not_authorized",
              "upgrade",
              "client_upgrade_required",
              "invalid-json",
              "ResponseError",
              "invalid-revision",
              "ResponseError",
              "redirect",
              "HTTPError");
      cases.forEach(
          (key, code) ->
              assertEquals(
                  code, assertThrows(PAMException.class, () -> sdk.getCredential(key)).getCode()));
    }
  }

  @Test
  void synchronizationValidatesMetadata() {
    try (Client sdk = client("java-agent", "jms-pam-agent")) {
      List<KnownRevision> known = List.of(new KnownRevision("db", 2));
      AgentSync sync = sdk.syncAgent(known, List.of(), "", "", "");
      assertFalse(sync.getCredentials().get(0).isChanged());
      assertEquals("socket", sync.getConfiguration().get("delivery_mode"));
      assertEquals(
          "ResponseError",
          assertThrows(
                  PAMException.class, () -> sdk.syncAgent(known, List.of(), "", "", "invalid-flag"))
              .getCode());
    }
  }

  @Test
  void commandsClaimOnceAndPreserveHandlerException() {
    try (Client sdk = client("java-command", "jms-pam")) {
      Event event = sdk.listApplicationCommands().get(0);
      int[] executed = {0};
      assertEquals(
          "success", sdk.executeApplicationCommand(event, command -> executed[0]++).getStatus());
      assertEquals(1, executed[0]);
      ObjectMapper mapper = new ObjectMapper();
      Event duplicate =
          new Event(
              mapper.valueToTree(
                  Map.of("event", "application.restart.requested", "command_id", "duplicate")));
      assertFalse(sdk.executeApplicationCommand(duplicate, command -> executed[0]++).isAccepted());
      assertEquals(1, executed[0]);
      RuntimeException failure = new RuntimeException("business failure");
      Event rejected =
          new Event(
              mapper.valueToTree(
                  Map.of(
                      "event", "application.restart.requested", "command_id", "report-failure")));
      assertSame(
          failure,
          assertThrows(
              RuntimeException.class,
              () ->
                  sdk.executeApplicationCommand(
                      rejected,
                      command -> {
                        throw failure;
                      })));
    }
  }

  @Test
  void reconnectReceiptsAndStreamClosure() throws Exception {
    List<Event> events = new ArrayList<>();
    try (Client sdk = client("java-events", "jms-pam")) {
      assertTimeoutPreemptively(
          Duration.ofSeconds(6),
          () -> {
            try (EventStream stream = sdk.watchCredentialEvents()) {
              for (Event event : stream) {
                events.add(event);
                if (events.size() == 4) break;
              }
            }
          });
      assertEquals(
          List.of("snapshot", "credential.updated", "future.notification", "snapshot"),
          events.stream().map(Event::getEvent).collect(java.util.stream.Collectors.toList()));
      assertEquals(3, events.get(3).getCredentials().get(0).getRevision());
      assertEquals(
          "preserved", events.get(2).getData().path("future_payload").path("notice").asText());
      String statsUrl = endpoint.substring(0, endpoint.length() - "/prefix".length()) + "/__stats";
      JsonNode stats =
          new ObjectMapper()
              .readTree(
                  HttpClient.newBuilder()
                      .version(HttpClient.Version.HTTP_1_1)
                      .build()
                      .send(
                          HttpRequest.newBuilder(URI.create(statsUrl)).build(),
                          HttpResponse.BodyHandlers.ofString())
                      .body());
      List<String> receipts = new ArrayList<>();
      for (JsonNode receipt : stats.get("receipts"))
        if (receipt.path("instance").asText().equals("java-events"))
          receipts.add(receipt.path("eventId").asText());
      assertTrue(receipts.contains("updated-1"));
      assertTrue(receipts.contains("future-1"));
      try (Client copy = sdk.clone();
          EventStream stream = sdk.watchCredentialEvents()) {
        sdk.close();
        assertFalse(stream.iterator().hasNext());
        assertEquals(2, copy.getCredential("db").getRevision());
      }
    }
  }
}
