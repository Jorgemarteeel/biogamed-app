import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";
import { AxiosError } from "axios";

// Load the real TypeScript client without adding a test runner dependency.
const filename = fileURLToPath(new URL("../src/services/api.ts", import.meta.url));
const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true },
}).outputText;
const loaded = new Module(filename);
loaded.filename = filename;
loaded.paths = Module._nodeModulePaths(path.dirname(filename));
loaded._compile(compiled, filename);
const api = loaded.exports.default;

function browser(token = "old-token") {
  const values = new Map(token ? [["token", token]] : []);
  const redirects = [];
  global.window = {
    localStorage: {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
      removeItem: (key) => values.delete(key),
    },
    location: { replace: (url) => redirects.push(url) },
  };
  return { values, redirects };
}

function rejectWith(status, beforeReject = () => {}) {
  return async (config) => {
    beforeReject(config);
    throw new AxiosError("Request rejected", undefined, config, undefined,
      status ? { status, data: {}, headers: {}, config } : undefined);
  };
}

afterEach(() => { delete global.window; });

test("401 with current token clears it and redirects once for simultaneous requests", async () => {
  const { values, redirects } = browser();
  await Promise.allSettled([
    api.get("/auth/me", { adapter: rejectWith(401) }),
    api.get("/game/history", { adapter: rejectWith(401) }),
  ]);
  assert.equal(values.has("token"), false);
  assert.deepEqual(redirects, ["/login?session=expired"]);
});

for (const url of ["/auth/login", "/auth/register", "/auth/login/?x=1"]) {
  test(`public auth ${url} does not send a stored token or trigger expiry handling`, async () => {
    const { values, redirects } = browser();
    await assert.rejects(api.post(url, {}, { adapter: rejectWith(401, (config) => {
      assert.equal(config.headers.Authorization, undefined);
    }) }));
    assert.equal(values.get("token"), "old-token");
    assert.deepEqual(redirects, []);
  });
}

test("late 401 does not destroy a newer login", async () => {
  const { values, redirects } = browser();
  await assert.rejects(api.get("/auth/me", { adapter: rejectWith(401, () => {
    values.set("token", "new-token");
  }) }));
  assert.equal(values.get("token"), "new-token");
  assert.deepEqual(redirects, []);
});

for (const status of [403, 500, undefined]) {
  test(`${status ?? "network error"} does not clear the session`, async () => {
    const { values, redirects } = browser();
    await assert.rejects(api.get("/auth/me", { adapter: rejectWith(status) }));
    assert.equal(values.get("token"), "old-token");
    assert.deepEqual(redirects, []);
  });
}

test("401 without a token does not cause a redirect loop", async () => {
  const { redirects } = browser(null);
  await assert.rejects(api.get("/auth/me", { adapter: rejectWith(401) }));
  assert.deepEqual(redirects, []);
});

test("server-side errors remain rejected without accessing window", async () => {
  await assert.rejects(api.get("/auth/me", { adapter: rejectWith(401) }));
});

test("successful requests keep token and response", async () => {
  const { values, redirects } = browser();
  const result = await api.get("/auth/me", { adapter: async (config) => {
    assert.equal(config.headers.Authorization, "Bearer old-token");
    return { status: 200, data: { name: "Test" }, headers: {}, config };
  } });
  assert.equal(result.data.name, "Test");
  assert.equal(values.get("token"), "old-token");
  assert.deepEqual(redirects, []);
});

test("starting Trivial sends an authenticated POST and returns the server session", async () => {
  browser();
  const originalAdapter = api.defaults.adapter;
  const session = { session_id: 17, topic_id: 3, questions: [
    { id: 8, text: "Pregunta", options: ["A", "B"], question_type: "TRIVIAL", letter: null },
  ] };
  api.defaults.adapter = async (config) => {
    assert.equal(config.method, "post");
    assert.equal(config.url, "/game/start/3");
    assert.deepEqual(config.params, { mode: "TRIVIAL" });
    assert.equal(config.headers.Authorization, "Bearer old-token");
    return { status: 201, data: session, headers: {}, config };
  };
  try {
    assert.deepEqual(await loaded.exports.startTrivialGame(3), session);
  } finally {
    api.defaults.adapter = originalAdapter;
  }
});

test("a topic with no playable questions keeps the session and exposes the 409", async () => {
  const { values, redirects } = browser();
  const originalAdapter = api.defaults.adapter;
  api.defaults.adapter = rejectWith(409);
  try {
    await assert.rejects(loaded.exports.startTrivialGame(3), (error) => error.response.status === 409);
    assert.equal(values.get("token"), "old-token");
    assert.deepEqual(redirects, []);
  } finally {
    api.defaults.adapter = originalAdapter;
  }
});

test("submission sends each selection including index zero and uses the server score", async () => {
  browser();
  const originalAdapter = api.defaults.adapter;
  const answers = [{ question_id: 21, selected_index: 0 }, { question_id: 5, selected_index: 2 }];
  const result = { score: 1, total_questions: 2, corrections: [
    { question_id: 21, selected_index: 0, correct_option_index: 0, is_correct: true },
    { question_id: 5, selected_index: 2, correct_option_index: 1, is_correct: false },
  ] };
  api.defaults.adapter = async (config) => {
    assert.equal(config.method, "post");
    assert.equal(config.url, "/game/submit/17");
    assert.equal(config.headers.Authorization, "Bearer old-token");
    assert.deepEqual(JSON.parse(config.data), { answers });
    return { status: 200, data: result, headers: {}, config };
  };
  try {
    assert.deepEqual(await loaded.exports.submitTrivialGame(17, answers), result);
    assert.deepEqual(answers, [{ question_id: 21, selected_index: 0 }, { question_id: 5, selected_index: 2 }]);
  } finally {
    api.defaults.adapter = originalAdapter;
  }
});

test("retry after a lost submission response recovers the saved result", async () => {
  browser();
  const originalAdapter = api.defaults.adapter;
  const answers = [{ question_id: 21, selected_index: 0 }];
  const corrections = [{ question_id: 21, selected_index: 0, correct_option_index: 0, is_correct: true }];
  let posts = 0;
  const calls = [];
  api.defaults.adapter = async (config) => {
    calls.push(`${config.method} ${config.url}`);
    if (config.method === "post") {
      posts += 1;
      return rejectWith(posts === 1 ? undefined : 409)(config);
    }
    return { status: 200, data: { is_completed: true, score: 1, question_ids: [21], answer_logs: corrections }, headers: {}, config };
  };
  try {
    await assert.rejects(loaded.exports.submitTrivialGame(17, answers));
    assert.deepEqual(await loaded.exports.submitTrivialGame(17, answers), { score: 1, total_questions: 1, corrections });
    assert.deepEqual(calls, ["post /game/submit/17", "post /game/submit/17", "get /game/history/17"]);
  } finally {
    api.defaults.adapter = originalAdapter;
  }
});

test("a conflict on an unfinished game stays an error instead of showing a false result", async () => {
  browser();
  const originalAdapter = api.defaults.adapter;
  api.defaults.adapter = async (config) => config.method === "post"
    ? rejectWith(409)(config)
    : { status: 200, data: { is_completed: false, score: 0, question_ids: [21], answer_logs: [] }, headers: {}, config };
  try {
    await assert.rejects(loaded.exports.submitTrivialGame(17, [{ question_id: 21, selected_index: 0 }]), (error) => error.response.status === 409);
  } finally {
    api.defaults.adapter = originalAdapter;
  }
});

test("expired sessions during submission redirect to login without fetching history", async () => {
  const { values, redirects } = browser();
  const originalAdapter = api.defaults.adapter;
  let calls = 0;
  api.defaults.adapter = rejectWith(401, () => { calls += 1; });
  try {
    await assert.rejects(loaded.exports.submitTrivialGame(17, [{ question_id: 21, selected_index: 0 }]));
    assert.equal(calls, 1);
    assert.equal(values.has("token"), false);
    assert.deepEqual(redirects, ["/login?session=expired"]);
  } finally {
    api.defaults.adapter = originalAdapter;
  }
});
