package org.jumpserver.pam;

/** A network, HTTP or response-decoding failure. Never log credential payloads. */
public final class PAMException extends RuntimeException {
  private final String code;
  private final int statusCode;
  private final String detail;
  private final String requestId;

  public PAMException(
      String code, int statusCode, String detail, String requestId, Throwable cause) {
    super("[" + code + "] " + detail, cause);
    this.code = code;
    this.statusCode = statusCode;
    this.detail = detail;
    this.requestId = requestId;
  }

  public String getCode() {
    return code;
  }

  public int getStatusCode() {
    return statusCode;
  }

  public String getDetail() {
    return detail;
  }

  public String getRequestId() {
    return requestId;
  }
}
