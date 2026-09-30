package org.jumpserver.pam;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.http.WebSocket;
import java.time.Duration;
import java.util.Iterator;
import java.util.NoSuchElementException;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import org.jumpserver.pam.Models.Event;

/** One cancellable, reconnecting stream. Close the stream when leaving a for-each loop. */
public final class EventStream implements Iterable<Event>, AutoCloseable {
  private static final Object END = new Object();
  private final Client client;
  private final Duration timeout;
  private final ObjectMapper mapper;
  private final ArrayBlockingQueue<Object> events = new ArrayBlockingQueue<>(128);
  private final AtomicBoolean closed = new AtomicBoolean(), iterated = new AtomicBoolean();
  private final Thread reader;
  private volatile WebSocket connection;
  private volatile CompletableFuture<WebSocket> pending;
  private volatile boolean validMessage;

  EventStream(Client client, Duration timeout, ObjectMapper mapper) {
    this.client = client;
    this.timeout = timeout;
    this.mapper = mapper;
    reader = new Thread(this::read, "jms-pam-events");
    reader.setDaemon(true);
  }

  void start() {
    reader.start();
  }

  private void read() {
    long delay = 1000;
    try {
      while (!closed.get()) {
        validMessage = false;
        Listener listener = new Listener();
        try {
          pending = client.connectEvents(listener);
          connection = pending.get(timeout.toMillis(), TimeUnit.MILLISECONDS);
          if (closed.get()) {
            connection.abort();
            break;
          }
          while (!closed.get() && !listener.disconnected.await(10, TimeUnit.SECONDS)) {
            if (System.nanoTime() - listener.lastMessage >= TimeUnit.SECONDS.toNanos(30))
              throw new java.util.concurrent.TimeoutException("Event connection timed out");
            connection
                .sendText("{\"event\":\"ping\"}", true)
                .get(timeout.toMillis(), TimeUnit.MILLISECONDS);
          }
        } catch (InterruptedException error) {
          Thread.currentThread().interrupt();
          break;
        } catch (Exception ignored) {
          /* Reconnect without logging authorization or response bodies. */
        } finally {
          if (pending != null) pending.cancel(true);
          if (connection != null) connection.abort();
          connection = null;
        }
        if (validMessage) delay = 1000;
        if (!closed.get()) {
          try {
            Thread.sleep(delay);
          } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            break;
          }
          delay = Math.min(delay * 2, 30000);
        }
      }
    } finally {
      close();
    }
  }

  private final class Listener implements WebSocket.Listener {
    private volatile long lastMessage = System.nanoTime();
    private final StringBuilder message = new StringBuilder();
    private final CountDownLatch disconnected = new CountDownLatch(1);

    @Override
    public void onOpen(WebSocket socket) {
      socket.request(1);
    }

    @Override
    public CompletionStage<?> onText(WebSocket socket, CharSequence text, boolean last) {
      try {
        message.append(text);
        if (message.length() > 16 * 1024 * 1024)
          throw new IllegalArgumentException("Event too large");
        if (last) {
          JsonNode data = Models.object(mapper.readTree(message.toString()));
          message.setLength(0);
          String name = Models.string(data, "event");
          validMessage = true;
          lastMessage = System.nanoTime();
          if (!name.equals("pong")) {
            if (!name.equals("snapshot")
                && data.path("event_id").isTextual()
                && !data.get("event_id").asText().isEmpty()) {
              socket
                  .sendText(
                      mapper.writeValueAsString(
                          java.util.Map.of(
                              "event", "received", "event_id", data.get("event_id").asText())),
                      true)
                  .exceptionally(error -> null);
            }
            Event event = new Event(data);
            client.reconcileLatestCredentials(event);
            while (!closed.get() && !events.offer(event, 100, TimeUnit.MILLISECONDS)) {}
          }
        }
        if (!closed.get()) socket.request(1);
      } catch (InterruptedException error) {
        Thread.currentThread().interrupt();
        socket.abort();
        disconnected.countDown();
      } catch (Exception error) {
        socket.abort();
        disconnected.countDown();
      }
      return CompletableFuture.completedFuture(null);
    }

    @Override
    public CompletionStage<?> onClose(WebSocket socket, int code, String reason) {
      disconnected.countDown();
      return CompletableFuture.completedFuture(null);
    }

    @Override
    public void onError(WebSocket socket, Throwable error) {
      disconnected.countDown();
    }
  }

  @Override
  public Iterator<Event> iterator() {
    if (!iterated.compareAndSet(false, true))
      throw new IllegalStateException("Event stream has one consumer");
    return new Iterator<Event>() {
      private Object next;

      @Override
      public boolean hasNext() {
        if (closed.get()) return false;
        if (next == null) {
          try {
            next = events.take();
          } catch (InterruptedException error) {
            close();
            Thread.currentThread().interrupt();
            return false;
          }
        }
        return next != END;
      }

      @Override
      public Event next() {
        if (!hasNext()) throw new NoSuchElementException();
        Event event = (Event) next;
        next = null;
        return event;
      }
    };
  }

  Event poll(long timeoutMillis) throws InterruptedException {
    Object value = events.poll(timeoutMillis, TimeUnit.MILLISECONDS);
    return value instanceof Event ? (Event) value : null;
  }

  boolean isClosed() {
    return closed.get();
  }

  @Override
  public void close() {
    if (closed.compareAndSet(false, true)) {
      if (pending != null) pending.cancel(true);
      if (connection != null) connection.abort();
      reader.interrupt();
      events.clear();
      events.offer(END);
      client.removeStream(this);
    }
    if (Thread.currentThread() != reader) {
      try {
        reader.join(1000);
      } catch (InterruptedException error) {
        Thread.currentThread().interrupt();
      }
    }
  }
}
