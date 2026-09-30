package org.jumpserver.pam;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import org.jumpserver.pam.Models.Credential;
import org.jumpserver.pam.Models.Event;

/** A managed listener. close() stops and waits; hooks may close their own subscription. */
public final class EventSubscription implements AutoCloseable {
  private final Client client;
  private final CredentialEventListener listener;
  private final EventStream stream;
  private final AtomicBoolean stopped = new AtomicBoolean();
  private final CountDownLatch finished = new CountDownLatch(1);
  private final Map<String, PendingCredential> pending = new HashMap<>();
  private final Thread worker;

  private static final class PendingCredential {
    final Event update, event;
    final long delay, due;

    PendingCredential(Event update, Event event, long delay) {
      this.update = update;
      this.event = event;
      this.delay = delay;
      this.due = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(delay);
    }
  }

  EventSubscription(Client client, CredentialEventListener listener) {
    this.client = client;
    this.listener = java.util.Objects.requireNonNull(listener, "listener");
    this.stream = client.watchCredentialEvents();
    this.worker = new Thread(this::run, "jms-pam-event-handler");
    this.worker.setDaemon(true);
  }

  void start() {
    try {
      worker.start();
    } catch (RuntimeException | Error error) {
      stop();
      finished.countDown();
      throw error;
    }
  }

  public boolean isRunning() {
    return finished.getCount() != 0;
  }

  public void stop() {
    stopped.set(true);
    stream.close();
  }

  public void awaitTermination() throws InterruptedException {
    if (Thread.currentThread() == worker)
      throw new IllegalStateException("A listener cannot await its own termination");
    finished.await();
  }

  @Override
  public void close() {
    stop();
    if (Thread.currentThread() == worker) return;
    boolean interrupted = false;
    while (true) {
      try {
        finished.await();
        break;
      } catch (InterruptedException error) {
        interrupted = true;
      }
    }
    if (interrupted) Thread.currentThread().interrupt();
  }

  private void report(Exception error, Event event) {
    if (stopped.get()) return;
    try {
      listener.onEventError(error, event);
    } catch (RuntimeException hookError) {
      CredentialEventListener.logError(hookError);
    }
  }

  private static String selector(Event update) {
    if (update.getCredentialMode().equals("subscription") && !update.getAccountId().isEmpty()
        && !update.getKey().isEmpty()) {
      String key = update.getKey();
      if (!key.endsWith(":" + update.getAccountId())) key += ":" + update.getAccountId();
      return "key:" + key;
    }
    if (update.getCredentialMode().equals("alternating_rotation") && !update.getKey().isEmpty())
      return "key:" + update.getKey();
    return null;
  }

  private void refresh(Event update, Event event, long delay) {
    String target = selector(update);
    if (target == null || stopped.get()) return;
    try {
      PendingCredential previous = pending.get(target);
      if (previous != null
          && previous.update.getData().has("revision")
          && update.getData().has("revision")
          && previous.update.getRevision() > update.getRevision()) return;
      Credential credential = client.getCredential(target.substring(4), false);
      if (update.getData().has("revision") && credential.getRevision() < update.getRevision())
        throw new IllegalStateException("Credential API revision is behind the event");
      if (stopped.get()) return;
      listener.onCredentialChanged(credential);
      pending.remove(target);
    } catch (Exception error) {
      if (stopped.get()) return;
      report(error, event);
      pending.put(
          target, new PendingCredential(update, event, Math.min(Math.max(1000, delay * 2), 30000)));
    }
  }

  private void dispatch(Event event) {
    String name = event.getEvent();
    if (name.equals("snapshot")
        || name.equals("credential.revoked")
        || name.equals("configuration.updated")) pending.clear();
    try {
      listener.onEvent(event);
    } catch (Exception error) {
      report(error, event);
    }
    if (stopped.get()) return;
    try {
      if (name.equals("snapshot")) {
        for (Event update : event.getCredentials()) refresh(update, event, 0);
      } else if (name.equals("credential.updated") && event.getCommandId().isEmpty()) {
        refresh(event, event, 0);
      } else if (name.equals("credential.revoked")) {
        listener.onCredentialRevoked(event);
      }
    } catch (Exception error) {
      report(error, event);
    }
  }

  private void retry() {
    PendingCredential earliest = null;
    for (PendingCredential item : pending.values())
      if (earliest == null || item.due < earliest.due) earliest = item;
    if (earliest != null && earliest.due <= System.nanoTime())
      refresh(earliest.update, earliest.event, earliest.delay);
  }

  private void run() {
    try {
      while (!stopped.get() && !stream.isClosed()) {
        Event event = stream.poll(100);
        if (event != null) dispatch(event);
        retry();
      }
    } catch (InterruptedException error) {
      Thread.currentThread().interrupt();
    } catch (Exception error) {
      report(error, null);
    } finally {
      stop();
      pending.clear();
      finished.countDown();
    }
  }
}
