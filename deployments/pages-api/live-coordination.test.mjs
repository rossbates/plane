import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

// Exercise the exact hook deployed in the pinned compiled image without starting
// an HTTP server, websocket server, or production Redis connection.
const source = readFileSync("/app/apps/live/dist/start.mjs", "utf8");
const match = source.match(/async onLoadDocument\(\{ documentName \}\) \{\s*await this\.sub\.subscribe\(this\["subKey"\]\(documentName\)\);\s*\}/g);
assert.equal(match?.length, 1, "Exactly one early Redis subscription hook is present");
const Hook = new Function(`return class { ${match[0]} }`)();

test("channel subscription completes before the database load can start", async () => {
  const calls = [];
  let acknowledge;
  const ack = new Promise((resolve) => { acknowledge = resolve; });
  const hook = new Hook();
  hook.subKey = (id) => `hocuspocus:${id}`;
  hook.sub = { subscribe: async (channel) => { calls.push(channel); await ack; } };
  const load = (async () => {
    await hook.onLoadDocument({ documentName: "page-uuid" });
    calls.push("database read");
  })();
  await Promise.resolve();
  assert.deepEqual(calls, ["hocuspocus:page-uuid"]);
  acknowledge();
  await load;
  assert.deepEqual(calls, ["hocuspocus:page-uuid", "database read"]);
});

test("a failed subscription prevents a stale document database read", async () => {
  let databaseRead = false;
  const hook = new Hook();
  hook.subKey = (id) => `hocuspocus:${id}`;
  hook.sub = { subscribe: async () => { throw new Error("Redis unavailable"); } };
  await assert.rejects(async () => {
    await hook.onLoadDocument({ documentName: "page-uuid" });
    databaseRead = true;
  }, /Redis unavailable/);
  assert.equal(databaseRead, false);
});
