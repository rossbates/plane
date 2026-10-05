import { defineConfig } from "tsdown";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm"],
  dts: true,
  platform: "neutral",
  // Keep core/instance.js beside the locale directory it imports. A single
  // bundled dist/index.js leaves ../locales pointing outside the distribution.
  unbundle: true,
  copy: [{ from: "src/locales", to: "dist/locales" }],
  exports: true,
});
