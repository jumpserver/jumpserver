"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const http = require("node:http");
const { WebSocketServer } = require("../node/node_modules/ws");

const signedHeaders = [
  "(request-target)",
  "accept",
  "date",
  "digest",
  "x-jms-request-id",
  "x-jms-org",
  "x-jms-client-version",
  "x-jms-protocol-version",
  "x-jms-config-schema-version",
];

async function startServer() {
  const requests = [];
  const failures = [];
  const receipts = [];
  const connections = new Map();
  const ids = new Set();
  const sockets = new Set();
  function authenticate(request, body) {
    const headers = request.headers;
    const auth = Object.fromEntries(
      [...String(headers.authorization).matchAll(/(\w+)="([^"]*)"/g)].map((match) => [
        match[1],
        match[2],
      ]),
    );
    assert.equal(auth.keyId, "contract-app");
    assert.equal(auth.algorithm, "hmac-sha256");
    assert.equal(auth.headers, signedHeaders.join(" "));
    assert.equal(
      headers.digest,
      "SHA-256=" + crypto.createHash("sha256").update(body).digest("base64"),
    );
    assert.equal(headers["x-jms-org"], "contract-org");
    assert.equal(headers["x-jms-client-version"], "1.0.0");
    assert.equal(headers["x-jms-protocol-version"], "1");
    assert.equal(
      headers["x-jms-config-schema-version"],
      headers["x-source"] === "jms-pam-agent" ? "1" : "0",
    );
    assert.match(
      headers["x-jms-request-id"],
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );
    assert.ok(!ids.has(headers["x-jms-request-id"]), "request ID reused");
    ids.add(headers["x-jms-request-id"]);
    assert.ok(Math.abs(Date.now() - Date.parse(headers.date)) < 30000);
    const signing = signedHeaders
      .map(
        (name) =>
          `${name}: ${
            name === "(request-target)"
              ? request.method.toLowerCase() + " " + request.url
              : headers[name]
          }`,
      )
      .join("\n");
    assert.equal(
      auth.signature,
      crypto.createHmac("sha256", "contract-secret").update(signing).digest("base64"),
    );
  }
  const server = http.createServer(async (request, response) => {
    const url = new URL(request.url, "http://localhost");
    if (url.pathname === "/__stats") {
      response.setHeader("Content-Type", "application/json");
      response.end(
        JSON.stringify({
          requests,
          receipts,
          failures,
          connections: Object.fromEntries(connections),
        }),
      );
      return;
    }
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    const body = Buffer.concat(chunks);
    response.setHeader("Content-Type", "application/json");
    try {
      authenticate(request, body);
      const data =
        request.method === "GET" ? Object.fromEntries(url.searchParams) : JSON.parse(body);
      assert.ok(data.instance_id);
      requests.push({
        path: url.pathname,
        method: request.method,
        data,
        requestId: request.headers["x-jms-request-id"],
      });
      const route = url.pathname
        .replace(/^\/prefix/, "")
        .replace("/api/v1/accounts/credential-client", "");
      let result;
      if (route === "/credential/") {
        assert.equal(Boolean(data.key) !== Boolean(data.account_id), true);
        if (data.key === "forbidden" || data.key === "upgrade") {
          response.statusCode = data.key === "forbidden" ? 403 : 426;
          result = {
            code:
              data.key === "forbidden" ? "credential_not_authorized" : "client_upgrade_required",
            detail: "Denied",
            request_id: "failure-id",
          };
        } else if (data.key === "invalid-json") {
          response.end("invalid");
          return;
        } else if (data.key === "redirect") {
          response.statusCode = 302;
          response.setHeader("Location", "/unexpected-redirect");
          result = { detail: "Redirect" };
        } else {
          result = {
            key: data.key || "db",
            revision: data.key === "invalid-revision" ? true : 2,
            asset: {
              id: "asset",
              name: "database",
              address: "127.0.0.1",
              platform: {
                id: "platform",
                name: "PostgreSQL",
                category: "database",
                type: "postgresql",
              },
            },
            account: {
              id: "account",
              name: "db-user",
              username: "app",
              secret_type: "password",
              secret: "DO_NOT_LOG_SECRET",
            },
            future_optional_field: "ignored",
          };
        }
      } else if (route === "/confirm/") {
        assert.equal(data.account_id, "account");
        assert.equal(data.revision, 2);
        result = { key: data.key, revision: data.revision };
      } else if (route === "/agent/sync/") {
        assert.ok(Array.isArray(data.credentials));
        assert.ok(Array.isArray(data.delivered_credentials));
        result = {
          config_digest: "digest",
          date_last_synced: "now",
          removed_keys: [],
          credentials: [{ key: "db", revision: 2, available: true, changed: false }],
          configuration: { delivery_mode: "socket", credential_keys: ["db"] },
        };
        if (data.sync_error === "invalid-flag") result.credentials[0].available = "false";
      } else if (route === "/commands/") {
        result = {
          commands: [
            {
              event: "application.restart.requested",
              command_id: "command",
              event_id: "command-event",
            },
          ],
        };
      } else if (route === "/command-result/") {
        assert.ok(["running", "success", "failed"].includes(data.status));
        if (data.command_id === "report-failure" && data.status === "failed") {
          response.statusCode = 503;
          result = { code: "temporarily_unavailable" };
        } else result = { accepted: data.command_id !== "duplicate", status: data.status };
      } else throw new Error("Unexpected route");
      response.end(JSON.stringify(result));
    } catch (error) {
      failures.push(error.message);
      response.statusCode = 401;
      response.end(
        JSON.stringify({ code: "contract_failure", detail: "Protocol assertion failed" }),
      );
    }
  });
  const ws = new WebSocketServer({ noServer: true });
  server.on("upgrade", (request, socket, head) => {
    try {
      authenticate(request, Buffer.alloc(0));
      assert.equal(request.headers["x-jms-event-receipts"], "1");
      assert.match(
        new URL(request.url, "http://localhost").pathname,
        /\/ws\/accounts\/credential-events\/$/,
      );
      ws.handleUpgrade(request, socket, head, (connection) =>
        ws.emit("connection", connection, request),
      );
    } catch (error) {
      failures.push(error.message);
      socket.destroy();
    }
  });
  ws.on("connection", (socket, request) => {
    sockets.add(socket);
    socket.on("close", () => sockets.delete(socket));
    const url = new URL(request.url, "http://localhost");
    const instance = url.searchParams.get("instance_id");
    const count = (connections.get(instance) || 0) + 1;
    connections.set(instance, count);
    socket.send(JSON.stringify({ event: "pong" }));
    socket.send(
      JSON.stringify({
        event: "snapshot",
        credentials: [{ key: "db", credential_mode: "alternating_rotation", revision: count + 1 }],
      }),
    );
    socket.send(
      JSON.stringify({
        event: "credential.updated",
        event_id: "updated-" + count,
        credential_key: "db",
        credential_mode: "alternating_rotation",
        account_id: "account",
        revision: 2,
      }),
    );
    socket.send(
      JSON.stringify({
        event: "future.notification",
        event_id: "future-" + count,
        future_payload: { notice: "preserved" },
      }),
    );
    socket.on("message", (message) => {
      const event = JSON.parse(message);
      if (event.event === "received") receipts.push({ instance, eventId: event.event_id });
      else if (event.event === "ping") socket.send(JSON.stringify({ event: "pong" }));
      else failures.push("Unexpected client WS event");
    });
    if (count === 1) setTimeout(() => socket.close(), 150).unref();
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return {
    endpoint: `http://127.0.0.1:${server.address().port}/prefix`,
    stats: () => ({ requests, receipts, failures, connections }),
    async close() {
      for (const socket of sockets) socket.terminate();
      ws.close();
      server.closeAllConnections();
      await new Promise((resolve) => server.close(resolve));
    },
  };
}

module.exports = { startServer };
if (require.main === module)
  startServer().then((server) => {
    console.log(server.endpoint);
    process.on("SIGTERM", () => server.close().then(() => process.exit(0)));
  });
