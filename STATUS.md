# Verified status — November 12, 2026

## What is included and locally verified

- Backend APIs and Chromium visibility pipeline implemented.
- **28 pytest tests passed** in this container (Python 3.13; Playwright 1.57; system Chromium) including actual browser scans, CSS and JavaScript injection examples, safe/unsafe comparisons, and mocked LLM tool-call authorization.
- Frontend React/TypeScript source files passed the TypeScript parser's syntax check.
- Restricted public URL fetch implementation included, URL feature disabled by default.
- Agent Lab connects to a real model API when `OPENAI_API_KEY` is provided. Fake email tool never sends real emails.

## What is NOT verified (do not misrepresent this)

- A live LLM API call (no API key supplied); the 2 agent tests mock model tool-call outputs.
- React `npm install` and `npm run build` (the container cannot reach the npm package registry; run these locally).
- The complete public website in a deployed environment.
- Docker build and DeployXA deployment; sandbox and RAM viability unresolved.
- Arbitrary internet URL fetching; URL scanner off by default.
- Any empirical hijack-rate benchmark; no real ON/OFF model outcomes collected.

## Next milestones

1. Follow `START_HERE_WINDOWS.md` and confirm `X-Ray` works in your own browser.
2. Run `npm run build` and fix any missing dependencies/errors.
3. Enable a low-budget real LLM key on the backend, test Agent Lab ON and OFF using only fake fixtures.
4. Deploy with Chromium sandbox and sufficient resources; otherwise document and narrow scope.
5. Gather real numbers, record the under-three-minute video, and submit before the deadline.
