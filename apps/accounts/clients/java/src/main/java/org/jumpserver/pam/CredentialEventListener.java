package org.jumpserver.pam;

import org.jumpserver.pam.Models.Credential;
import org.jumpserver.pam.Models.Event;

/** Ordered business hooks. Credential handlers must be safe to retry and reconnect. */
@FunctionalInterface
public interface CredentialEventListener {
  void onCredentialChanged(Credential credential) throws Exception;

  default void onEvent(Event event) throws Exception {}

  default void onCredentialRevoked(Event event) throws Exception {}

  default void onEventError(Exception error, Event event) {
    logError(error);
  }

  static void logError(Exception error) {
    System.getLogger(CredentialEventListener.class.getName())
        .log(
            System.Logger.Level.WARNING,
            "Credential event handler failed: {0}",
            error.getClass().getSimpleName());
  }
}
