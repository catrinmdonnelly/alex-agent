# Alex

A weekly SEO analyst for small businesses, who tells you exactly what's happening in your search traffic every Wednesday morning before your week gets busy and gives you the ten minutes of reading that actually matter.

Most owners set up Google Search Console once, find it overwhelming, and never go back, which means their site might be ranking for things they don't know about, pages that used to bring traffic are silently dying, and real people on Reddit are asking questions their site could answer perfectly if they only knew the question existed. Alex closes that gap every week.

> **Status:** Free to use. Take the code, point it at your business. MIT licensed.

## What Alex actually does for a business

Picture a small ecommerce brand selling handmade ceramic plant pots, turning over £40,000 a month with two people running it and no marketing team. They've had Google Search Console set up for two years and have never looked at it once. Every Wednesday at ten in the morning, Alex pulls a week of data, scans the web for what's happening in their niche, and writes a report that lands like this:

> Last week brought 487 clicks from search, up 12% on the previous week, and most of it came from your "how to clean a ceramic plant pot" blog post jumping from page three to page one for "remove mineral deposits ceramic" (Google clearly likes how you wrote that). The page is sitting at position four with a 0.8% click-through rate though, which is bad, because the meta title reads "Cleaning Ceramic Plant Pots, Cornish Ceramics", which is too generic, so try something like "How to remove white residue from ceramic plant pots" instead. The query "ceramic plant pots for orchids" is sending you eighty impressions a week but you don't have a single page about orchids on the site, so that's a quick blog post for next week. There's also a Mumsnet thread from yesterday where someone's asking about flaking glaze, and your existing "Why glaze cracks" post is exactly the answer, with a draft reply below ready for you to edit and post.

The value isn't the report itself, since anyone could write something similar given the data. The value is that **someone is writing it for you every Wednesday morning, on time, without you ever having to remember to log into Search Console**.

## Who Alex helps

- A small business with a site that's already getting some search traffic (a few hundred impressions a week minimum)
- An owner who'll act on a 10-minute weekly read
- Someone willing to do the GSC service account setup. It's the fiddly bit, but it's a one-time thing.

## Who Alex doesn't help

- Brand new sites with no organic traffic yet
- Owners who won't update meta descriptions or write a real reply to a forum thread
- Sites without a Google Search Console property already set up and verified

## What success looks like after three months

Success isn't a stack of beautifully-formatted reports piling up in your repo. It's three or four things that changed on your actual site because Alex flagged them: a page got an updated title and the click-through rate doubled, a blog post got refreshed because it was decaying, a Reddit thread got a real human reply that earned a customer, a new page exists for a query you didn't know was sending you traffic. If a year goes by and nothing on your site looks any different, Alex wasn't doing his job, or you weren't reading him.

## What you get every Wednesday

A single markdown file at `seo-reports/YYYY-MM-DD.md` with everything in one place:

1. **GSC dashboard**, the headline numbers and what they mean
2. **What to celebrate / what to worry about**, the signals from this week's data
3. **Top keywords**, the queries actually sending you impressions and clicks
4. **New queries**, things you started ranking for this week
5. **Keyword opportunities**, gaps Alex spotted, with a recommended action for each
6. **Striking distance plays**, queries you're close to ranking for, and how to push them
7. **CTR gap fixes**, meta titles and descriptions that aren't pulling their weight
8. **Website amendments**, on-page changes worth making
9. **Backlink opportunities**, sites Alex thinks would link to you with the right pitch
10. **Reddit and forum threads**, with draft responses you can edit and post
11. **Quick wins**, anything you can do in under 15 minutes

Plus two short companion files in `exchange/` for any other agent reading along, and a Station inbox JSON if you use the [Station widget](https://github.com/catrinmdonnelly/station).

## What it costs

About £2 a month in Anthropic API spend. Google Search Console is free. GitHub Actions usage is free at this volume.

## What you'll need before you start

This is the most technical of the three agents to set up. Plan an hour the first time. The GSC service account is the only fiddly bit and you only do it once.

1. A GitHub account
2. A site already verified in [Google Search Console](https://search.google.com/search-console) with at least a few weeks of search data
3. An [Anthropic API key](https://console.anthropic.com)
4. A Google Cloud account (free tier is fine) to create a service account that can read your GSC data
5. About 60 minutes for first-time setup

If the GSC step looks daunting, [SETUP.md](SETUP.md) walks through every click. You can also paste it into ChatGPT or Claude and ask it to walk you through step by step.

## How it works

1. Alex authenticates to Google Search Console using a service account you create
2. Pulls 7 days of data and compares against the previous 7
3. Reads your `brand-voice.md` and `state.md` from config so recommendations sound like you
4. Calls Claude with web search to spot competitors, forum threads, and trends
5. Writes the report and commits it back to your repo

The whole pipeline runs on GitHub Actions every Wednesday at 10:00 UK by default. If anything breaks, he emails you.

## Set up

See [SETUP.md](SETUP.md) for the full step-by-step. The short version:

1. Fork this repo
2. Edit `config/brand-voice.md` and `config/state.md` so Alex knows how you sound and what matters
3. Set up a Google Cloud service account, give it read access to your GSC property (the fiddly bit)
4. Add three secrets and two variables to your GitHub repo
5. Run the workflow once to test, then let Wednesday's schedule take over

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
- **What to focus on.** Edit `config/state.md` to tell Alex which pages matter most, which forums your audience reads, and what's off-limits.
- **Schedule.** Edit `.github/workflows/weekly.yml`.
- **Model.** Set `ANTHROPIC_MODEL` to switch model.
- **Timezone.** Set `AGENT_TIMEZONE` to any IANA name.

## The bigger picture

Alex can run alongside two siblings if you want a fuller setup:

| Agent | Role | Cadence |
|-------|------|---------|
| **[Cleo](https://github.com/catrinmdonnelly/cleo-agent)** | Weekly growth strategy. Reads what's happening, decides the focus. | Mondays |
| **Alex** | SEO. Pulls Search Console, finds rising queries and ranking opportunities. | Wednesdays |
| **[Jess](https://github.com/catrinmdonnelly/jess-agent)** | Social content. Plans and posts daily Instagram carousels. | Daily |

Each one runs on its own. You don't need to run all three.

## Help

Issues and pull requests welcome. The GSC step is where most people get stuck. Open an issue with which step is failing and the error message and I'll help.

## Licence

MIT. See [LICENSE](LICENSE).
