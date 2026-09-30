package org.jumpserver.pam;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.jumpserver.pam.Models.*;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class EventHandlerTest {
  private static String endpoint;

  @BeforeAll
  static void setup() {
    endpoint = System.getenv("JMS_TEST_ENDPOINT");
    assumeTrue(endpoint != null, "Use clients/tests/run.py");
  }

  private Client.Options options(String id) {
    return new Client.Options(endpoint, "contract-app", "contract-secret", id)
        .orgId("contract-org");
  }

  private void control(String instance, String query) throws Exception {
    URI uri =
        URI.create(
            endpoint.replace("/prefix", "") + "/__control?instance=" + instance + "&" + query);
    assertEquals(
        200,
        HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .build()
            .send(HttpRequest.newBuilder(uri).GET().build(), HttpResponse.BodyHandlers.discarding())
            .statusCode());
  }

  @Test
  void updateEventRefreshesRetainedLatestAndApiIsPreferredOnline() throws Exception {
    String instance = "latest-java-events";
    try (Client sdk = new Client(options(instance))) {
      CountDownLatch initial = new CountDownLatch(1), updated = new CountDownLatch(1);
      try (EventSubscription subscription =
          sdk.startEvents(
              new CredentialEventListener() {
                public void onCredentialChanged(Credential value) {
                  assertFalse(value.isFromLocal());
                  if (value.getRevision() >= 3) updated.countDown();
                  else initial.countDown();
                }

                public void onEventError(Exception error, Event event) {}
              })) {
        assertTrue(initial.await(5, TimeUnit.SECONDS));
        control(instance, "revision=3&event=credential.updated");
        assertTrue(updated.await(5, TimeUnit.SECONDS));
        control(instance, "fault=503");
        Credential retained = sdk.getCredential("db");
        assertTrue(retained.isFromLocal());
        assertEquals(3, retained.getRevision());
        assertEquals("LATEST_SECRET_3", retained.getAccount().getSecret());
        control(instance, "fault=0&revision=4");
        Credential live = sdk.getCredential("db");
        assertFalse(live.isFromLocal());
        assertEquals(4, live.getRevision());
        control(instance, "revision=2");
        assertThrows(PAMException.class, () -> sdk.getCredential("db"));
        control(instance, "fault=503");
        assertEquals(4, sdk.getCredential("db").getRevision());
      }
    }
  }

  @Test
  void cacheOnlyOnTransientFailures() {
    for (String fault :
        List.of("503", "timeout", "401", "403", "404", "426", "revoked", "invalid")) {
      try (Client sdk = new Client(options("java-cache-" + fault).timeout(Duration.ofSeconds(1)))) {
        String key = "cache-" + fault;
        Credential live = sdk.getCredential(key);
        assertFalse(live.isFromLocal());
        if (fault.equals("503") || fault.equals("timeout")) {
          Credential cached = sdk.getCredential(key);
          assertTrue(cached.isFromLocal());
          assertEquals(live.getAccount().getSecret(), cached.getAccount().getSecret());
          assertThrows(PAMException.class, () -> sdk.getCredential(key, false));
        } else assertThrows(PAMException.class, () -> sdk.getCredential(key));
      }
    }
  }

  @Test
  void retainsLatestUntilRevocationAndCloneStartsEmpty() throws Exception {
    for (String change : List.of("retain", "scope", "revoked", "configuration")) {
      try (Client sdk = new Client(options("java-latest-" + change))) {
        sdk.getCredential("cache-503");
        if (change.equals("scope"))
          sdk.reconcileLatestCredentials(
              new Event(
                  new ObjectMapper().readTree("{\"event\":\"snapshot\",\"credentials\":[]}")));
        if (change.equals("revoked") || change.equals("configuration"))
          sdk.reconcileLatestCredentials(
              new Event(
                  new ObjectMapper()
                      .readTree(
                          "{\"event\":\""
                              + (change.equals("revoked")
                                  ? "credential.revoked"
                                  : "configuration.updated")
                              + "\"}")));
        if (change.equals("retain") || change.equals("configuration")) {
          assertTrue(sdk.getCredential("cache-503").isFromLocal());
          assertTrue(sdk.getCredential("cache-503").isFromLocal());
        } else assertThrows(PAMException.class, () -> sdk.getCredential("cache-503"));
        try (Client clone = sdk.clone()) {
          assertThrows(PAMException.class, () -> clone.getCredential("cache-503"));
        }
      }
    }
  }

  @Test
  void policyRevocationRemovesSubscriptionAccountAlias() throws Exception {
    String instance = "latest-java-revoked-alias";
    try (Client sdk = new Client(options(instance))) {
      sdk.getCredential("db:account");
      control(instance, "fault=503");
      assertTrue(sdk.getCredential("db:account").isFromLocal());
      sdk.reconcileLatestCredentials(
          new Event(
              new ObjectMapper()
                  .readTree("{\"event\":\"credential.revoked\",\"credential_key\":\"db\"}")));
      assertThrows(PAMException.class, () -> sdk.getCredential("db:account"));
    }
  }

  @Test
  void reconnectSnapshotAndSelfClose() throws Exception {
    try (Client sdk = new Client(options("hooks-java"))) {
      CountDownLatch applied = new CountDownLatch(1);
      AtomicInteger errors = new AtomicInteger();
      EventSubscription sub =
          sdk.startEvents(
              new CredentialEventListener() {
                public void onCredentialChanged(Credential c) {
                  assertFalse(c.isFromLocal());
                  if (c.getRevision() >= 3) {
                    sdk.close();
                    applied.countDown();
                  }
                }

                public void onEventError(Exception error, Event event) {
                  errors.incrementAndGet();
                }
              });
      try {
        assertTrue(applied.await(5, TimeUnit.SECONDS));
        sub.awaitTermination();
        assertEquals(0, errors.get());
      } finally {
        sub.close();
      }
    }
  }

  @Test
  void retryWithoutNewEventsAndDuplicateListener() throws Exception {
    try (Client sdk = new Client(options("retry-java"))) {
      CountDownLatch applied = new CountDownLatch(1);
      AtomicInteger calls = new AtomicInteger(), errors = new AtomicInteger();
      try (EventSubscription sub =
          sdk.startEvents(
              new CredentialEventListener() {
                public void onCredentialChanged(Credential c) throws Exception {
                  if (calls.incrementAndGet() == 1) throw new Exception("temporary failure");
                  applied.countDown();
                }

                public void onEventError(Exception error, Event event) {
                  errors.incrementAndGet();
                }
              })) {
        assertThrows(IllegalStateException.class, () -> sdk.startEvents(c -> {}));
        assertTrue(applied.await(4, TimeUnit.SECONDS));
        assertEquals(2, calls.get());
        assertEquals(1, errors.get());
      }
      try (EventSubscription restarted = sdk.startEvents(c -> {})) {
        assertTrue(restarted.isRunning());
      }
    }
  }

  @Test
  void staleRevisionIsNotApplied() throws Exception {
    try (Client sdk = new Client(options("java-stale"))) {
      CountDownLatch stale = new CountDownLatch(1);
      AtomicInteger calls = new AtomicInteger();
      try (EventSubscription sub =
          sdk.startEvents(
              new CredentialEventListener() {
                public void onCredentialChanged(Credential c) {
                  calls.incrementAndGet();
                }

                public void onEventError(Exception error, Event event) {
                  if (error instanceof IllegalStateException) stale.countDown();
                }
              })) {
        assertTrue(stale.await(5, TimeUnit.SECONDS));
        assertEquals(2, calls.get());
      }
    }
  }
}
