# Deploy CodeScope: frontend on Vercel, backend on Render

```
 Browser ──► Vercel (React app, static files)
    │
    └──────► Render web service (FastAPI, Docker) ──► Render Postgres
```

The web app and the API live on **different addresses**, so two things connect them:

- the app is told where the API is (`VITE_API_URL`, set on Vercel), and
- the API is told which web address may call it (`CORS_ORIGINS`, set on Render).

You need free accounts on **GitHub**, **Render** and **Vercel**. Plan on about 20 minutes, most of it waiting for builds.

> **Read this first: the free tier is for trying things out.** Render says free instances are not for production. The free database is **deleted 30 days after it is created** (14 days of grace to upgrade), the free API **sleeps after 15 idle minutes** (the next request waits about a minute), and free databases have no backups. See [Free tier limits](#free-tier-limits-and-going-to-production).

---

## 1. Put the project on GitHub

Both Render and Vercel deploy from a Git repository. In a terminal in the project folder:

```bat
cd D:\codescope
git init
git add .
git commit -m "CodeScope"
git branch -M main
git remote add origin https://github.com/YOUR-NAME/codescope.git
git push -u origin main
```

Create the empty repository on github.com first (**New repository**, no README). Your local `.env` is ignored by Git on purpose: it never leaves your computer.

## 2. Backend and database on Render

1. Render dashboard → **New** → **Blueprint** → connect GitHub → choose your repository.
2. Render reads `render.yaml` and shows a database (`codescope-db`) and a web service (`codescope-api`).
3. It asks for **`CORS_ORIGINS`**. Enter the address your Vercel site *will* have, for example `https://codescope.vercel.app` (pick the project name you will use in step 3). If you are unsure, enter a placeholder; you fix it in step 4.
4. Click **Apply**. The first build takes several minutes.
5. When it says **Live**, open `https://YOUR-SERVICE.onrender.com/health`. You should see `{"status":"ok"}`.
6. Copy the service address (shown at the top of its page). You need it next.

Render generated `JWT_SECRET` and the database connection for you. Nothing secret is stored in the repository.

## 3. Frontend on Vercel

1. Vercel → **Add New** → **Project** → import the same repository.
2. **Root Directory: `frontend`** (click Edit). This is the setting people miss. Vercel should detect **Vite**; the build command and output folder come from `frontend/vercel.json`.
3. Open **Environment Variables** and add:

   | Name | Value |
   |---|---|
   | `VITE_API_URL` | your Render address, e.g. `https://codescope-api.onrender.com` |

   The `/api` part is added for you if you leave it out.
4. **Deploy.** When it finishes, copy your site's address (e.g. `https://codescope.vercel.app`).

## 4. Tell the API who may call it

1. Render → **codescope-api** → **Environment**.
2. Set **`CORS_ORIGINS`** to your exact Vercel address: `https://codescope.vercel.app` (https, **no trailing slash**).
   Several addresses can be separated by commas.
3. **Save.** Render redeploys the API on its own.

Optional, to also allow Vercel *preview* deployments, add `CORS_ORIGIN_REGEX` with the value
`https://codescope(-[a-z0-9-]+)?\.vercel\.app` (replace `codescope` with your project name).

## 5. Try it

Open your Vercel address. Register, create a project, add a public GitHub repository and run an analysis.

The first request after the API has been idle takes up to a minute (the free instance is waking up). The app tells you this if it can't connect.

## Updating later

`git push` and both sides redeploy automatically. Database migrations run each time the API starts.

**Changing `VITE_API_URL` needs a redeploy on Vercel**, because the value is baked in when the site is built (Deployments → ⋯ → Redeploy).

---

## What works differently here

- **"Forgot password" cannot deliver a link yet.** Production never shows the reset token, and no e-mail service is connected. Free Render instances also block the usual mail ports (25, 465, 587), so e-mail has to go through an HTTP provider (Resend, SendGrid, ...). Do not "fix" this by setting `APP_ENV=development`: that would show reset tokens, and API docs, to everyone.
- **Sign-in is rate limited by the app itself** (there is no nginx here): by IP, and more strictly per account, so one account cannot be brute-forced. Counters live in the API process, so they reset when it restarts. Tune with `AUTH_RATE_LIMIT_PER_MINUTE` (default 30, `0` turns it off).
- **Analyses run inside the API process.** A restart (Render may restart free instances at any time) fails the analysis that was running; the page then shows it as failed and you can run it again.
- **Repository size:** `MAX_REPO_MB` is 100 in `render.yaml` because a free instance has 512 MB of RAM.

## Free tier limits, and going to production

| Free limit (Render docs) | What to do for real use |
|---|---|
| Database deleted 30 days after creation; no backups | Upgrade `codescope-db` to a paid plan **before day 30**. Keep your own `pg_dump` backups too |
| API sleeps after 15 idle minutes, restarts at any time | Upgrade `codescope-api` to a paid plan |
| 512 MB RAM | A paid plan, then raise `MAX_REPO_MB` |

Change the `plan:` lines in `render.yaml` (or change the plan in the dashboard). Vercel's free tier is fine for this static site.

## Custom domain for the API

If the API is not on `*.onrender.com`, the browser's Content-Security-Policy in `frontend/vercel.json` blocks it. Edit `connect-src 'self' https://*.onrender.com` and put your API address there, and update `VITE_API_URL` and `CORS_ORIGINS` to match.

## Troubleshooting

| What you see | Cause and fix |
|---|---|
| Browser console: *blocked by CORS policy* | `CORS_ORIGINS` on Render does not exactly match your Vercel address. Check `https` vs `http`, no trailing slash, and that it is the address in the browser bar (not a preview address). |
| "Cannot reach the CodeScope server" | The free API is waking up: wait a minute and retry. If it persists, `VITE_API_URL` is wrong or was changed without redeploying Vercel. |
| `https://…onrender.com/health` does not answer | Open the service's **Logs** on Render. A typical cause is a failed build or database not ready yet. |
| Render deploy fails the health check | The API did not start. Read the log: it prints the real error (for example a bad `DATABASE_URL`). |
| Vercel shows 404 when you reload a page | Root Directory is not `frontend`, so `vercel.json` (which routes every path to the app) is not used. |
| Blank page and *Content Security Policy* errors | The API is not on `*.onrender.com`: see "Custom domain for the API". |
| 429 "Too many attempts" | The sign-in rate limit. Wait a minute. |
| Analysis fails with "Repository not found" | Only **public** `github.com` repositories are supported. |
| Analysis fails with "too large" | The repository is over `MAX_REPO_MB`. |
