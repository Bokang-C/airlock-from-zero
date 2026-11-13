# Cursor integration prompt — optional after you run the starter

Copy this into Cursor **after** opening the existing Airlock starter folder:

> Read `README.md`, `START_HERE_WINDOWS.md`, and the code in `backend/airlock` and `frontend/src` first. Do not replace the existing architecture. I am entering IceHacks 2026 and must be able to explain my work. Guide me step by step. First help me run the existing Python FastAPI backend and React frontend locally, and fix any runtime errors. Then verify the five X-Ray sample cases and the test suite. Do not claim the React frontend is tested until `npm run build` succeeds. Do not make the LLM demo scripted: it must use real model calls, and fake send_email may only write to the on-screen outbox. Keep all secrets in backend/.env. Never disable the Chromium sandbox for a public deployment. Avoid feature creep. If you modify any source files, explain the reason and how to test it.
