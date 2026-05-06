# Alex setup

Plain English, end to end. About 60 minutes from start to first run. The Google Search Console step is the only fiddly bit, and you only do it once.

## Before you start

You'll need:
- A GitHub account ([sign up](https://github.com/join))
- A Google account (the one that owns your Search Console property)
- An Anthropic account ([sign up](https://console.anthropic.com))
- £5 to £10 of credit on your Anthropic account
- Your site already verified in [Search Console](https://search.google.com/search-console) with at least 2-3 weeks of data
- About 60 minutes the first time

You will *not* need to write any code.

---

## Step 1 — get an Anthropic API key

1. Go to [console.anthropic.com](https://console.anthropic.com).
2. Sign up or sign in.
3. Click your profile in the top right, then **API Keys**.
4. Click **Create Key**, name it `alex-agent`, and copy the key. **You'll only see it once.** Paste it somewhere safe.
5. Click **Plans & Billing** and add £5 to £10 of credit. Alex costs about £2 a month at typical use.

---

## Step 2 — copy this repo into your GitHub

1. Click **Fork** in the top right of [the GitHub page](https://github.com/catrinmdonnelly/alex-agent), or use **Use this template** for a clean repo.
2. Either way, you now have your own copy.

---

## Step 3 — create a Google Cloud service account

This is the slow step. A service account is a special Google account that Alex uses to talk to Search Console without needing your password.

### 3a. Make a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com). Sign in with the same Google account that owns your Search Console property.
2. At the top of the page there's a project picker (it might say "Select a project" or show an existing project name). Click it.
3. Click **New project** in the dialog that opens.
4. Name it something like `alex-seo-agent`. You can leave the organisation as is. Click **Create**.
5. Wait for it to finish creating. Once it's done, the project picker should show your new project.

### 3b. Enable the Search Console API

1. With your new project selected, click the **hamburger menu** (top left) → **APIs & Services** → **Library**.
2. In the search box, type `Search Console`.
3. Click **Google Search Console API**.
4. Click **Enable**. Wait a few seconds.

### 3c. Create the service account

1. Hamburger menu → **APIs & Services** → **Credentials**.
2. Click **+ Create Credentials** at the top, then **Service account**.
3. Service account name: `alex-seo`. Service account ID will autofill. Description optional.
4. Click **Create and Continue**.
5. **Grant access**: skip this, click **Continue**, then **Done**. Alex doesn't need any cloud-level roles.

### 3d. Generate the JSON key

1. You should now be on the Credentials page. Under **Service Accounts** you'll see `alex-seo`. Click on it.
2. Click the **Keys** tab.
3. Click **Add Key** → **Create new key**.
4. Choose **JSON** (it's the default). Click **Create**.
5. A JSON file will download to your computer. Keep it safe. **Don't put it anywhere public, anywhere it might end up in a public git commit, or in your email.**
6. The file looks like this:
   ```json
   {
     "type": "service_account",
     "project_id": "alex-seo-agent",
     "client_email": "alex-seo@alex-seo-agent.iam.gserviceaccount.com",
     ...
   }
   ```
7. Copy the value of `client_email`. You'll need it in the next step.

### 3e. Grant the service account access to your Search Console property

1. Go to [search.google.com/search-console](https://search.google.com/search-console).
2. Pick your property from the property selector (top left).
3. Click **Settings** in the left sidebar (gear icon at the bottom).
4. Click **Users and permissions**.
5. Click **Add user**.
6. Email address: paste the `client_email` from step 3d.
7. Permission: **Restricted** is enough (read-only). Click **Add**.

That's the GSC step done. The service account can now read your data.

### 3f. Note your site URL format

1. Back in Search Console, look at the property selector at the top left.
2. You'll see something like `sc-domain:example.com` (a domain property) or `https://example.com/` (a URL-prefix property). Note exactly what it shows. You'll paste this into a GitHub variable in step 5.

---

## Step 4 — fill in your business context

1. In your GitHub repo, click into the `config/` folder.
2. Edit `brand-voice.md`. Replace the placeholders with how your business actually writes. Bullet points are fine.
3. Edit `state.md`. The pages-that-matter and forums sections are the most important.
4. `system-prompt.md` is optional. Leave it as is to use Alex's default voice.

Commit each file as you go using GitHub's pencil-edit interface.

---

## Step 5 — add your secrets and variables to GitHub

1. In your repo, click **Settings → Secrets and variables → Actions**.

### Secrets (sensitive — encrypted)

Click **New repository secret** for each:

| Name | Value |
|------|-------|
| `ANTHROPIC_API_KEY` | The key from step 1 |
| `GSC_CREDENTIALS_JSON` | The **entire content** of the JSON file from step 3d. Open the file in a text editor, select all, copy, paste. GitHub handles the escaping. |

### Variables (visible — not encrypted)

Click the **Variables** tab. Then **New repository variable** for each:

| Name | Value |
|------|-------|
| `BUSINESS_NAME` | Your business name, e.g. `Cornish Ceramics` |
| `GSC_SITE_URL` | Exactly the format from step 3f, e.g. `sc-domain:example.com` or `https://example.com/` |

---

## Step 6 — turn on Actions

1. In your repo, click **Actions** in the top tabs.
2. If you see a yellow banner, click **I understand my workflows, go ahead and enable them**.

---

## Step 7 — run Alex for the first time

1. **Actions** → click **Alex weekly SEO report** in the left sidebar.
2. Click **Run workflow** → **Run workflow**.
3. Wait two to five minutes. Refresh.
4. The run should turn green. Click into your repo's `seo-reports/` folder and you'll see the first report.

If it fails, click into the run, expand the failed step, read the error. The most common issues:
- Missing or wrong `GSC_CREDENTIALS_JSON` secret
- Wrong `GSC_SITE_URL` format (must match Search Console exactly)
- Service account not added to Search Console (step 3e missed)
- No data in Search Console yet (need at least a few weeks)

Fix and re-run.

---

## Step 8 (optional) — failure email alerts

Same as Cleo if you've set that up. Otherwise:

1. In your Google account, [generate an app password](https://myaccount.google.com/apppasswords) named `alex-agent`.
2. In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**, four times:
   - `FAILURE_EMAIL_TO`
   - `FAILURE_EMAIL_FROM`
   - `FAILURE_EMAIL_SMTP_HOST` = `smtp.gmail.com`
   - `FAILURE_EMAIL_SMTP_PASS` = the 16-character app password

---

## Step 9 — change the schedule (optional)

Alex runs at 10:00 UK every Wednesday by default. To change:

1. Edit `.github/workflows/weekly.yml`.
2. Change the cron lines:
   ```yaml
   - cron: "0 9 * * 3"     # 09:00 UTC Wed = 10:00 UK BST
   - cron: "0 10 * * 3"    # 10:00 UTC Wed = 10:00 UK GMT
   ```
3. Use [crontab.guru](https://crontab.guru) to design a new schedule. GitHub Actions cron is in **UTC**.

---

## What to expect after that

Every Wednesday morning, Alex will:
1. Pull GSC data
2. Compare to the previous week
3. Read your config and any direction from upstream agents
4. Write the full report, content briefs, outreach targets
5. Commit and push

You'll see them appear in your repo when you next look.

---

## Troubleshooting

**`HttpError 403: User does not have sufficient permissions`** — The service account isn't on the Search Console property yet. Repeat step 3e.

**`HttpError 404: Site not found`** — `GSC_SITE_URL` doesn't match what's in Search Console. Check the format exactly (`sc-domain:` vs `https://`, trailing slash).

**Empty report, "no data"** — Either the property is brand new and has no data yet, or the service account is on a different property than the URL in `GSC_SITE_URL`.

**The cron isn't firing** — GitHub Actions pauses cron schedules in repos with no activity for 60 days. Run the workflow manually once and the schedule resumes.

**Recommendations are generic** — That's a config problem. Make `config/state.md` more specific: list the exact pages that matter, the exact topics you want to own, the forums where your audience actually is.
