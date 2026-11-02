import assert from "node:assert/strict";
import { test } from "node:test";

process.env.TZ = "Asia/Tokyo";
const { formatDateTime } = await import("../src/format.ts");

test("muestra la hora de carga en zona de México", () => {
  assert.equal(formatDateTime("2026-11-02T00:36:00Z"), "01/11/2026 18:36");
  assert.equal(formatDateTime("2026-11-02T00:36:00+00:00"), "01/11/2026 18:36");
});

test("no depende de la zona del navegador", () => {
  assert.equal(new Date("2026-07-15T05:05:00Z").getHours(), 14);
  assert.equal(formatDateTime("2026-07-15T05:05:00Z"), "14/07/2026 23:05");
});
