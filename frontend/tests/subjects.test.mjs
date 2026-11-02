import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

function loadTypescript(url) {
  const filename = fileURLToPath(url);
  const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true },
  }).outputText;
  const loaded = new Module(filename);
  loaded.filename = filename;
  loaded.paths = Module._nodeModulePaths(path.dirname(filename));
  loaded._compile(compiled, filename);
  return loaded.exports;
}

const client = loadTypescript(new URL("../src/services/api.ts", import.meta.url));
const { canManageSubjects, visibleSubjectsPage, SUBJECTS_PAGE_SIZE } =
  loadTypescript(new URL("../src/lib/subjects.ts", import.meta.url));

afterEach(() => { delete global.window; });

function testBrowser() {
  global.window = {
    localStorage: { getItem: (key) => key === "token" ? "test-token" : null },
    location: { replace: () => assert.fail("No redirect expected") },
  };
}

test("subject requests use the shared authenticated client and retain server data", async () => {
  testBrowser();
  const originalAdapter = client.default.defaults.adapter;
  const calls = [];
  client.default.defaults.adapter = async (config) => {
    calls.push(config);
    assert.equal(config.headers.Authorization, "Bearer test-token");
    return { status: config.method === "post" ? 201 : 200,
      data: config.method === "post"
        ? { id: 7, name: "Bioinformática", description: null }
        : [{ id: 4, name: "Biología", description: "Base" }],
      headers: {}, config };
  };
  try {
    assert.deepEqual(await client.getSubjects(12, 13), [{ id: 4, name: "Biología", description: "Base" }]);
    assert.deepEqual(await client.createSubject({ name: "Bioinformática", description: null }),
      { id: 7, name: "Bioinformática", description: null });
    assert.equal(calls[0].url, "/subjects");
    assert.equal(calls[0].method, "get");
    assert.deepEqual(calls[0].params, { skip: 12, limit: 13 });
    assert.equal(calls[1].url, "/subjects");
    assert.equal(calls[1].method, "post");
    assert.deepEqual(JSON.parse(calls[1].data), { name: "Bioinformática", description: null });
  } finally {
    client.default.defaults.adapter = originalAdapter;
  }
});

test("subject access only admits the two staff roles returned by /auth/me", () => {
  assert.equal(canManageSubjects("student"), false);
  assert.equal(canManageSubjects("teacher"), true);
  assert.equal(canManageSubjects("admin"), true);
});

test("one extra item determines next page without displaying it", () => {
  const received = Array.from({ length: SUBJECTS_PAGE_SIZE + 1 }, (_, index) => ({
    id: index + 1, name: `Asignatura ${index + 1}`, description: null,
  }));
  assert.deepEqual(visibleSubjectsPage(received), {
    items: received.slice(0, SUBJECTS_PAGE_SIZE), hasMore: true,
  });
  assert.equal(visibleSubjectsPage(received.slice(0, SUBJECTS_PAGE_SIZE)).hasMore, false);
  assert.deepEqual(visibleSubjectsPage([]), { items: [], hasMore: false });
});
