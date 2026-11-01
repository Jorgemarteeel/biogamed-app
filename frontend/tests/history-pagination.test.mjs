import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const filename = fileURLToPath(new URL("../src/lib/history-pagination.ts", import.meta.url));
const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const loaded = new Module(filename);
loaded.filename = filename;
loaded.paths = Module._nodeModulePaths(path.dirname(filename));
loaded._compile(compiled, filename);
const { visibleHistoryPage } = loaded.exports;

test("an extra server item enables the next page without displaying it", () => {
  const received = Array.from({ length: 11 }, (_, index) => index + 1);
  assert.deepEqual(visibleHistoryPage(received), { items: received.slice(0, 10), hasMore: true });
});

test("a full final page and an empty page have no next link", () => {
  assert.equal(visibleHistoryPage(Array(10).fill(1)).hasMore, false);
  assert.deepEqual(visibleHistoryPage([]), { items: [], hasMore: false });
});
