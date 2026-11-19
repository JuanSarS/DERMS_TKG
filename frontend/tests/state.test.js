import { strict as assert } from "node:assert";
import { test } from "node:test";
import { appState, escapeHtml, update } from "../src/state.js";

test("escape prevents HTML injection", () => {
  assert.equal(escapeHtml("<script>"), "&lt;script&gt;");
});
test("partial state update does not clear confirmed result", () => {
  update({ lastGood: { run_id: "persisted" } });
  update({ status: { remote: { state: "OFFLINE" } } });
  assert.equal(appState.lastGood.run_id, "persisted");
});
