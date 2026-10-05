/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */
import { describe, expect, it, vi } from "vitest";
import type { onLoadDocumentPayload } from "@hocuspocus/server";

// No production Redis client, HTTP server, or websocket listener is created.
vi.mock("@/redis", () => ({ redisManager: { getClient: vi.fn() } }));
import { Redis } from "@/extensions/redis";

const payload = { documentName: "page-uuid" } as onLoadDocumentPayload;
const hook = (subscribe: (channel: string) => Promise<unknown>) =>
  ({ sub: { subscribe }, subKey: (id: string) => `hocuspocus:${id}` }) as unknown as Redis;

describe("early page-document subscription", () => {
  it("waits for subscription acknowledgement before database loading", async () => {
    const calls: string[] = [];
    let acknowledge!: () => void;
    const acknowledgement = new Promise<void>((resolve) => {
      acknowledge = resolve;
    });
    const instance = hook(async (channel) => {
      calls.push(channel);
      await acknowledgement;
    });
    const loading = (async () => {
      await Redis.prototype.onLoadDocument.call(instance, payload);
      calls.push("database read");
    })();
    await Promise.resolve();
    expect(calls).toEqual(["hocuspocus:page-uuid"]);
    acknowledge();
    await loading;
    expect(calls).toEqual(["hocuspocus:page-uuid", "database read"]);
  });

  it("fails closed when Redis cannot acknowledge the subscription", async () => {
    const databaseRead = vi.fn();
    const instance = hook(async () => {
      throw new Error("Redis unavailable");
    });
    await expect(
      (async () => {
        await Redis.prototype.onLoadDocument.call(instance, payload);
        databaseRead();
      })()
    ).rejects.toThrow("Redis unavailable");
    expect(databaseRead).not.toHaveBeenCalled();
  });
});
