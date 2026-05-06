# Alex

A weekly SEO agent. Alex pulls Google Search Console for your site, compares the last 7 days against the previous 7, finds rising queries, declining pages, ranking opportunities, and writes a weekly report. He drafts content briefs and outreach targets too.

He runs every Wednesday morning. The reports land in your repo as markdown files. Read in 10 minutes. Specific enough to act on the same day.

> **Status:** Free to use. Take the code, point it at your business. MIT licensed.

## What you get every Wednesday

- **A full SEO report** at `seo-reports/YYYY-MM-DD.md`. GSC dashboard, top keywords, new queries, opportunities, striking distance plays, CTR fixes, website amendments, backlink targets, forum threads with draft responses, quick wins.
- **Content briefs** at `blog-briefs/YYYY-MM-DD.md`. Each keyword opportunity turned into a brief ready to draft.
- **Outreach targets** at `outreach-targets/YYYY-MM-DD.md`. Backlink emails and forum threads with draft replies. Always review before sending.
- **A trends file** at `exchange/seo-trends-latest.md`. Picked up automatically by a downstream content agent if you have one.
- **A summary file** at `exchange/seo-report-latest.md`. Picked up by an upstream strategy agent if you have one.

## What it costs

About £2 a month in Anthropic API spend. Google Search Console is free. GitHub Actions usage is free at this volume.

## What you'll need before you start

1. A GitHub account.
2. A site that's already verified in [Google Search Console](https://search.google.com/search-console) and has at least a few weeks of search data.
3. An [Anthropic API key](https://console.anthropic.com).
4. A Google Cloud account (free tier is fine) to create a service account that can read your GSC data.
5. About 60 minutes for first-time setup. The GSC service account is the slow part.

## How it works

1. Alex authenticates to Google Search Console using a service account you create
2. Pulls 7 days of data and compares against the previous 7
3. Reads your brand voice and current state from config files
4. Calls Claude with web search to do the analysis and write the report
5. Commits the report and a couple of summary files back to the repo

The whole pipeline runs on GitHub Actions every Wednesday at 10:00 UK. If anything breaks, he emails you.

## Set up

See [SETUP.md](SETUP.md) for the full step-by-step. The GSC service account is the only fiddly bit. It takes about 30 minutes the first time.

## Running it locally

```sh
cp .env.example .env
# fill in ANTHROPIC_API_KEY, GSC_SITE_URL, GSC_CREDENTIALS_JSON, BUSINESS_NAME

pip install -r requirements.txt
python alex.py
```

The report will appear in `seo-reports/`.

## Customising

- **Voice and approach.** Edit `config/system-prompt.md` to give Alex a different style. Leave it blank to use the default.
- **Schedule.** Edit `.github/workflows/weekly.yml`.
- **Forums and outreach areas.** Edit `config/state.md` to tell Alex where your audience hangs out and where to leave alone.

## The bigger picture

Alex is one of three agents that work together if you run all of them:

| Agent | Role | Cadence |
|-------|------|---------|
| **[Cleo](https://github.com/catrinmdonnelly/cleo-agent)** | Weekly growth strategy. Reads what's happening, decides the focus. | Mondays |
| **Alex** | SEO. Pulls Search Console, finds rising queries and declining pages. | Wednesdays |
| **[Jess](https://github.com/catrinmdonnelly/jess-agent)** | Social content. Plans and posts daily Instagram carousels. | Daily |

Each one runs on its own. Together, Alex reads Cleo's direction, picks SEO priorities that align, and posts trend findings any social agent can pick up.

## Help

Issues and pull requests welcome. The GSC step is where most people get stuck — open an issue with which step is failing and the error message.

## Licence

MIT. See [LICENSE](LICENSE).
