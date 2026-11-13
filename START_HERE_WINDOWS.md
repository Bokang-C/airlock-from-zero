# AIRLOCK — Start Here (Windows)

**Follow these steps in this order.** This package contains the actual backend and frontend source code. No previous project is needed.

## Step 0: Install the tools

- **Python 3.12** from https://www.python.org/downloads/ (tick “Add Python to PATH” if the installer offers it)
- **Node.js LTS** from https://nodejs.org/en/download
- **Cursor** https://cursor.com/ or **VS Code** https://code.visualstudio.com/
- A GitHub account (needed for IceHacks submission)

Open Cursor/VS Code → **File → Open Folder** → choose `airlock-from-zero` after unzipping.

## Step 1: Start the backend (PowerShell terminal #1)

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
Copy-Item .env.example .env
.\.venv\Scripts\python.exe run.py
```

Leave that terminal open. Open http://127.0.0.1:8000/api/health . You should see `"ok": true`.

## Step 2: Start the frontend (PowerShell terminal #2)

Open a **second** terminal in Cursor/VS Code:

```powershell
cd frontend
npm install
npm run dev
```

Go to http://127.0.0.1:5173 . The Airlock homepage should appear.

Click **X-Ray Scanner** → choose **Opacity: 0** → **Run inspection**. The verdict should be `BLOCK` and the hidden red text should be revealed.

## Step 3: Run tests

In the backend terminal (you may open a third terminal):

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## Step 4: Enable the real agent (optional, needs API key)

Edit `backend/.env`. Set `OPENAI_API_KEY=your_secret_key_here`, save it, and restart the backend. Do NOT put this key in frontend files, commit it to GitHub, or share it in screenshots. Visit Agent Lab; its fake email outbox is the ONLY email destination.

If you don't have a key, X-Ray still works. Save the agent integration for the next step.

## Step 5: Submit to GitHub

From the root folder:

```powershell
git init
git add .
git commit -m "Build Airlock visibility-aware scanner prototype"
```

Create an **empty public GitHub repo** using GitHub's website; follow the exact commands GitHub shows to add a remote and push `main`. Confirm no `.env` file appears in the repo. If `git` isn't found, install Git from https://git-scm.com/downloads/win and restart your terminal.

## Step 6: Public demo + video

See `docs/DEPLOYMENT.md` and `docs/VIDEO_SCRIPT.md`. **Do not disable the browser sandbox in a public deployment.** DeployXA free tier is likely tight for Chromium; verify the sandbox and memory first. The hackathon ends Sunday Nov 15, 2026 at 6 PM Pacific (9 PM Eastern).

## Troubleshooting

- `No module named playwright` → Run pip with the exact `backend/.venv/Scripts/python.exe` interpreter, not your system Python.
- `Executable doesn't exist` → Run `python -m playwright install chromium` within the same venv.
- `npm is not recognized` → Install Node.js and reopen terminal.
- `Cannot find module` → Run `npm install` inside the **frontend** folder.
- `Backend 503` → Inspect the backend terminal for Chromium errors. On an isolated **local-only** machine you can set `AIRLOCK_DEV_NO_BROWSER_SANDBOX=1` in `backend/.env` and restart; never do this on the public server.
- `Agent Lab 503` → Add `OPENAI_API_KEY` to `backend/.env` and restart.
- `Frontend loads but scanner request fails` → Verify terminal #1 is running on port 8000 and frontend Vite is on 5173.
