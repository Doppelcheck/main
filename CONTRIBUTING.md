# Contributing

Thanks for looking. This is a small project, so the process is short.

## What has to pass

CI runs on every push and pull request against `main`
(`.github/workflows/ci.yml`). It runs exactly what you can run locally:

```bash
npm ci
npm run compile          # tsc --noEmit
npm run test             # vitest
npm run build            # chrome-mv3
npm run build:firefox    # firefox-mv2
```

If those four are green on your machine, CI will agree with you.

## Setup

Node is pinned by `.nvmrc` — `nvm use` picks up the right version, and CI
reads the same file, so there is one source of truth.

```bash
nvm use
npm ci
npm run dev              # loads the extension into a dev Chrome profile
npm run dev:firefox      # same, Firefox
```

## House rules

- **TypeScript is strict**, with `noUncheckedIndexedAccess`. An index access
  gives you `T | undefined` and you are expected to handle it.
- **Tests belong in `tests/`**, named `*.test.ts`. The suite covers the
  pure-logic modules — the tolerant LLM-JSON parser and the settings
  migration — because those are the parts that fail silently in a user's
  browser rather than loudly in a build. New logic of that kind should arrive
  with tests; UI work is not expected to.
- **`legacy/` is an archive.** The previous Python + FastAPI + bookmarklet
  implementation is kept deliberately, and runnable. Don't modernise, lint or
  upgrade anything in it.
- **The Anthropic transport is hand-written over `fetch`** (`lib/llm/anthropic.ts`)
  to keep the extension bundle small. Please don't replace it with the SDK.
- Both browser targets have to keep building. A change that only works on
  Chrome MV3 is half a change.

## Pull requests

Describe what breaks without the change. A reproduction — a page, a model, a
settings combination — is worth more than a description of the diff, which the
diff already provides.
