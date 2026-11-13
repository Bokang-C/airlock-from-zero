# Deploying Airlock — security-first checklist

**Do not deploy arbitrary Chromium browsing without an OS sandbox and isolation.** Playwright explicitly warns that its Docker image is not suitable for crawling untrusted pages by default, and recommends non-root + a seccomp profile to enable Chromium sandboxing. See https://playwright.dev/python/docs/docker.

**Step 1.** Test the full app locally, including browser scanner and (when credentials are configured) a real agent tool call. Run `pytest -q`. Record the results; don't claim untested success.

**Step 2.** Push this repository to GitHub; no `.env` or `node_modules` should be committed. Use a fresh API key with low spending limits and strict provider-side budget limits. Consider disabling the public agent demo or adding stronger restrictions if cost becomes a concern.

**Step 3.** In DeployXA, choose **New Project → GitHub**, select the repository. The root `Dockerfile` builds both frontend and backend. Set `OPENAI_API_KEY` as an encrypted environment secret if demo functionality is needed. Set `AIRLOCK_ENABLE_URL_SCAN=0` and `AIRLOCK_DEV_NO_BROWSER_SANDBOX=0`. DeployXA documentation supports a Git repository and Dockerfile build: https://deployxa.com/docs/quickstart.

**Step 4.** Check browser sandbox viability on the host. The image uses `USER airlock` but Kubernetes/container runtimes may prevent the Chromium user namespace sandbox. A sandbox error requires a compatible security profile / host setting or an isolated browser service; do **not** toggle off the sandbox on a shared public deployment. If sandbox remains unsupported, deploy static frontend separately and keep the untrusted HTML scanner disabled, or choose a host that supports securely isolated Chromium.

**Step 5.** Verify the **public** URL on phone and desktop. Inspect `/api/health`, test `/api/scan` with harmless HTML and a hidden payload, and test both agent modes if enabled. Make sure screenshots and error messages work. Do not use private data or real emails.

**Step 6.** Ensure the URL remains awake at judging time. DeployXA's free tier includes 512MB RAM and sleeps after periods of inactivity; running Chromium in 512MB could fail, so measure actual memory and upgrade/relocate if needed. Link: https://deployxa.com/docs/faq.

## Additional operational hardening before a real launch

- Browser process isolated by container/VM sandbox with constrained CPU, RAM, file system and no network access; a Playwright route is not the same as OS-level network isolation.
- Validate and pin DNS results at connection time; audit redirect handling and HTTP decompression limits; restrict URL mode on the public instance until reviewed.
- Persistent, distributed rate limits and authentication for paid LLM endpoints. Current limits are local to one Python worker and not intended to be internet-scale abuse controls.
- Security headers, event logs with private-data redaction, strict CSP, and immutable audit evidence.
- Screen-reader access review and safe, authenticated user-intent records for sensitive actions.
