import assert from "node:assert/strict";
import test from "node:test";

import { health } from "../../lib/health.js";

test("health reports ok", () => {
  assert.deepEqual(health(), { status: "ok" });
});
