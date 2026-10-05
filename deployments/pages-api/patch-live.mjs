// Plane v1.4.2 compiled counterpart of apps/live/src/extensions/redis.ts.
// Keep the official image's exact dependencies and build; fail closed if it changes.
import { readFileSync, writeFileSync } from "node:fs";

const path = "/app/apps/live/dist/start.mjs";
const source = readFileSync(path, "utf8");
const marker = "\tasync onConfigure(payload) {\n\t\tawait super.onConfigure(payload);";
if (source.split(marker).length !== 2) throw new Error("Expected exactly one v1.4.2 Redis onConfigure hook");
const hook = [
  "\t// Local Pages API: reserve the document channel before its database read.",
  "\tasync onLoadDocument({ documentName }) {",
  '\t\tawait this.sub.subscribe(this["subKey"](documentName));',
  "\t}",
  marker,
].join("\n");
writeFileSync(path, source.replace(marker, hook));
console.log("Added early Redis subscription for Pages API/editor coordination");
