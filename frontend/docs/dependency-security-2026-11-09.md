# Targeted frontend dependency corrections — 2026-11-09

Scope: npm package manifests and lockfile only, plus this record. No application, backend, engine, migration, database or visual changes. User approved the targeted correction for a local commit on main; no push authorized. The separate monitoring/calendar commit remains unchanged.

## Selection and installed versions

Rechecked the 24 root GitHub advisory records through the official public API and npm registry metadata on 9 November, rather than assuming targets in the earlier external audit report. Next and eslint-config-next both publish stable 16.4.5. Next requires Node >=20.9 and accepts the installed React 19.2.8; its optional sharp range is now ^0.35.5. Host Node 24.7.0 and demo Node 20.20.2 satisfy that requirement.

| Group | Package | Before | After |
| --- | --- | --- | --- |
| 1 | next; eslint-config-next | 16.3.0 | 16.4.5 |
| 1 | sharp | 0.35.3 | 0.35.5 |
| 2 | follow-redirects | 1.16.1 | 1.16.3 |
| 2 | nanoid | 3.3.17 | 3.3.20 |
| 2 | source-map-js | 1.2.1 | 1.2.2 |
| 2 | brace-expansion (both existing branches) | 1.1.18; 5.0.9 | 1.1.21; 5.0.12 |
| 2 | js-yaml | 4.3.1 | 4.3.2 |
| 2 | zod | 4.4.3 | 4.6.7 |
| 3, retained | typescript-eslint and associated wrappers | 8.66.0 | 8.66.0 |
| 3, retained | minimatch via typescript-estree | 10.2.6 | 10.2.6 |

Direct Next versions stay exact. Other direct dependencies are unchanged. Transitive changes respect existing declared ranges; no overrides, forced fixes, major replacements or downgrades. Next platform binaries, @next/env and its ESLint plugin move together; its declared @swc/helpers becomes 0.5.23. sharp binary packages become 0.35.5 and libvips packages 1.3.4. npm also resolves compatible helpers in those updated subtrees (fastq 1.20.3 and sharp's semver 7.8.6) and records already-declared optional Tailwind WASI dependencies previously absent from the lock. Tailwind itself is unchanged.

Commands, in frontend:

```powershell
npm install --save-exact next@16.4.5 eslint-config-next@16.4.5 --package-lock-only --ignore-scripts
npm update follow-redirects nanoid source-map-js brace-expansion js-yaml zod --package-lock-only --ignore-scripts
npm ci
```

## Remaining supported-combination blocker

The latest published typescript-estree 8.72.1 still declares minimatch ^10.2.2; no patched 10.x is published (latest 10.2.6). The official advisory starts its fixed range at 11.0.1, outside that declared range. eslint-config-next 16.4.5 declares typescript-eslint ^8.56.0. Updating the wrapper alone would not resolve this advisory. An upstream supported dependency range or backport is needed; passing lint alone would not establish general compatibility with an undocumented major override. Keep this group unchanged instead of accepting npm's proposed downgrade of eslint-config-next or forcing minimatch 11.

GHSA-g3hv-75wg-m249 is a development/CI denial-of-service risk when attacker-controlled glob patterns reach optimizationLevel >=2. The inspected typescript-estree call in useProgramFromProjectService.js supplies only dot:true; that does not establish the triggering configuration in this app, nor prove all possible tool configurations safe. Avoid untrusted lint configuration/globs; recheck upstream before the next security update. It remains actionable, not dismissed because it is a development dependency.

## Audit result

- Before: 16 package nodes (1 critical, 7 high, 8 moderate).
- After full npm audit: 8 moderate nodes; no critical/high, no new nodes or root advisories.
- Resolved nodes: next, sharp, follow-redirects, nanoid, source-map-js, brace-expansion, js-yaml, zod.
- Remaining: minimatch plus seven propagated nodes: typescript-eslint, @typescript-eslint/{eslint-plugin,parser,type-utils,typescript-estree,utils}, eslint-config-next. These represent one remaining root advisory, not eight independent defects.
- npm audit --omit=dev: zero findings on host and demo. This is a registry snapshot, not a guarantee of application security. The demo runs a development server and still includes the lint/tooling packages.

## Verification

- npm ci: successful on Windows and isolated Linux-musl demo, from the same lockfile.
- npx tsc --noEmit and npm run lint: successful.
- npm run build: successful, Next 16.4.5, including static generation and TypeScript.
- 90 tests pass: node --test tests/calendar-dates.test.mjs tests/monitoring.test.mjs tests/academic-panel.test.mjs tests/academic-practice.test.mjs tests/session-expiry.test.mjs tests/landing.test.mjs tests/pasapalabra-join-recovery.test.mjs. Existing React test-double warning about scroll=false remains; no test failures.
- Demo frontend restarted with Next 16.4.5 (webpack). sharp 0.35.5 loads and generates a PNG using libvips 8.18.7 on Node 20.20.2 / Alpine. This is a benign codec smoke check, not adversarial image testing.
- Isolation confirmed before sync: Compose project biogamed_docente_demo, backend database biogamed_demo on its private db service, dedicated biogamed_docente_demo_demo_data volume; only its frontend manifests and node_modules updated. No database commands, migrations, new accounts, games or rooms; habitual services were not restarted or updated.
- Integrated-browser review: existing demo teacher authenticated, dashboard and academic catalogue loaded, category counts and shared illustrations visible, preparation reached without starting a game; selecting Nivel 2 preserved the URL and showed 10 eligible questions. All four existing category SVG images reported complete with nonzero natural width and were visible in the integrated browser. No browser other than integrated IAB, no desktop control. This is a short dependency regression check, not a new full game/accessibility review. Existing approved game/monitoring visual checks remain applicable because their code is unchanged.

Review URL: http://localhost:13004 (existing demo credentials). Open Práctica biomédica → Preguntas del Trivial original → Erlenmeyer → Trivial. No need to start a game to verify preparation.

## Official sources

- [Next image security fix](https://github.com/advisories/GHSA-2464-fhr4-w9xw); [Next development-server disclosure](https://github.com/advisories/GHSA-39w2-rjm5-chcv).
- [sharp SVG fix](https://github.com/advisories/GHSA-wq5f-xc86-pv6w); [sharp AVIF fix](https://github.com/advisories/GHSA-rgj7-g3m4-5g8c).
- [follow-redirects](https://github.com/advisories/GHSA-mrwp-f3q8-3g9p), [nanoid](https://github.com/advisories/GHSA-2v37-7h3g-55p8), [source-map-js](https://github.com/advisories/GHSA-68fv-2mgg-jv7q).
- [brace-expansion latest fix](https://github.com/advisories/GHSA-q2hr-2g5m-vwhr), [js-yaml](https://github.com/advisories/GHSA-2883-xcg3-v3hh), [zod](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5).
- [Remaining minimatch advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249).
- Registry metadata: next@16.4.5, eslint-config-next@16.4.5, @typescript-eslint/typescript-estree@8.72.1 (npm view engines, peerDependencies and dependencies). All targets and actual resolutions checked again after installation.
